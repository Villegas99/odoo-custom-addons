# from odoo import http


# class GastosCajaChica(http.Controller):
#     @http.route('/gastos_caja_chica/gastos_caja_chica', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/gastos_caja_chica/gastos_caja_chica/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('gastos_caja_chica.listing', {
#             'root': '/gastos_caja_chica/gastos_caja_chica',
#             'objects': http.request.env['gastos_caja_chica.gastos_caja_chica'].search([]),
#         })

#     @http.route('/gastos_caja_chica/gastos_caja_chica/objects/<model("gastos_caja_chica.gastos_caja_chica"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('gastos_caja_chica.object', {
#             'object': obj
#         })

