{
    # The name users will see in the Odoo Apps store
    'name': 'University CRM',

    # 18.0 = Odoo version you are using
    # 1.0.0 = your module version (major.minor.patch)
    # Always start at 1.0.0 and increase when you make changes
    'version': '18.0.1.0.0',

    # Short description shown under the module name in Apps store
    'summary': 'Manage student leads from inquiry to enrollment',

    # Your name
    'author': 'Your Name',

    # Which section this module appears in inside the Apps store
    'category': 'Extra Tools',

    # Other modules this module needs to work
    # 'base' is the Odoo core — always required as minimum
    # Later you might add 'crm' or 'sale' if you need their features
    'depends': ['base'],

   # Files Odoo loads when installing your module
    # ORDER MATTERS — security must be first, then views, then menus
    'data': [
        'security/security_groups.xml',   # user groups — manager and employee
        'security/ir.model.access.csv',   # who can read/write/delete
        'views/student_views.xml',        # forms and list views
        'views/menu.xml',                 # menus in the top bar
    ],

    # Sample data loaded only in demo/test mode — not in real production
    'demo': [
        'data/demo_data.xml',
    ],

    # True = module appears in the Apps store and can be installed
    'installable': True,

    # True = module gets its own icon and menu in the top navigation bar
    'application': True,

    # False = user must install it manually (not installed automatically)
    'auto_install': False,
}