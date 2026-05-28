import logging

from odoo import fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SendToSunatWizard(models.TransientModel):
    """
    Wizard de envío/reenvío de comprobantes electrónicos a SUNAT vía NubeFact.
    Permite seleccionar el modo (sandbox/producción) antes de confirmar el envío.
    """
    _name = 'send.to.sunat.wizard'
    _description = 'Wizard de envío a SUNAT / NubeFact'

    move_id = fields.Many2one(
        comodel_name='account.move',
        string='Comprobante',
        required=True,
        readonly=True,
        ondelete='cascade',
    )
    modo = fields.Selection(
        selection=[
            ('demo', 'Sandbox NubeFact (pruebas)'),
            ('produccion', 'Producción (SUNAT real)'),
        ],
        string='Modo de envío',
        required=True,
        default='demo',
        help="Seleccione 'Sandbox' para pruebas sin afectar SUNAT. "
             "Use 'Producción' solo cuando el comprobante sea real.",
    )

    def action_confirmar_envio(self):
        """
        Confirma el envío del comprobante a SUNAT en el modo seleccionado.
        Escribe el modo en la configuración y dispara action_send_to_sunat().
        """
        self.ensure_one()

        if not self.move_id:
            raise UserError(_("No hay ningún comprobante asociado a este wizard."))

        if self.move_id.state != 'posted':
            raise UserError(_(
                "El comprobante '%s' debe estar publicado antes de enviarlo a SUNAT."
            ) % self.move_id.name)

        # Actualizar el modo en la configuración global del módulo
        Config = self.env['sciback.school.config']
        Config.get_config().write({'nubefact_modo': self.modo})

        _logger.info(
            "Wizard SUNAT: enviando %s en modo %s",
            self.move_id.name, self.modo
        )

        # Delegar al método del modelo (que encola via queue_job)
        self.move_id.action_send_to_sunat()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Envío encolado'),
                'message': _(
                    "El comprobante %s fue encolado para envío a SUNAT "
                    "en modo %s. Revise el estado en unos momentos."
                ) % (self.move_id.name, dict(self._fields['modo'].selection)[self.modo]),
                'type': 'success',
                'sticky': False,
            },
        }
