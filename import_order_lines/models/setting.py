# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    create_product_import = fields.Boolean(string="Auto create product when import")


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    create_product_import = fields.Boolean(related="company_id.create_product_import", readonly=False)
