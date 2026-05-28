import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class SunatLog(models.Model):
    _name = 'sunat.log'
    _description = 'Log de envíos a SUNAT/NubeFact'
    _order = 'timestamp desc'
    _log_access = False  # No crear campos write_uid/create_uid — datos de auditoría inmutables

    move_id = fields.Many2one(
        comodel_name='account.move',
        string='Comprobante',
        ondelete='set null',
        index=True,
        readonly=True,
    )
    timestamp = fields.Datetime(
        string='Fecha/hora',
        default=fields.Datetime.now,
        readonly=True,
        index=True,
    )
    http_status = fields.Integer(
        string='HTTP Status',
        readonly=True,
    )
    aceptada_por_sunat = fields.Boolean(
        string='Aceptada SUNAT',
        readonly=True,
    )
    sunat_result = fields.Selection(
        selection=[
            ('accepted', 'Aceptada'),
            ('observed', 'Observada'),
            ('rejected', 'Rechazada'),
            ('error', 'Error de comunicación'),
        ],
        string='Resultado',
        readonly=True,
    )
    hash_cpe = fields.Char(
        string='Hash',
        readonly=True,
        help='Hash del comprobante devuelto por SUNAT.',
    )
    codigo_sunat = fields.Char(
        string='Código SUNAT',
        readonly=True,
    )
    descripcion_sunat = fields.Text(
        string='Descripción SUNAT',
        readonly=True,
    )
    error_msg = fields.Text(
        string='Error técnico',
        readonly=True,
        help='Detalle del error de comunicación (sin datos sensibles).',
    )

    @classmethod
    def _log(cls, env, move, http_status, result, **kwargs):
        """
        Crea un registro de log. Llamar dentro del job de envío.
        No loguea el payload completo (puede contener datos personales).
        """
        env['sunat.log'].sudo().create({
            'move_id': move.id if move else False,
            'http_status': http_status,
            'sunat_result': result,
            **{k: v for k, v in kwargs.items() if k in (
                'aceptada_por_sunat', 'hash_cpe', 'codigo_sunat',
                'descripcion_sunat', 'error_msg',
            )},
        })
