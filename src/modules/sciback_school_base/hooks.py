"""
Hooks de instalación para sciback_school_base.

pre_init_hook: Si los niveles EBR (op.course) ya existen en la DB sin XMLID
(p.ej. creados manualmente antes de instalar este módulo), registra sus
XMLIDs en ir_model_data para que el XML de datos pueda referenciarlos
con ref="sciback_school_base.nivel_*" sin colisionar con la constraint única.
"""


def pre_init_hook(env):
    """Adopta registros op.course existentes registrando sus XMLIDs."""
    NIVELES = [
        ('nivel_inicial', 'INICIAL'),
        ('nivel_primaria', 'PRIMARIA'),
        ('nivel_secundaria', 'SECUNDARIA'),
    ]
    IrModelData = env['ir.model.data']
    OpCourse = env['op.course']

    for xml_id, code in NIVELES:
        # Verificar si el XMLID ya existe
        existing_xid = IrModelData.search([
            ('module', '=', 'sciback_school_base'),
            ('name', '=', xml_id),
            ('model', '=', 'op.course'),
        ], limit=1)
        if existing_xid:
            continue

        # Buscar el registro por código
        course = OpCourse.search([('code', '=', code)], limit=1)
        if not course:
            continue

        # Registrar el XMLID apuntando al registro existente
        IrModelData.create({
            'module': 'sciback_school_base',
            'name': xml_id,
            'model': 'op.course',
            'res_id': course.id,
            'noupdate': True,
        })
