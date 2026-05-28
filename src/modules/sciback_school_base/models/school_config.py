from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ScibackSchoolConfig(models.Model):
    _name = 'sciback.school.config'
    _description = 'Configuración del Colegio'
    _rec_name = 'name'

    # ─── Datos generales ────────────────────────────────────────────────────
    name = fields.Char(
        string='Nombre del Colegio',
        required=True,
    )
    ruc = fields.Char(
        string='RUC',
        size=11,
        required=True,
        help='RUC de 11 dígitos registrado en SUNAT',
    )
    codigo_modular = fields.Char(
        string='Código Modular MINEDU',
        help='Código de 7 dígitos asignado por MINEDU/SIAGIE',
    )
    anno_lectivo = fields.Char(
        string='Año Lectivo',
        required=True,
        default=lambda self: str(fields.Date.today().year),
        help='Año escolar en curso (ej: 2026)',
    )
    director_id = fields.Many2one(
        comodel_name='res.partner',
        string='Director(a)',
        help='Director actual del colegio',
    )
    ugel_id = fields.Many2one(
        comodel_name='res.partner',
        string='UGEL de Jurisdicción',
        help='Unidad de Gestión Educativa Local',
    )

    # ─── Niveles educativos ──────────────────────────────────────────────────
    nivel_ids = fields.Many2many(
        comodel_name='op.course',
        relation='sciback_school_config_course_rel',
        column1='config_id',
        column2='course_id',
        string='Niveles Educativos Activos',
        help='Niveles EBR habilitados en este colegio',
    )

    # ─── Integraciones ───────────────────────────────────────────────────────
    nubefact_api_token = fields.Char(
        string='Token NubeFact',
        groups='base.group_system',
        help='Token de autenticación para facturación electrónica con NubeFact',
    )
    nubefact_url_token = fields.Char(
        string='URL Token NubeFact',
        groups='base.group_system',
        help='UUID del emisor en la URL de NubeFact (ej: 12345678-abcd-...). '
             'Distinto del API token.',
    )
    nubefact_modo = fields.Selection(
        selection=[
            ('demo', 'Sandbox / Demo'),
            ('produccion', 'Producción (SUNAT real)'),
        ],
        string='Modo NubeFact',
        default='demo',
        required=True,
        groups='base.group_system',
        help="'Sandbox' para pruebas sin afectar SUNAT. "
             "'Producción' para emisión real.",
    )
    culqi_public_key = fields.Char(
        string='Culqi Public Key',
        groups='base.group_system',
    )
    culqi_secret_key = fields.Char(
        string='Culqi Secret Key',
        groups='base.group_system',
    )

    # ─── Singleton ───────────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        if self.search([], limit=1):
            raise ValidationError(
                'Solo puede existir un registro de Configuración del Colegio. '
                'Edite el registro existente.'
            )
        return super().create(vals_list)

    @api.model
    def get_config(self):
        """Retorna el singleton o lanza error si no existe aún."""
        config = self.search([], limit=1)
        if not config:
            raise ValidationError(
                'Configure primero los datos del colegio en '
                'Configuración > SciBack School.'
            )
        return config
