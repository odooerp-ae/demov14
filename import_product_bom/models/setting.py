# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    allow_import_bom = fields.Boolean(string="Allow import BOM in sales orders")


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    allow_import_bom = fields.Boolean(related="company_id.allow_import_bom", readonly=False)
