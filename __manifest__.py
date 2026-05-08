# ── Module Configuration ─────────────────────────────────────
# Tells Odoo the module name, dependencies, and which files to load.
{
    'name': 'University CRM',
    'version': '18.0.1.2.0',
    'summary': 'Manage student leads from inquiry to enrollment',
    'author': 'Your Name',
    'category': 'Extra Tools',

    # Depends on: base (core), mail (chatter), portal (student login), website (portal pages)
    'depends': ['base', 'mail', 'portal', 'website'],

    # Files loaded in order during install/upgrade
    'data': [
        'security/security_groups.xml',       # Employee & Manager roles
        'security/ir.model.access.csv',       # Read/write permissions per role
        'security/record_rules.xml',          # Record-level access restrictions
        'data/currencies.xml',                # Activate EUR and TRY currencies
        'data/phone_validation_data.xml',     # Phone format rules per country
        'views/student_views.xml',            # Student list, form, wizard views
        'views/archive_views.xml',            # Soft-delete archive views
        'views/menu.xml',                     # Sidebar navigation menus
        'templates/portal_templates.xml',     # Student self-service portal pages
    ],

    # Sample data for testing — only loaded with "Load Demo Data" checked
    'demo': [
        'data/demo_data.xml',
    ],

    'installable': True,
    'application': True,
    'auto_install': False,
}