# -*- coding: utf-8 -*-

from odoo import fields, models, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    sale_order_id = fields.Many2one(comodel_name="sale.order", compute="_get_sale_id",
                                    string="Contract Ref.", store=False)

    @api.depends('sale_line_ids', 'sale_line_ids.order_id')
    def _get_sale_id(self):
        for record in self:
            if record.sale_line_ids:
                record.sale_order_id = record.sale_line_ids.order_id.id
            else:
                record.sale_order_id = False


class AccountMoveInherit(models.Model):
    _inherit = 'account.move'

    def _post(self, soft=True):
        # OVERRIDE
        # Auto-reconcile the invoice with payments coming from sale payments.
        posted = super()._post(soft)

        for invoice in posted.filtered(lambda move: move.is_invoice()):
            if not invoice.amount_residual:
                continue
            sale_line_ids = self.invoice_line_ids.mapped("sale_line_ids")
            if sale_line_ids:

                payments = self.env['account.payment'].search(
                    [('sale_order_id', 'in', sale_line_ids.mapped("order_id").ids)])

                for payment in payments:
                    if not invoice.amount_residual:
                        break
                    credit_line = payment.line_ids.filtered(
                        lambda l: l.credit and not l.reconciled
                    )
                    if credit_line:
                        invoice.js_assign_outstanding_line(credit_line.id)
        return posted
