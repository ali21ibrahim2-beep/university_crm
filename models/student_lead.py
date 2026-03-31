# Import the tools we need from Odoo
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import re

# This class defines your database table
# Every student lead will be one row in this table
class StudentLead(models.Model):

    _name = 'student.lead'
    _description = 'Student Lead'
    # Default sorting — newest first
    _order = 'date_contacted desc'

    # ── BASIC INFORMATION ───────────────────────────────────

    # Student full name — required, cannot be empty
    # Only accepts letters and spaces — no numbers or symbols
    name = fields.Char(string='Student Name', required=True)
    
    # Assigned employee — which employee is handling this student
    # Links to Odoo's built-in users table
    user_id = fields.Many2one(
        'res.users',
        string='Assigned To',
        default=lambda self: self.env.user,
        tracking=True
    )
    
    # Email address — used for portal invitation and contact
    # Must be a valid email format
    email = fields.Char(string='Email')

    # Second phone number — optional
    phone2 = fields.Char(string='Second Phone')
    
    # Country code selector — shows country name with phone code
    # Example: Turkey (+90), United States (+1)
    phone_country_id = fields.Many2one(
        'res.country',
        string='Country Code',
        default=lambda self: self.env['res.country'].search(
            [('code', '=', 'TR')], limit=1
        )
    )

    # Computed field — shows the phone code as text
    # Example: +90, +1, +44
    phone_code_display = fields.Char(
        string='Code',
        compute='_compute_phone_code',
        store=False
    )

    @api.depends('phone_country_id')
    def _compute_phone_code(self):
        for rec in self:
            if rec.phone_country_id and rec.phone_country_id.phone_code:
                rec.phone_code_display = f'+{rec.phone_country_id.phone_code}'
            else:
                rec.phone_code_display = ''

    # Phone number — numbers only, no letters
    phone = fields.Char(string='Phone Number')

    # Country — links to Odoo's built-in country table
    # Searchable dropdown with all countries
    country_id = fields.Many2one(
        'res.country',
        string='Nationality'
    )

    # Academic specialization — what the student wants to study
    specialization = fields.Char(string='Academic Specialization')

    # ── CURRENCY AND BUDGET ─────────────────────────────────

    # Currency selector — links to Odoo's built-in currency table
    # Default = USD
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env['res.currency'].search(
            [('name', '=', 'USD')], limit=1
        )
    )

    # Exact budget — one fixed amount
    budget_amount = fields.Monetary(
        string='Budget',
        currency_field='currency_id'
    )

    # Budget range — minimum amount
    budget_min = fields.Monetary(
        string='Budget From',
        currency_field='currency_id'
    )

    # Budget range — maximum amount
    budget_max = fields.Monetary(
        string='Budget To',
        currency_field='currency_id'
    )

    # Computed field — shows budget in list view
    # Shows exact budget OR range depending on what is filled
    budget_display = fields.Char(
        string='Budget',
        compute='_compute_budget_display',
        store=True
    )

    @api.depends('budget_amount', 'budget_min', 'budget_max', 'currency_id')
    def _compute_budget_display(self):
        for rec in self:
            currency = rec.currency_id.symbol or '$'
            if rec.budget_min and rec.budget_max:
                # Show range — from min to max
                rec.budget_display = (
                    f'{currency} {rec.budget_min:,.0f}'
                    f' - '
                    f'{currency} {rec.budget_max:,.0f}'
                )
            elif rec.budget_amount:
                # Show exact budget
                rec.budget_display = f'{currency} {rec.budget_amount:,.2f}'
            else:
                rec.budget_display = ''

    # ── STATUS AND DATES ────────────────────────────────────

    # Status — dropdown showing where student is in the process
    status = fields.Selection([
        ('new', 'New Inquiry'),
        ('options_sent', 'Options Sent'),
        ('chosen', 'University Chosen'),
        ('docs', 'Collecting Documents'),
        ('enrolled', 'Enrolled'),
        ('lost', 'Lost'),
    ], string='Status', default='new')

    # Date we first contacted this student
    date_contacted = fields.Date(
        string='Date Contacted',
        default=fields.Date.today
    )

    # Date we need to follow up with this student
    follow_up_date = fields.Date(string='Follow-up Date')

    # General notes about the student
    notes = fields.Text(string='Notes')

    # ── COMPUTED FIELD ───────────────────────────────────────

    # Full phone with country code — computed automatically
    # Example: +90 5318661439
    phone_full = fields.Char(
        string='Full Phone',
        compute='_compute_phone_full',
        store=True
    )

    @api.depends('phone_country_id', 'phone')
    def _compute_phone_full(self):
        for rec in self:
            if rec.phone_country_id and rec.phone:
                # Get the country phone code — example: +90
                code = rec.phone_country_id.phone_code
                rec.phone_full = f'+{code} {rec.phone}'
            else:
                rec.phone_full = rec.phone or ''

    # ── VALIDATION ──────────────────────────────────────────

    @api.constrains('name')
    def _check_name(self):
        for rec in self:
            # Name must only contain letters and spaces
            if rec.name and not re.match(r'^[a-zA-Z\u0600-\u06FF\s]+$', rec.name):
                raise ValidationError(
                    'Student name can only contain letters and spaces!'
                )

    @api.constrains('phone')
    def _check_phone(self):
        for rec in self:
            # Phone must only contain numbers, spaces, dashes
            if rec.phone and not re.match(r'^[\d\s\-]+$', rec.phone):
                raise ValidationError(
                    'Phone number can only contain numbers!'
                )

# ── ACCESS RULES ────────────────────────────────────────
# This makes employees see only their own students
# Managers see everything
    @api.model
    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):
        # Check if current user is a manager or admin
        is_manager = self.env.user.has_group(
            'university_crm.group_university_manager'
        )
        # Admin user (id=1) always sees everything
        is_admin = self.env.user.id == 1
        # If not manager and not admin — show only their own students
        if not is_manager and not is_admin:
            domain = [('user_id', '=', self.env.uid)] + list(domain)
        return super()._search(
            domain, offset=offset, limit=limit, order=order
        )


    # ── DELETE PROTECTION ────────────────────────────────────
    # This runs every time someone tries to delete a student
    def unlink(self):
        # Check if the current user is a manager or admin
        is_manager = self.env.user.has_group(
            'university_crm.group_university_manager'
        )
        is_admin = self.env.user.id == 1
        
        # If NOT manager and NOT admin — check ownership
        if not is_manager and not is_admin:
            for rec in self:
                # If this student belongs to someone else — block delete
                if rec.user_id.id != self.env.uid:
                    raise ValidationError(
                        'You can only delete your own students!'
                    )
        # If manager or admin — allow delete without any check
        return super().unlink()

    @api.constrains('budget_amount', 'budget_min', 'budget_max')
    def _check_budget(self):
        for rec in self:
            # Exact budget cannot be negative
            if rec.budget_amount < 0:
                raise ValidationError('Budget cannot be negative!')
            # Range fields cannot be negative
            if rec.budget_min < 0 or rec.budget_max < 0:
                raise ValidationError('Budget range cannot be negative!')
            # Min cannot be more than max
            if rec.budget_min and rec.budget_max and rec.budget_min > rec.budget_max:
                raise ValidationError(
                    'Budget From cannot be more than Budget To!'
                )