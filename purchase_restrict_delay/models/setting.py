# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    days_max_rfq = fields.Float(
        string='Max Days confirm RFQ',help="Max Days needed to confirm a RFQ")


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    days_max_rfq = fields.Float(related="company_id.days_max_rfq", readonly=False)
