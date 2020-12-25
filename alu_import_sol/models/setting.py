# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    alu_import_so_lines = fields.Boolean(string="Aluminum import SOL")


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    alu_import_so_lines = fields.Boolean(related="company_id.alu_import_so_lines", readonly=False)
