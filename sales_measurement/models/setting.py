# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"


    is_auto_confirm = fields.Boolean(string="Auto confirm SO when Production Payment or Payment Finalize",  )


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    is_auto_confirm = fields.Boolean(related="company_id.is_auto_confirm", readonly=False)
