# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    sale_order_id = fields.Many2one(comodel_name="sale.order", copy=False)
    show_credit_card = fields.Boolean(compute="_show_credit_card", store=True)
    credit_card_no = fields.Char()

    @api.constrains('sale_order_id', 'amount'
                    'sale_order_id.order_line', 'sale_order_id.paid_amount')
    def _check_sale_paid_amount(self):
        """
        Check if there is ale order with products with no bom and paid amount is above 75 %
        """
        for payment in self:
            sale_order = payment.sale_order_id
            if payment.currency_id == sale_order.currency_id:
                total_payment_amount = payment.amount + sale_order.paid_amount
            else:
                total_payment_amount = sale_order.paid_amount + sale_order.currency_id._convert(payment.amount, payment.currency_id, payment.company_id, payment.date)
            products_with_no_bom = payment.sale_order_id.order_line.mapped('product_id').filtered(lambda p: p.has_manufacture_route and not p.bom_ids)

            paid_percentage = (total_payment_amount / sale_order.amount_total) * 100 if sale_order.amount_total else 0.0

            if paid_percentage >= 75 and products_with_no_bom:
                raise ValidationError(_("There is no Bill of Material of type manufacture or kit found for the products {}."
                         " Please define a Bill of Material for those products.".format(products_with_no_bom.mapped("name"))))

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
