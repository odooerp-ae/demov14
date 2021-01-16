
from odoo import api, fields, models, _


class District(models.Model):
    _name = "res.district"

    name = fields.Char(string="", required=True)


class Partner(models.Model):
    _inherit = "res.partner"

    district = fields.Char(required=False)
    zone = fields.Char(string="منطقة", required=True)
    section = fields.Char(string="قطعة", required=True)
    building = fields.Char(string="المنزل", required=True)
    auto_confirm_rfq = fields.Boolean(copy=False, help="Confirm RQF generated automatic from this vendor")