# ── Phone Country Format Model ───────────────────────────────
# Stores phone validation rules per country.
# Each record defines: how many digits the phone must have,
# and optionally which digit it must start with.
# Example: Turkey → 10 digits, starts with 5.
# These rules are used by student_lead._check_phone() to validate input.

from odoo import models, fields


class PhoneCountryFormat(models.Model):

    _name = 'phone.country.format'
    _description = 'Phone Country Format'
    _rec_name = 'country_id'

    # Which country this rule applies to (one rule per country)
    country_id = fields.Many2one(
        'res.country',
        string='Country',
        required=True,
        ondelete='cascade',
    )

    # How many digits the phone number must have (e.g. 10 for Turkey)
    digit_count = fields.Integer(
        string='Digit Count',
        required=True,
        help='Exact number of digits required for this country',
    )

    # Optional — allowed starting digits for a mobile number in this country.
    # Each character of the string is one valid leading digit:
    #   "5"   → must start with 5                    (Turkey, Saudi Arabia)
    #   "67"  → first digit must be 6 or 7           (Spain, Morocco)
    #   ""    → no restriction
    leading_digit = fields.Char(
        string='Leading Digits',
        help=(
            'Allowed starting digits for the mobile number. '
            'Each character is a valid first digit — "5" means starts with 5, '
            '"67" means starts with 6 or 7. Leave empty for no restriction.'
        ),
    )

    # Prevent duplicate rules — one country can only have one format rule
    _sql_constraints = [
        ('country_unique', 'UNIQUE(country_id)',
         'A phone format rule already exists for this country!'),
    ]
