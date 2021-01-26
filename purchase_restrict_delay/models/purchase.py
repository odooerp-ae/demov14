# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from dateutil.relativedelta import relativedelta


class Purchase(models.Model):
    _inherit = "purchase.order"

    def _send_rfq_confirm_reminder_mail(self):
        template = self.env.ref('purchase_restrict_delay.email_template_rfq_confirm_reminder', raise_if_not_found=False)
        if template:

            orders = self.search([('state', 'in', ['draft', 'sent']),
        ]).filtered(lambda p: ((p.date_order + relativedelta(days=p.company_id.rfq_reminder_days)).date()) <= fields.Date.today())
            for order in orders:
                order.with_context(is_reminder=True).message_post_with_template(template.id, email_layout_xmlid=None,

                                                                                composition_mode='comment')

    def _send_po_delivery_reminder_mail(self):
        template = self.env.ref('purchase_restrict_delay.email_template_po_delivery_reminder', raise_if_not_found=False)
        if template:

            orders = self.search([('state', 'in', ['purchase', 'done']),
                                  ('picking_count', '>=', 1),
        ]).filtered(lambda p: not p.is_shipped and ((p.date_planned + relativedelta(days=p.company_id.po_delivery_reminder_days)).date()) <= fields.Date.today())
            for order in orders:
                order.with_context(is_reminder=True).message_post_with_template(template.id, email_layout_xmlid=None,
                                                                                composition_mode='comment')
