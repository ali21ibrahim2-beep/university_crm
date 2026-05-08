# Models init — imports all database models for Odoo to register
from . import phone_country_format   # Phone validation rules per country
from . import student_lead           # Main student lead model + delete wizard
from . import student_archive        # Soft-delete archive for deleted students
from . import user_password          # Custom password management for res.users