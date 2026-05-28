{
    'name': 'SciBack SUNAT NubeFact',
    'version': '17.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Emisión de comprobantes electrónicos SUNAT vía NubeFact',
    'author': 'SciBack',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'l10n_pe',
        'queue_job',
        'sciback_school_base',
    ],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/queue_channel_data.xml',
        'data/nubefact_journal_data.xml',
        'views/account_move_views.xml',
        'wizards/send_to_sunat_wizard_views.xml',
    ],
    'installable': True,
}
