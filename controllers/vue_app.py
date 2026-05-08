import os
from odoo import http
from odoo.http import request


class VueApp(http.Controller):
    """Serve the built Vue SPA (dist/index.html) for any /app/* route.

    Vite writes to ../../static/dist relative to uni-crm, so the HTML lives
    at <module>/static/dist/index.html and Odoo serves the bundled JS/CSS
    automatically under /university_crm/static/dist/assets/...
    """

    _DIST_INDEX = "static/dist/index.html"

    def _module_root(self):
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    @http.route(["/app", "/app/<path:subpath>"], type="http", auth="public", methods=["GET"], csrf=False)
    def spa(self, subpath=None, **kw):
        index_path = os.path.join(self._module_root(), self._DIST_INDEX)
        try:
            with open(index_path, "rb") as f:
                html = f.read()
        except FileNotFoundError:
            return request.make_response(
                "Vue bundle not found. Run `npm run build` in uni-crm-odoo-final/uni-crm/.",
                headers=[("Content-Type", "text/plain; charset=utf-8")],
                status=404,
            )
        return request.make_response(
            html,
            headers=[
                ("Content-Type", "text/html; charset=utf-8"),
                ("Cache-Control", "no-cache"),
            ],
        )
