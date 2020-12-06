
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta


class SaleOrder(models.Model):
    _inherit = "sale.order"

    measure_request_id = fields.Many2one(comodel_name="measurement.request", copy=False)
    state = fields.Selection([
        ('draft', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Contract'),
        ('advance_payment', 'Advance Payment'),
        ('final_measurement', 'Final Measurement'),
        ('production_payment', 'Production Payment'),
        ('payment_finalize', 'Payment Finalize'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
        ('rejected', 'Rejected'),
    ], string='Status', readonly=True, copy=False, index=True, tracking=3, default='draft')
    payment_ids = fields.One2many(comodel_name="account.payment", inverse_name="sale_order_id", copy=False)

    paid_amount = fields.Monetary(string="Total Paid Amount", compute='_compute_payment_amount', store=True)
    unpaid_amount = fields.Monetary(string="Total Unpaid Amount", compute='_compute_payment_amount', store=True)
    paid_amount_percent = fields.Float(compute='_compute_payment_amount', store=True, string="Paid %")
    reject_reason_id = fields.Many2one(comodel_name="sale.order.reject", string="Reject Reason", copy=False)
    is_auto_rejected = fields.Boolean(copy=False)
    so_auto_confirm = fields.Selection(related="company_id.so_auto_confirm", store=True)

    @api.depends('payment_ids.amount',
                 'payment_ids.state', 'amount_total', 'state')
    def _compute_payment_amount(self):
        for rec in self:
            paid_amount = 0.0
            payments = rec.payment_ids.filtered(lambda p:p.state == 'posted')
            for payment in payments:
                paid_amount += payment.currency_id._convert(payment.amount, rec.currency_id, self.company_id, rec.date_order)

            rec.paid_amount = paid_amount

            rec.paid_amount_percent = (paid_amount / rec.amount_total) * 100 if rec.amount_total else 0.0
            rec.unpaid_amount = rec.amount_total - paid_amount if paid_amount <= rec.amount_total else 0

            if rec.paid_amount_percent > 0.0 and rec.state in ['draft', 'sent']:
                rec.state = 'advance_payment'

            elif rec.paid_amount_percent >= 75 and rec.paid_amount_percent < 100 and rec.state == 'final_measurement':
                rec.state = 'production_payment'

            elif rec.paid_amount_percent >= 100 and rec.state == 'final_measurement':
                rec.state = 'payment_finalize'

    def action_set_to_final_measurement(self):
        self.state = 'final_measurement'
        return True

    def action_so_register_payment(self):
        journal_id = self.env['account.move']._search_default_journal(('bank', 'cash'))
        ctx = {
            'default_sale_order_id': self.id,
            'default_partner_id': self.partner_id.id,
            'default_payment_type': 'inbound',
            'default_partner_type': 'customer',
            'default_amount': self.unpaid_amount,
            'default_journal_id': journal_id.id,
        }

        return {
                'name': _('Register Payment'),
                'res_model': 'account.payment',
                'view_mode': 'form',
                'view_id': self.env.ref('sales_measurement.view_sale_account_payment_register_form').id,
                'context': ctx,
                'target': 'new',
                'type': 'ir.actions.act_window',
            }

    def action_view_payments(self):
        action_ref = 'account.action_account_payments'
        ctx = self.env.context.copy()
        action = self.env['ir.actions.act_window']._for_xml_id(action_ref)
        ctx.update({
            'default_sale_order_id': self.id,
            'default_partner_id': self.partner_id.id,
            'default_amount': self.unpaid_amount,
        })
        action['domain'] = [('id', 'in', self.mapped('payment_ids').ids)]
        action['context'] = ctx
        return action

    def _so_auto_reject(self):
        date = fields.Datetime.now() - relativedelta(months=3)
        orders = self.sudo().search([('date_order','<=', date), ('state', 'in', ['draft', 'sent'])])
        orders.write({"state": 'rejected',
                      "reject_reason_id":  self.env.ref("sales_measurement.so_auto_rejected").id,
                      "is_auto_rejected": True,
        })
        return True

    def _check_auto_confirm(self):
        so_auto_confirm = self.env.company.so_auto_confirm

        if so_auto_confirm != 'none':
            auto_orders = self.filtered(lambda s: s.state == so_auto_confirm)
            auto_orders.action_confirm()
        return True
