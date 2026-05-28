import logging

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

TIPO_COMPROBANTE = [
    ('1', 'Factura (F...)'),
    ('2', 'Boleta (B...)'),
    ('7', 'Nota de Crédito (FC.../BC...)'),
    ('8', 'Nota de Débito (FD.../BD...)'),
]


class SunatSerie(models.Model):
    _name = 'sunat.serie'
    _description = 'Series y correlativos SUNAT'
    _order = 'tipo_comprobante, name'

    name = fields.Char(
        string='Serie',
        required=True,
        help='Código de serie (ej: B001, F001, BC01, FC01). 4 caracteres.',
    )
    tipo_comprobante = fields.Selection(
        selection=TIPO_COMPROBANTE,
        string='Tipo de comprobante',
        required=True,
    )
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Diario contable',
        required=True,
        ondelete='restrict',
        help='Diario asociado a esta serie.',
    )
    next_number = fields.Integer(
        string='Siguiente número',
        default=1,
        required=True,
        help='Próximo correlativo a emitir. No modificar manualmente en producción.',
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_journal_unique', 'UNIQUE(name, journal_id)',
         'La serie ya existe para este diario.'),
    ]

    @api.constrains('name')
    def _check_serie_format(self):
        import re
        for rec in self:
            if not re.match(r'^[A-Z]{1}[A-Z0-9]{3}$', rec.name):
                raise ValidationError(
                    f"La serie '{rec.name}' debe tener exactamente 4 caracteres: "
                    f"1 letra seguida de 3 letras/dígitos (ej: B001, F001, BC01)."
                )

    def get_next_number(self):
        """
        Retorna el siguiente correlativo y lo incrementa atómicamente.
        Usa SELECT FOR UPDATE para evitar race conditions con múltiples workers.
        """
        self.ensure_one()
        # Lock the row to prevent concurrent access
        self.env.cr.execute(
            'SELECT next_number FROM sunat_serie WHERE id = %s FOR UPDATE',
            (self.id,)
        )
        row = self.env.cr.fetchone()
        if not row:
            raise UserError(f"No se encontró la serie {self.name} en la base de datos.")
        current = row[0]
        self.env.cr.execute(
            'UPDATE sunat_serie SET next_number = %s WHERE id = %s',
            (current + 1, self.id)
        )
        return current

    @api.model
    def get_for_journal(self, journal, tipo_comprobante):
        """
        Retorna la serie activa para el diario y tipo de comprobante dados.
        Lanza UserError si no existe ninguna configurada.
        """
        serie = self.search([
            ('journal_id', '=', journal.id),
            ('tipo_comprobante', '=', str(tipo_comprobante)),
            ('active', '=', True),
        ], limit=1)
        if not serie:
            raise UserError(
                f"No hay una serie SUNAT configurada para el diario '{journal.name}' "
                f"con tipo de comprobante {tipo_comprobante}. "
                f"Configure una en Contabilidad → Configuración → Series SUNAT."
            )
        return serie
