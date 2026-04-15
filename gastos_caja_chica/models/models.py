# from odoo import models, fields, api


# class gastos_caja_chica(models.Model):
#     _name = 'gastos_caja_chica.gastos_caja_chica'
#     _description = 'gastos_caja_chica.gastos_caja_chica'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

