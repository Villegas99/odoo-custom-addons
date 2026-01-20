# from odoo import http


# class CrmPlanner1(http.Controller):
#     @http.route('/crm_planner1/crm_planner1', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/crm_planner1/crm_planner1/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('crm_planner1.listing', {
#             'root': '/crm_planner1/crm_planner1',
#             'objects': http.request.env['crm_planner1.crm_planner1'].search([]),
#         })

#     @http.route('/crm_planner1/crm_planner1/objects/<model("crm_planner1.crm_planner1"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('crm_planner1.object', {
#             'object': obj
#         })

