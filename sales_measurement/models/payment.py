# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    sale_order_id = fields.Many2one(comodel_name="sale.order", copy=False)
    show_credit_card = fields.Boolean(compute="_show_credit_card", store=True)
    credit_card_no = fields.Char()

    @api.depends('journal_id')
    def _show_credit_card(self):
        for record in self:
            record.show_credit_card = True if record.journal_id and record.journal_id.type == 'bank' else False

    @api.depends('journal_id', 'sale_order_id')
    def _compute_currency_id(self):
        """
        Override to return default currency of sale order if exist
        """
        for pay in self:
            pay.currency_id = pay.sale_order_id.currency_id or pay.journal_id.currency_id or pay.journal_id.company_id.currency_id
