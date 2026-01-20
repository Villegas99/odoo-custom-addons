from odoo import fields, models


class CrmLeadFolioEp(models.Model):
    _name = "crm.lead.folio.ep"
    _description = "Folio EP"
    _rec_name = "name"

    lead_id = fields.Many2one(
        comodel_name="crm.lead",
        string="Lead",
        required=True,
        ondelete="cascade",
    )

    name = fields.Char(string="ID", required=True)
