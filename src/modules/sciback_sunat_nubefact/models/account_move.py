import hashlib
import logging
import re

import requests

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError
from odoo.addons.queue_job.exception import RetryableJobError

_logger = logging.getLogger(__name__)

# ─── Constantes NubeFact ─────────────────────────────────────────────────────

NUBEFACT_URLS = {
    # demo.nubefact.com no existe — ambos modos usan api.nubefact.com.
    # La diferencia está en la configuración de la cuenta NubeFact, no en la URL.
    'demo': 'https://api.nubefact.com/api/v1/{url_token}',
    'produccion': 'https://api.nubefact.com/api/v1/{url_token}',
}

# Códigos HTTP de NubeFact que ameritan reintento automático
RETRYABLE_HTTP_CODES = {429, 500, 502, 503, 504}

SUNAT_STATES = [
    ('draft', 'Borrador'),
    ('sending', 'Enviando'),
    ('sent', 'Enviado'),
    ('accepted', 'Aceptado'),
    ('rejected', 'Rechazado'),
    ('observed', 'Observado'),
]

# NubeFact: tipo_de_comprobante (catálogo NubeFact/SUNAT)
TIPO_FACTURA = 1
TIPO_BOLETA = 2
TIPO_NC = 3   # Nota de Crédito
TIPO_ND = 4   # Nota de Débito

# NubeFact: moneda (catálogo)
MONEDA_MAP = {'PEN': 1, 'USD': 2}

# NubeFact: tipo_de_igv — Catálogo 07 SUNAT
# 1=Gravado, 6=Gratuito, 8=Exonerado, 9=Inafecto
IGV_GRAVADO = 1
IGV_EXONERADO = 8
IGV_INAFECTO = 9   # EBR: servicios educativos son INAFECTOS (Art. 2 TUO Ley IGV)


class AccountMove(models.Model):
    _inherit = 'account.move'

    # ─── Campos SUNAT ────────────────────────────────────────────────────────

    sunat_state = fields.Selection(
        selection=SUNAT_STATES,
        string='Estado SUNAT',
        default='draft',
        copy=False,
        tracking=True,
    )
    sunat_serie = fields.Char(string='Serie SUNAT', copy=False, readonly=True)
    sunat_numero = fields.Integer(string='N° SUNAT', copy=False, readonly=True)
    sunat_hash = fields.Char(string='Hash SUNAT', copy=False, readonly=True)
    sunat_qr = fields.Char(
        string='QR SUNAT',
        copy=False,
        readonly=True,
        help='Cadena para código QR de la representación impresa.',
    )
    sunat_enlace_pdf = fields.Char(string='PDF NubeFact', copy=False, readonly=True)
    sunat_enlace_xml = fields.Char(string='XML NubeFact', copy=False, readonly=True)
    sunat_error_msg = fields.Text(string='Error SUNAT', copy=False, readonly=True)

    # ─── Acciones públicas ────────────────────────────────────────────────────

    def action_send_to_sunat(self):
        self.ensure_one()

        if not self.env.user.has_group('sciback_sunat_nubefact.group_sunat_emisor'):
            raise AccessError(_("No tiene permisos para emitir comprobantes a SUNAT."))

        if self.state != 'posted':
            raise UserError(_("Solo se pueden enviar a SUNAT facturas publicadas."))

        if self.sunat_state in ('accepted', 'sending'):
            raise UserError(_(
                "Este comprobante ya fue enviado o está en proceso de envío."
            ))

        self.sunat_state = 'sending'

        self.with_delay(
            description=f"Envío SUNAT: {self.name}",
            channel='root.sunat',
            max_retries=5,
        )._job_send_to_sunat()

        return True

    # ─── Métodos del job ─────────────────────────────────────────────────────

    def _job_send_to_sunat(self):
        self.ensure_one()

        # Idempotencia: si ya fue aceptado, no reemitir
        if self.sunat_state == 'accepted':
            _logger.info("Comprobante %s ya aceptado, omitiendo reenvío.", self.name)
            return

        # Asignar serie y número si aún no tienen (con lock)
        if not self.sunat_serie or not self.sunat_numero:
            self._assign_sunat_serie_numero()

        payload = self._get_nubefact_payload()
        try:
            response = self._nubefact_send(payload)
            self._process_nubefact_response(response)
        except Exception as exc:
            if self.sunat_state == 'sending':
                self.sunat_state = 'draft'
            self._sunat_log(
                http_status=getattr(getattr(exc, 'response', None), 'status_code', 0),
                result='error',
                error_msg=str(exc)[:500],
            )
            _logger.exception("Error al enviar %s a NubeFact", self.name)
            raise

    def _assign_sunat_serie_numero(self):
        """Asigna serie y número correlativo desde sunat.serie (con SELECT FOR UPDATE)."""
        tipo = str(self._get_nubefact_tipo_comprobante())
        serie_rec = self.env['sunat.serie'].get_for_journal(self.journal_id, tipo)
        numero = serie_rec.get_next_number()
        self.write({'sunat_serie': serie_rec.name, 'sunat_numero': numero})

    # ─── Construcción del payload ─────────────────────────────────────────────

    def _get_nubefact_payload(self):
        self.ensure_one()
        config = self._nubefact_get_config()
        partner = self.partner_id

        self._validate_partner_sunat(partner)

        tipo = self._get_nubefact_tipo_comprobante()
        items = self._get_nubefact_items()

        # Calcular totales por tipo de afectación desde los items ya construidos
        # (no usar self.amount_tax que refleja taxes de Odoo, no la afectación SUNAT)
        product_lines = self.invoice_line_ids.filtered(lambda l: l.display_type == 'product')
        total_gravada = sum(
            l.price_subtotal for l in product_lines
            if self._get_tipo_igv_linea(l) == IGV_GRAVADO
        )
        total_inafecta = sum(
            l.price_subtotal for l in product_lines
            if self._get_tipo_igv_linea(l) == IGV_INAFECTO
        )
        total_exonerada = sum(
            l.price_subtotal for l in product_lines
            if self._get_tipo_igv_linea(l) == IGV_EXONERADO
        )
        total_igv = round(total_gravada * 0.18, 2)

        codigo_unico = self._make_codigo_unico(
            config['ruc'], self.sunat_serie, self.sunat_numero
        )

        payload = {
            'operacion': 'generar_comprobante',
            'tipo_de_comprobante': tipo,
            'serie': self.sunat_serie or '',
            'numero': self.sunat_numero or 0,
            'sunat_transaction': 1,
            'cliente_tipo_de_documento': self._get_tipo_doc_cliente(partner),
            'cliente_numero_de_documento': (partner.vat or '').strip(),
            'cliente_denominacion': re.sub(r'[\x00-\x1f]', ' ', partner.name or '').strip()[:100],
            'cliente_direccion': (partner.street or '')[:200],
            'cliente_email': partner.email or '',
            'cliente_email_1': '',
            'fecha_de_emision': self.invoice_date.strftime('%d-%m-%Y') if self.invoice_date else '',
            'fecha_de_vencimiento': self.invoice_date_due.strftime('%d-%m-%Y') if self.invoice_date_due else '',
            'moneda': MONEDA_MAP.get(self.currency_id.name, 1),
            'tipo_de_cambio': '',
            'porcentaje_de_igv': 18,
            'descuento_global': '',
            'total_descuento': '',
            'total_anticipo': '',
            'total_gravada': round(total_gravada, 2) if total_gravada else '',
            'total_inafecta': round(total_inafecta, 2) if total_inafecta else '',
            'total_exonerada': round(total_exonerada, 2) if total_exonerada else '',
            'total_igv': round(total_igv, 2) if total_igv else '',
            'total_gratuita': '',
            'total_otros_cargos': '',
            'total': round(total_gravada + total_igv + total_inafecta + total_exonerada, 2),
            'percepcion_tipo': '',
            'percepcion_base_imponible': '',
            'total_percepcion': '',
            'total_incluido_percepcion': '',
            'detraccion': False,
            'enviar_automaticamente_a_la_sunat': True,
            'enviar_automaticamente_al_cliente': False,
            'codigo_unico': codigo_unico,
            'condiciones_de_pago': '',
            'medio_de_pago': '',
            'placa_vehiculo': '',
            'orden_compra_servicio': '',
            'tabla_personalizada_codigo': '',
            'formato_de_pdf': '',
            'items': items,
        }

        # Campos adicionales para Notas de Crédito/Débito
        if self.move_type == 'out_refund' and self.reversed_entry_id:
            orig = self.reversed_entry_id
            payload.update({
                'documento_que_se_modifica_tipo': self._get_tipo_doc_original(orig),
                'documento_que_se_modifica_serie': orig.sunat_serie or '',
                'documento_que_se_modifica_numero': orig.sunat_numero or 0,
                'tipo_de_nota_de_credito': 1,  # Anulación (más común)
                'motivo_de_emision': 'Anulación de la operación',
            })

        return payload

    def _get_nubefact_items(self):
        items = []
        for line in self.invoice_line_ids.filtered(lambda l: l.display_type == 'product'):
            tipo_igv = self._get_tipo_igv_linea(line)
            qty = line.quantity or 1
            base = round(line.price_subtotal, 2)  # Precio sin IGV

            if tipo_igv == IGV_GRAVADO:
                # Gravado: precio_unitario incluye IGV, total = base + igv
                igv_monto = round(base * 0.18, 2)
                precio_unitario = round((base + igv_monto) / qty, 6)
                total = round(base + igv_monto, 2)
            else:
                # Inafecto/Exonerado: IGV=0, precio_unitario = valor_unitario
                igv_monto = 0
                precio_unitario = round(base / qty, 6)
                total = base

            items.append({
                'unidad_de_medida': 'ZZ',
                'codigo': line.product_id.default_code or '',
                'descripcion': (line.name or line.product_id.name or '')[:250],
                'cantidad': qty,
                'valor_unitario': round(base / qty, 6),
                'precio_unitario': precio_unitario,
                'descuento': '',
                'subtotal': base,
                'tipo_de_igv': tipo_igv,
                'igv': igv_monto,
                'total': total,
                'anticipo_regularizacion': False,
                'anticipo_documento_serie': '',
                'anticipo_documento_numero': '',
            })
        return items

    def _get_tipo_igv_linea(self, line):
        """
        Retorna el código NubeFact de afectación IGV para una línea.
        EBR: servicios educativos son INAFECTOS (código 9), no gravados.
        Si el producto tiene campo personalizado, usarlo; sino, default inafecto.
        """
        product = line.product_id
        if hasattr(product, 'sunat_tipo_igv') and product.sunat_tipo_igv:
            return int(product.sunat_tipo_igv)
        return IGV_INAFECTO  # Default: servicios educativos EBR son inafectos

    def _get_nubefact_tipo_comprobante(self):
        # Nota de crédito primero (tiene precedencia sobre el tipo de diario)
        if self.move_type == 'out_refund':
            return TIPO_NC
        if self.move_type == 'out_invoice':
            if self.journal_id.code == 'BOL':
                return TIPO_BOLETA
            return TIPO_FACTURA
        return TIPO_FACTURA

    def _get_tipo_doc_cliente(self, partner):
        if not partner.vat:
            return 0
        vat = partner.vat.strip()
        if len(vat) == 11 and vat.isdigit():
            return 6  # RUC
        if len(vat) == 8 and vat.isdigit():
            return 1  # DNI
        return 0

    def _get_tipo_doc_original(self, original_move):
        """Para NC: tipo del comprobante que se está modificando."""
        if original_move.journal_id.code == 'BOL':
            return TIPO_BOLETA
        return TIPO_FACTURA

    def _validate_partner_sunat(self, partner):
        if not partner.name or len(partner.name.strip()) < 2:
            raise UserError(_("El nombre del cliente es requerido para emitir el comprobante."))
        if partner.vat:
            vat = partner.vat.strip()
            if len(vat) == 11 and not vat.isdigit():
                raise UserError(_("RUC del cliente inválido: %s") % vat)
            if len(vat) == 8 and not vat.isdigit():
                raise UserError(_("DNI del cliente inválido: %s") % vat)

    # ─── Procesamiento de respuesta ────────────────────────────────────────────

    def _process_nubefact_response(self, response):
        self.ensure_one()

        aceptada = response.get('aceptada_por_sunat', False)
        sunat_note = response.get('sunat_note', '') or ''
        codigo = str(response.get('sunat_responsecode', ''))
        descripcion = response.get('sunat_description', '') or ''

        # Guardar datos de respuesta
        # Nota: NubeFact usa 'codigo_hash' (no 'hash') en v1
        vals = {
            'sunat_hash': response.get('codigo_hash', '') or response.get('hash', ''),
            'sunat_qr': response.get('cadena_para_codigo_qr', ''),
            'sunat_enlace_pdf': response.get('enlace_del_pdf', ''),
            'sunat_enlace_xml': response.get('enlace_del_xml', ''),
        }

        if aceptada and not sunat_note:
            vals['sunat_state'] = 'accepted'
            vals['sunat_error_msg'] = False
            result = 'accepted'
            _logger.info("Comprobante %s aceptado por SUNAT.", self.name)

        elif aceptada and sunat_note:
            vals['sunat_state'] = 'observed'
            vals['sunat_error_msg'] = f"[{codigo}] {sunat_note}"
            result = 'observed'
            _logger.warning("Comprobante %s observado: %s", self.name, sunat_note)

        else:
            vals['sunat_state'] = 'rejected'
            vals['sunat_error_msg'] = f"[{codigo}] {descripcion}"
            result = 'rejected'
            _logger.error("Comprobante %s rechazado: %s", self.name, descripcion)

        self.write(vals)

        # Adjuntar CDR si viene URL (descargar y adjuntar como ir.attachment)
        cdr_url = response.get('enlace_del_cdr', '')
        if cdr_url:
            self._attach_cdr_from_url(cdr_url)

        # Log de auditoría
        self._sunat_log(
            http_status=200,
            result=result,
            aceptada_por_sunat=aceptada,
            hash_cpe=vals.get('sunat_hash', ''),
            codigo_sunat=codigo,
            descripcion_sunat=descripcion[:500] if descripcion else '',
        )

    def _attach_cdr_from_url(self, cdr_url):
        """Descarga el CDR desde NubeFact y lo adjunta al comprobante."""
        try:
            import base64
            import requests as req
            resp = req.get(cdr_url, timeout=30, verify=True)
            if resp.ok:
                self.env['ir.attachment'].create({
                    'name': f"CDR-{self.sunat_serie}-{self.sunat_numero}.zip",
                    'res_model': self._name,
                    'res_id': self.id,
                    'datas': base64.b64encode(resp.content).decode(),
                    'mimetype': 'application/zip',
                })
        except Exception:
            _logger.warning("No se pudo descargar el CDR de %s", cdr_url)

    def _sunat_log(self, **kwargs):
        """Registra en la tabla de auditoría sunat.log."""
        try:
            self.env['sunat.log']._log(self.env, self, **kwargs)
        except Exception:
            _logger.warning("No se pudo registrar en sunat.log para %s", self.name)

    # ─── Métodos NubeFact (integrados desde nubefact.mixin) ──────────────────

    def _nubefact_get_config(self):
        """
        Retorna configuración no sensible del emisor: ruc, url_token, modo.
        El api_token NO se retorna aquí — se lee directamente en _nubefact_send.
        """
        config = self.env['sciback.school.config'].get_config()

        if not config.nubefact_api_token:
            raise UserError(_(
                "Falta configurar el API Token de NubeFact. "
                "Ve a Configuración → SciBack School → Integraciones."
            ))
        if not config.nubefact_url_token:
            raise UserError(_(
                "Falta configurar el URL Token de NubeFact. "
                "Ve a Configuración → SciBack School → Integraciones."
            ))
        if not config.ruc:
            raise UserError(_(
                "Falta configurar el RUC del colegio. "
                "Ve a Configuración → SciBack School → General."
            ))

        return {
            'ruc': config.ruc,
            'url_token': config.nubefact_url_token,
            'modo': config.nubefact_modo or 'demo',
        }

    def _nubefact_send(self, payload):
        """
        Realiza el POST a la API REST de NubeFact.

        El api_token se lee directamente aquí y nunca sale de este scope.
        Timeout: (10s connect, 120s read) — NubeFact puede tardar por SUNAT.

        Lanza:
          - UserError: para errores definitivos (4xx) que no deben reintentarse.
          - RetryableJobError: para errores transitorios (5xx, 429, timeout de red)
            que queue_job debe reintentar con backoff.
        """
        config_rec = self.env['sciback.school.config'].get_config()
        api_token = config_rec.nubefact_api_token
        url_token = config_rec.nubefact_url_token
        modo = config_rec.nubefact_modo or 'demo'

        url = NUBEFACT_URLS[modo].format(url_token=url_token)

        headers = {
            'Authorization': f'Token token="{api_token}"',
            'Content-Type': 'application/json',
        }

        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=(10, 120),
                verify=True,
            )
        except requests.exceptions.Timeout:
            # Ambiguo: NubeFact pudo haber recibido el request.
            # El job debe consultar el comprobante antes de reintentar.
            raise RetryableJobError(
                "Timeout al conectar con NubeFact (>120s). "
                "El comprobante podría haber sido emitido. "
                "Verifique antes de reintentar.",
                seconds=300,
                ignore_retry=False,
            )
        except requests.exceptions.ConnectionError as exc:
            raise RetryableJobError(
                f"No se pudo conectar con NubeFact: {exc}",
                seconds=60,
            )

        # Log mínimo (sin token, sin payload completo)
        _logger.info(
            "NubeFact [%s] HTTP %s para %s-%s",
            modo, response.status_code,
            payload.get('serie', '?'), str(payload.get('numero', '?'))
        )

        if response.status_code == 400:
            raise UserError(_(
                "NubeFact: payload inválido (400). Revise los datos del comprobante.\n%s"
            ) % self._extract_nubefact_error(response))

        if response.status_code == 401:
            raise UserError(_(
                "NubeFact: API Token inválido o sin autorización (401). "
                "Revise la configuración del token."
            ))

        if response.status_code == 402:
            raise UserError(_(
                "NubeFact: sin créditos disponibles (402). "
                "Recargue su cuenta NubeFact."
            ))

        if response.status_code == 422:
            raise UserError(_(
                "NubeFact: error de validación de negocio (422).\n%s"
            ) % self._extract_nubefact_error(response))

        if response.status_code in RETRYABLE_HTTP_CODES:
            raise RetryableJobError(
                f"NubeFact respondió {response.status_code}. Se reintentará automáticamente.",
                seconds=120,
            )

        if not response.ok:
            raise UserError(_(
                "Respuesta inesperada de NubeFact (HTTP %s):\n%s"
            ) % (response.status_code, response.text[:500]))

        try:
            return response.json()
        except ValueError:
            raise UserError(_(
                "NubeFact devolvió una respuesta no-JSON (HTTP %s):\n%s"
            ) % (response.status_code, response.text[:500]))

    @staticmethod
    def _extract_nubefact_error(response):
        """Extrae el mensaje de error del body de la respuesta NubeFact."""
        try:
            data = response.json()
            return data.get('errors', data.get('message', response.text[:300]))
        except ValueError:
            return response.text[:300]

    @staticmethod
    def _make_codigo_unico(ruc, serie, numero):
        """
        Genera un código único determinístico para idempotencia en NubeFact.
        NubeFact usa este código para deduplicar requests.
        Si dos POSTs llegan con el mismo codigo_unico, NubeFact devuelve el primero.
        """
        raw = f"{ruc}-{serie}-{numero:08d}"
        return hashlib.sha1(raw.encode()).hexdigest()[:20]
