# ── Student Archive Model ────────────────────────────────────
# Soft-delete archive — when a student is deleted, their data
# is copied here instead of being permanently removed.
# Stores: all original student fields + deletion metadata
# (who deleted, when, why).
# Managers can restore any archived students.
# Employees can restore archived students they deleted.

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class StudentArchive(models.Model):

    _name = 'student.archive'
    _description = 'Archived Student'
    _order = 'deleted_date desc'

    # ── COPIED STUDENT DATA ──────────────────────────────────
    # Mirror of all fields from student.lead — frozen at time of deletion.

    name = fields.Char(string='Student Name', required=True)
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone Number')
    phone2 = fields.Char(string='Second Phone')
    phone_full = fields.Char(string='Full Phone')

    phone_country_id = fields.Many2one(
        'res.country', string='Country Code'
    )
    country_id = fields.Many2one(
        'res.country', string='Nationality'
    )

    degree_level = fields.Selection([
        ('bachelor', 'Bachelor'),
        ('master', 'Master'),
        ('phd', 'PhD / Doctorate'),
        ('diploma', '2-Year Diploma'),
    ], string='Degree Level')

    specialization = fields.Selection([
        ('medicine', 'Medicine'),
        ('dentistry', 'Dentistry'),
        ('pharmacy', 'Pharmacy'),
        ('nursing', 'Nursing'),
        ('veterinary', 'Veterinary Medicine'),
        ('civil_eng', 'Civil Engineering'),
        ('mechanical_eng', 'Mechanical Engineering'),
        ('electrical_eng', 'Electrical Engineering'),
        ('computer_eng', 'Computer Engineering'),
        ('software_eng', 'Software Engineering'),
        ('chemical_eng', 'Chemical Engineering'),
        ('architecture', 'Architecture'),
        ('business_admin', 'Business Administration'),
        ('accounting', 'Accounting & Finance'),
        ('economics', 'Economics'),
        ('marketing', 'Marketing'),
        ('law', 'Law'),
        ('political_science', 'Political Science'),
        ('psychology', 'Psychology'),
        ('sociology', 'Sociology'),
        ('computer_science', 'Computer Science'),
        ('mathematics', 'Mathematics'),
        ('physics', 'Physics'),
        ('chemistry', 'Chemistry'),
        ('biology', 'Biology'),
        ('education', 'Education'),
        ('english_lit', 'English Literature'),
        ('translation', 'Translation'),
        ('other', 'Other'),
    ], string='Academic Specialization')

    specialization_other = fields.Char(string='Other Specialization')

    # ── SPECIALIZATION DISPLAY ───────────────────────────────
    # Same logic as student.lead — shows readable name or custom text.

    specialization_display = fields.Char(
        string='Specialization',
        compute='_compute_specialization_display',
        store=True,
    )

    @api.depends('specialization', 'specialization_other')
    def _compute_specialization_display(self):
        spec_labels = dict(self._fields['specialization'].selection)
        for rec in self:
            if rec.specialization == 'other' and rec.specialization_other:
                rec.specialization_display = rec.specialization_other
            elif rec.specialization:
                rec.specialization_display = spec_labels.get(
                    rec.specialization, rec.specialization
                )
            else:
                rec.specialization_display = ''

    # ── STATUS AND BUDGET ────────────────────────────────────
    # Frozen snapshot of the student's status and budget at deletion time.

    status = fields.Selection([
        ('new', 'New Inquiry'),
        ('options_sent', 'Options Sent'),
        ('chosen', 'University Chosen'),
        ('docs', 'Collecting Documents'),
        ('enrolled', 'Enrolled'),
        ('lost', 'Lost'),
    ], string='Status at Deletion')

    currency_id = fields.Many2one('res.currency', string='Currency')
    budget_amount = fields.Monetary(
        string='Budget', currency_field='currency_id'
    )
    budget_min = fields.Monetary(
        string='Budget From', currency_field='currency_id'
    )
    budget_max = fields.Monetary(
        string='Budget To', currency_field='currency_id'
    )

    date_contacted = fields.Date(string='Date Contacted')
    follow_up_date = fields.Date(string='Follow-up Date')
    notes = fields.Text(string='Notes')

    # Who was originally assigned to this student
    user_id = fields.Many2one(
        'res.users', string='Originally Assigned To'
    )

    # ── DELETION METADATA ────────────────────────────────────
    # Who deleted this student, when, and why.
    # This data is added automatically by the delete wizard.

    deleted_by = fields.Many2one(
        'res.users',
        string='Deleted By',
        required=True,
        default=lambda self: self.env.user,
    )

    deleted_date = fields.Datetime(
        string='Deleted On',
        required=True,
        default=fields.Datetime.now,
    )

    delete_reason = fields.Selection([
        ('enrolled', 'Completed Enrollment'),
        ('paid', 'Paid Fees'),
        ('documents', 'Completed Document Upload'),
        ('other', 'Other'),
    ], string='Deletion Reason', required=True)

    delete_reason_text = fields.Text(string='Reason Details')

    can_restore = fields.Boolean(
        string='Can Restore',
        compute='_compute_can_restore',
        store=False,
    )

    @api.depends('deleted_by')
    def _compute_can_restore(self):
        for rec in self:
            is_manager = self.env.user.has_group(
                'university_crm.group_university_manager'
            )
            is_admin = self.env.user.has_group('base.group_system')
            is_owner = rec.deleted_by == self.env.user
            rec.can_restore = is_manager or is_admin or is_owner
    # Only managers can restore. Creates a new student.lead from
    # the archived data, then deletes the archive record.

    def action_restore(self):
        """Restore archived student back to active students list."""
        self.ensure_one()

        is_manager = self.env.user.has_group(
            'university_crm.group_university_manager'
        )
        is_admin = self.env.user.has_group('base.group_system')
        is_owner = self.deleted_by == self.env.user
        if not (is_manager or is_admin or is_owner):
            raise ValidationError(
                'Only managers or the employee who archived the student can restore it!'
            )

        # Re-create the student lead from archived data
        self.env['student.lead'].create({
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'phone2': self.phone2,
            'phone_country_id': self.phone_country_id.id,
            'country_id': self.country_id.id,
            'degree_level': self.degree_level,
            'specialization': self.specialization,
            'specialization_other': self.specialization_other,
            'status': self.status or 'new',
            'currency_id': self.currency_id.id,
            'budget_amount': self.budget_amount,
            'budget_min': self.budget_min,
            'budget_max': self.budget_max,
            'date_contacted': self.date_contacted,
            'follow_up_date': self.follow_up_date,
            'notes': self.notes,
            'user_id': self.user_id.id,
        })

        # Remove from archive after restoring
        self.unlink()

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'student.archive',
            'view_mode': 'list,form',
            'target': 'current',
        }

    # ── ACCESS CONTROL ───────────────────────────────────────
    # Employees only see students THEY deleted.
    # Managers and admin see all archived students.

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):
        is_manager = self.env.user.has_group(
            'university_crm.group_university_manager'
        )
        is_admin = self.env.user.has_group('base.group_system')
        if not is_manager and not is_admin:
            domain = [('deleted_by', '=', self.env.uid)] + list(domain)
        return super()._search(
            domain, offset=offset, limit=limit, order=order
        )
