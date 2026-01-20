from odoo import fields, models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    folio_ep_ids = fields.One2many(
        comodel_name="crm.lead.folio.ep",
        inverse_name="lead_id",
        string="Folio EP",
    )

    mobiliario = fields.Boolean(string="Mobiliario")
    flores = fields.Boolean(string="Flores")
    produccion = fields.Boolean(string="Producción")
