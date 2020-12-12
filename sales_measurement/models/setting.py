# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    is_auto_confirm = fields.Boolean(string="Auto confirm SO when Production Payment or Payment Finalize")
    add_production_payment = fields.Boolean(string="Add Production Payment for SO")


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    is_auto_confirm = fields.Boolean(related="company_id.is_auto_confirm", readonly=False)
    add_production_payment = fields.Boolean(related="company_id.add_production_payment", readonly=False)
