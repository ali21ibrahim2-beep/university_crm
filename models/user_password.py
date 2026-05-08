import hashlib
from odoo import models, fields, api
from datetime import datetime


class ResUsers(models.Model):
    _inherit = 'res.users'

    # ── PASSWORD MANAGEMENT ──────────────────────────────────
    # For employees/managers who need a custom portal password
    # (separate from Odoo's standard password)

    password_hash_custom = fields.Char(
        string='Custom Password Hash',
        copy=False,
        help='SHA-256 hash of custom password. Used for portal authentication.'
    )

    has_custom_password = fields.Boolean(
        string='Has Custom Password Set',
        compute='_compute_has_custom_password',
        store=True,
    )

    password_set_date = fields.Datetime(
        string='Password Set Date',
        copy=False,
        help='Date when custom password was first set'
    )

    @api.depends('password_hash_custom')
    def _compute_has_custom_password(self):
        for user in self:
            user.has_custom_password = bool(user.password_hash_custom)

    @staticmethod
    def _hash_password(password):
        """SHA-256 hash with salt."""
        salted = f'univ_crm_salt_{password}'
        return hashlib.sha256(salted.encode()).hexdigest()

    def set_custom_password(self, password):
        """Set a custom password for this user."""
        if not password or len(password) < 6:
            raise ValueError('Password must be at least 6 characters long')
        
        self.write({
            'password_hash_custom': self._hash_password(password),
            'password_set_date': datetime.now(),
        })

    def verify_custom_password(self, password):
        """Verify if provided password matches stored hash."""
        if not self.password_hash_custom:
            return False
        expected = self._hash_password(password)
        return self.password_hash_custom == expected
