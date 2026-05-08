import base64
import hashlib
from odoo import http
from odoo.http import content_disposition, request


class StudentPortal(http.Controller):

    # ── HELPERS ──────────────────────────────────────────────

    def _hash_password(self, password):
        """SHA-256 hash with a fixed salt prefix."""
        salted = f'univ_crm_salt_{password}'
        return hashlib.sha256(salted.encode()).hexdigest()

    def _get_authenticated_student(self, token):
        """Return student only if token matches and session is authenticated."""
        if not token:
            return None
        student = request.env['student.lead'].sudo().search(
            [('portal_token', '=', token)], limit=1
        )
        if not student:
            return None
        session_token = request.session.get('student_token')
        if session_token != token:
            return None
        return student

    def _get_student_by_token(self, token):
        if not token:
            return None
        return request.env['student.lead'].sudo().search(
            [('portal_token', '=', token)], limit=1
        )

    def _m2o(self, value):
        return [value.id, value.display_name] if value else False

    def _serialize_student(self, student):
        return {
            'id': student.id,
            'name': student.name,
            'email': student.email or False,
            'phone_full': student.phone_full or False,
            'country_id': self._m2o(student.country_id),
            'user_id': self._m2o(student.user_id),
            'degree_level': student.degree_level or False,
            'specialization_display': student.specialization_display or False,
            'status': student.status,
            'date_contacted': str(student.date_contacted) if student.date_contacted else False,
            'follow_up_date': str(student.follow_up_date) if student.follow_up_date else False,
            'notes': student.notes or False,
            'portal_token': student.portal_token or False,
            'budget_display': student.budget_display or False,
            'currency_id': self._m2o(student.currency_id),
        }

    def _serialize_attachment(self, attachment):
        return {
            'id': attachment.id,
            'name': attachment.name,
            'mimetype': attachment.mimetype or 'application/octet-stream',
            'file_size': attachment.file_size,
            'create_date': str(attachment.create_date) if attachment.create_date else False,
            'res_model': attachment.res_model,
            'res_id': attachment.res_id,
        }

    def _portal_attachments(self, student):
        attachments = request.env['ir.attachment'].sudo().search([
            ('res_model', '=', 'student.lead'),
            ('res_id', '=', student.id),
        ], order='create_date desc')
        return attachments

    @http.route('/student/api/<string:token>', type='http', auth='public',
                methods=['GET'], csrf=False)
    def student_portal_api(self, token, **kwargs):
        student = self._get_student_by_token(token)
        if not student:
            return request.make_json_response(
                {'error': 'This portal link is invalid or has expired.'},
                status=404,
            )

        attachments = [
            self._serialize_attachment(attachment)
            for attachment in self._portal_attachments(student)
        ]
        return request.make_json_response({
            'student': self._serialize_student(student),
            'attachments': attachments,
        })

    @http.route('/student/api/<string:token>/upload', type='http', auth='public',
                methods=['POST'], csrf=False)
    def student_portal_upload_api(self, token, **kwargs):
        student = self._get_student_by_token(token)
        if not student:
            return request.make_json_response(
                {'error': 'This portal link is invalid or has expired.'},
                status=404,
            )

        files = request.httprequest.files.getlist('files')
        if not files:
            return request.make_json_response(
                {'error': 'Please choose at least one file to upload.'},
                status=400,
            )

        uploaded = 0
        for file_storage in files:
            if not file_storage.filename:
                continue
            file_storage.stream.seek(0)
            data = file_storage.stream.read()
            request.env['ir.attachment'].sudo().create({
                'name': file_storage.filename,
                'datas': base64.b64encode(data),
                'res_model': 'student.lead',
                'res_id': student.id,
                'mimetype': file_storage.content_type,
            })
            uploaded += 1

        attachments = [
            self._serialize_attachment(attachment)
            for attachment in self._portal_attachments(student)
        ]
        return request.make_json_response({
            'ok': True,
            'uploaded': uploaded,
            'attachments': attachments,
        })

    @http.route('/student/api/<string:token>/attachment/<int:attachment_id>',
                type='http', auth='public', methods=['GET'], csrf=False)
    def student_portal_attachment_download(self, token, attachment_id, **kwargs):
        student = self._get_student_by_token(token)
        if not student:
            return request.not_found()

        attachment = request.env['ir.attachment'].sudo().search([
            ('id', '=', attachment_id),
            ('res_model', '=', 'student.lead'),
            ('res_id', '=', student.id),
        ], limit=1)
        if not attachment:
            return request.not_found()

        file_content = base64.b64decode(attachment.datas or b'')
        headers = [
            ('Content-Type', attachment.mimetype or 'application/octet-stream'),
            ('Content-Disposition', content_disposition(attachment.name or 'document')),
        ]
        return request.make_response(file_content, headers=headers)


        # ── EMPLOYEE UPLOAD (no CSRF required for SPA uploads from authenticated users)
        @http.route('/employee/student/<int:student_id>/upload', type='http', auth='user', methods=['POST'], csrf=False)
        def employee_student_upload(self, student_id, **kwargs):
            files = request.httprequest.files.getlist('files')
            if not files:
                return request.make_json_response({'error': 'Please choose at least one file to upload.'}, status=400)

            uploaded = []
            for file_storage in files:
                if not file_storage.filename:
                    continue
                file_storage.stream.seek(0)
                data = file_storage.stream.read()
                attachment = request.env['ir.attachment'].sudo().create({
                    'name': file_storage.filename,
                    'datas': base64.b64encode(data),
                    'res_model': 'student.lead',
                    'res_id': student_id,
                    'mimetype': file_storage.content_type,
                })
                uploaded.append(self._serialize_attachment(attachment))

            return request.make_json_response({
                'ok': True,
                'uploaded': len(uploaded),
                'attachments': uploaded,
            })

    # ── LOGIN PAGE (GET) ─────────────────────────────────────

    @http.route('/student/login', type='http', auth='public', website=True, methods=['GET'])
    def student_login_page(self, token=None, **kwargs):
        """
        Show login page.
        If token is given, pre-fill the email (looked up from token).
        """
        # Already logged in? Go straight to dashboard.
        if token and request.session.get('student_token') == token:
            return request.redirect(f'/student/dashboard/{token}')

        email = ''
        if token:
            student = request.env['student.lead'].sudo().search(
                [('portal_token', '=', token)], limit=1
            )
            if student:
                email = student.email or ''

        return request.render('university_crm.student_login', {
            'token': token or '',
            'email': email,
            'error': kwargs.get('error', ''),
        })

    # ── LOGIN (POST) ─────────────────────────────────────────

    @http.route('/student/login', type='http', auth='public', website=True, methods=['POST'])
    def student_login_submit(self, email=None, password=None, token=None, **kwargs):
        """
        Authenticate student by email + password.
        Token is optional — used when coming from a portal link.
        """
        email = (email or '').strip().lower()
        password = password or ''

        student = request.env['student.lead'].sudo().search(
            [('email', '=ilike', email)], limit=1
        )

        if not student:
            return request.render('university_crm.student_login', {
                'token': token or '',
                'email': email,
                'error': 'No account found with that email address.',
            })

        # Check if password is set
        if not student.portal_password_hash:
            # Redirect to set-password page
            return request.redirect(
                f'/student/set-password/{student.portal_token}?first=1'
            )

        # Verify password
        expected = self._hash_password(password)
        if student.portal_password_hash != expected:
            return request.render('university_crm.student_login', {
                'token': token or '',
                'email': email,
                'error': 'Incorrect password. Please try again.',
            })

        # Success — store token in session
        request.session['student_token'] = student.portal_token
        return request.redirect(f'/student/dashboard/{student.portal_token}')

    # ── SET / CHANGE PASSWORD (GET) ──────────────────────────

    @http.route('/student/set-password/<string:token>', type='http',
                auth='public', website=True, methods=['GET'])
    def student_set_password_page(self, token, **kwargs):
        """
        Show set-password page.
        Works for first-time setup and for password changes.
        Only accessible via the portal token link.
        """
        student = request.env['student.lead'].sudo().search(
            [('portal_token', '=', token)], limit=1
        )
        if not student:
            return request.render('university_crm.student_login', {
                'token': '',
                'email': '',
                'error': 'Invalid or expired link.',
            })

        is_first = kwargs.get('first', '0') == '1' or not student.portal_password_hash

        return request.render('university_crm.student_set_password', {
            'student': student,
            'token': token,
            'is_first': is_first,
            'error': kwargs.get('error', ''),
        })

    # ── SET PASSWORD (POST) ──────────────────────────────────

    @http.route('/student/set-password/<string:token>', type='http',
                auth='public', website=True, methods=['POST'])
    def student_set_password_submit(self, token, password=None, password2=None, **kwargs):
        """Save the student's new password and log them in."""
        student = request.env['student.lead'].sudo().search(
            [('portal_token', '=', token)], limit=1
        )
        if not student:
            return request.redirect('/student/login')

        password = password or ''
        password2 = password2 or ''

        if len(password) < 6:
            return request.render('university_crm.student_set_password', {
                'student': student,
                'token': token,
                'is_first': not student.portal_password_hash,
                'error': 'Password must be at least 6 characters.',
            })

        if password != password2:
            return request.render('university_crm.student_set_password', {
                'student': student,
                'token': token,
                'is_first': not student.portal_password_hash,
                'error': 'Passwords do not match.',
            })

        # Save hashed password
        student.write({
            'portal_password_hash': self._hash_password(password)
        })

        # Log them in
        request.session['student_token'] = token
        return request.redirect(f'/student/dashboard/{token}')

    # ── DASHBOARD ────────────────────────────────────────────

    @http.route('/student/dashboard/<string:token>', type='http',
                auth='public', website=True, methods=['GET'])
    def student_dashboard(self, token, **kwargs):
        """
        Student dashboard — requires session auth.
        Token in URL + token in session must match.
        No Odoo employee login required.
        """
        student = self._get_authenticated_student(token)
        if not student:
            # Not logged in — redirect to login with token pre-filled
            return request.redirect(f'/student/login?token={token}')

        attachments = request.env['ir.attachment'].sudo().search([
            ('res_model', '=', 'student.lead'),
            ('res_id', '=', student.id),
        ])

        return request.render('university_crm.student_dashboard', {
            'student': student,
            'attachments': attachments,
            'token': token,
        })

    # ── FILE UPLOAD ──────────────────────────────────────────

    @http.route('/student/dashboard/<string:token>/upload', type='http',
                auth='public', website=True, methods=['POST'], csrf=True)
    def student_upload_file(self, token, **kwargs):
        """Handle file uploads from dashboard. Requires session auth."""
        student = self._get_authenticated_student(token)
        if not student:
            return request.redirect(f'/student/login?token={token}')

        files = kwargs.get('files')
        if files:
            if not isinstance(files, list):
                files = [files]
            for f in files:
                if f.filename:
                    f.stream.seek(0)
                    data = f.stream.read()
                    request.env['ir.attachment'].sudo().create({
                        'name': f.filename,
                        'datas': base64.b64encode(data),
                        'res_model': 'student.lead',
                        'res_id': student.id,
                        'mimetype': f.content_type,
                    })

        return request.redirect(f'/student/dashboard/{token}')

    # ── LOGOUT ───────────────────────────────────────────────

    @http.route('/student/logout', type='http', auth='public', website=True, methods=['GET'])
    def student_logout(self, **kwargs):
        """Clear student session and redirect to login."""
        token = request.session.pop('student_token', None)
        if token:
            return request.redirect(f'/student/login?token={token}')
        return request.redirect('/student/login')

    # ── EMPLOYEE/MANAGER LOGIN API ───────────────────────────

    @http.route('/api/auth/check-password', type='json', auth='public', methods=['POST'], csrf=False)
    def api_check_password(self, login):
        """Check if user has set a custom password."""
        user = request.env['res.users'].sudo().search([
            '|',
            ('login', '=', login),
            ('email', '=', login),
        ], limit=1)
        
        if not user:
            return {'error': 'User not found'}
        
        return {
            'has_custom_password': user.has_custom_password,
            'login': user.login,
            'name': user.name,
        }

    @http.route('/api/auth/set-password', type='json', auth='public', methods=['POST'], csrf=False)
    def api_set_password(self, login, password, password2):
        """Set custom password for first-time login."""
        user = request.env['res.users'].sudo().search([
            '|',
            ('login', '=', login),
            ('email', '=', login),
        ], limit=1)
        
        if not user:
            return {'error': 'User not found'}
        
        if not password or len(password) < 6:
            return {'error': 'Password must be at least 6 characters'}
        
        if password != password2:
            return {'error': 'Passwords do not match'}
        
        try:
            user.set_custom_password(password)
            return {'ok': True, 'message': 'Password set successfully'}
        except Exception as e:
            return {'error': str(e)}

    @http.route('/api/auth/login', type='json', auth='public', methods=['POST'], csrf=False)
    def api_login(self, login, password):
        """Authenticate employee/manager with email/login and custom password."""
        user = request.env['res.users'].sudo().search([
            '|',
            ('login', '=', login),
            ('email', '=', login),
        ], limit=1)
        
        if not user:
            return {'error': 'Invalid credentials'}
        
        if not user.has_custom_password:
            return {'error': 'Password not set'}
        
        if not user.verify_custom_password(password):
            return {'error': 'Invalid credentials'}
        
        # Set session
        request.session.uid = user.id
        request.session.db = request.env.cr.dbname
        request.session.login = user.login
        
        return {
            'ok': True,
            'uid': user.id,
            'login': user.login,
            'name': user.name,
        }

    @http.route('/api/auth/change-password', type='json', auth='user', methods=['POST'], csrf=False)
    def api_change_password(self, old_password, new_password, new_password2):
        """Change password for logged-in user."""
        user = request.env.user
        
        if not user.verify_custom_password(old_password):
            return {'error': 'Current password is incorrect'}
        
        if not new_password or len(new_password) < 6:
            return {'error': 'New password must be at least 6 characters'}
        
        if new_password != new_password2:
            return {'error': 'New passwords do not match'}
        
        try:
            user.set_custom_password(new_password)
            return {'ok': True, 'message': 'Password changed successfully'}
        except Exception as e:
            return {'error': str(e)}

    # ── STUDENT PORTAL API ───────────────────────────────────

    @http.route('/student/api/<string:token>/check-password', type='http', auth='public', methods=['GET'], csrf=False)
    def student_check_password(self, token, **kwargs):
        student = self._get_student_by_token(token)
        if not student:
            return request.make_json_response({'error': 'Invalid token'}, status=404)
        return request.make_json_response({
            'has_password': bool(student.portal_password_hash),
            'email': student.email or False,
        })

    @http.route('/student/api/<string:token>/login', type='http', auth='public', methods=['POST'], csrf=False)
    def student_api_login(self, token, **kwargs):
        import json
        try:
            body = json.loads(request.httprequest.data)
        except Exception:
            return request.make_json_response({'error': 'Invalid request'}, status=400)
        email = (body.get('email') or '').strip().lower()
        password_hash = body.get('password_hash') or ''
        student = self._get_student_by_token(token)
        if not student:
            return request.make_json_response({'error': 'Invalid token'}, status=404)
        if not student.portal_password_hash:
            return request.make_json_response({'error': 'No password set. Please set your password first.'})
        if student.portal_password_hash != password_hash:
            return request.make_json_response({'error': 'Incorrect password. Please try again.'})
        if student.email and student.email.lower() != email:
            return request.make_json_response({'error': 'Email does not match.'})
        attachments = [self._serialize_attachment(a) for a in self._portal_attachments(student)]
        return request.make_json_response({
            'ok': True,
            'student': self._serialize_student(student),
            'attachments': attachments,
        })

    @http.route('/student/api/<string:token>/set-password', type='http', auth='public', methods=['POST'], csrf=False)
    def student_api_set_password(self, token, **kwargs):
        import json
        try:
            body = json.loads(request.httprequest.data)
        except Exception:
            return request.make_json_response({'error': 'Invalid request'}, status=400)
        password_hash = body.get('password_hash') or ''
        if not password_hash:
            return request.make_json_response({'error': 'Password is required'})
        student = self._get_student_by_token(token)
        if not student:
            return request.make_json_response({'error': 'Invalid link'}, status=404)
        student.sudo().write({'portal_password_hash': password_hash})
        return request.make_json_response({'ok': True})
        


    # ── LEGACY TOKEN REDIRECT ────────────────────────────────
    # Old /my/application/<token> links still work — redirect to new login.

    @http.route('/my/application/<string:token>', type='http', auth='public', website=True)
    def legacy_portal_redirect(self, token, **kwargs):
        """Redirect old portal links to new login page."""
        student = request.env['student.lead'].sudo().search(
            [('portal_token', '=', token)], limit=1
        )
        if not student:
            return request.render('university_crm.student_login', {
                'token': '',
                'email': '',
                'error': 'This link is invalid or has expired.',
            })
        # If already authenticated, go to dashboard
        if request.session.get('student_token') == token:
            return request.redirect(f'/student/dashboard/{token}')
        # Otherwise go to login
        return request.redirect(f'/student/login?token={token}')
