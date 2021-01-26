# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    rfq_reminder_days = fields.Float(string='RFQ Reminder Days', help="Days used in send reminder mail to confirm a RFQ")
    po_delivery_reminder_days = fields.Float(string='PO Delivery Reminder Days', help="Days used in send reminder mail to complete PO Delivery")


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    rfq_reminder_days = fields.Float(related="company_id.rfq_reminder_days", readonly=False)
    po_delivery_reminder_days = fields.Float(related="company_id.po_delivery_reminder_days", readonly=False)
