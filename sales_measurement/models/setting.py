# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    so_auto_confirm = fields.Selection(string="When to confirm SO",
                                       selection=[('production_payment', 'Production Payment'),
                                                  ('none', 'None'),
                                                  ('payment_finalize', 'Payment Finalize'), ],
                                       default='none')


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    so_auto_confirm = fields.Selection(related="company_id.so_auto_confirm", readonly=False)
