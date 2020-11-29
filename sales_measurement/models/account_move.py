# -*- coding: utf-8 -*-

from odoo import fields, models, api


class AccountMoveInherit(models.Model):
    _inherit = 'account.move'

    def _post(self, soft):
        result = super(AccountMoveInherit, self)._post(soft)

        for invoice in self:

            if not invoice.amount_residual:
                continue
            sale_line_ids = self.invoice_line_ids.mapped("sale_line_ids")
            if sale_line_ids:

                payments = self.env['account.payment'].search([('sale_order_id', 'in', sale_line_ids.mapped("order_id").ids)])

                for payment in payments:
                    if not invoice.amount_residual:
                        break
                    credit_line = payment.line_ids.filtered(
                        lambda l: l.credit and not l.reconciled
                    )
                    if credit_line:
                        invoice.js_assign_outstanding_line(credit_line.id)
        return result
