import hashlib
import logging

import requests

from odoo import models, _
from odoo.exceptions import UserError
from odoo.addons.queue_job.exception import RetryableJobError

_logger = logging.getLogger(__name__)

NUBEFACT_URLS = {
    'demo': 'https://demo.nubefact.com/api/v1/{url_token}',
    'produccion': 'https://api.nubefact.com/api/v1/{url_token}',
}

# Códigos HTTP de NubeFact que ameritan reintento automático
RETRYABLE_HTTP_CODES = {429, 500, 502, 503, 504}


class NubefactMixin(models.AbstractModel):
    _name = 'nubefact.mixin'
    _description = 'NubeFact API Mixin'

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
            "NubeFact [%s] HTTP %s para move_id=%s",
            modo, response.status_code, payload.get('serie', '?') + '-' + str(payload.get('numero', '?'))
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
