
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta


class ProductTemplate(models.Model):
    _inherit = "product.template"

    type = fields.Selection(default='product')


class SaleOrder(models.Model):
    _inherit = "sale.order"

    measure_request_id = fields.Many2one(comodel_name="measurement.request", copy=False)
    state = fields.Selection(selection_add=[('advance_payment', 'Advance Payment'),
                                            ('final_measurement', 'Final Measurement'),
                                            ('production_payment', 'Production Payment'),
                                            ('payment_finalize', 'Payment Finalize'),
                                            ('rejected', 'Rejected'),
                                            ],
                             )
    payment_ids = fields.One2many(comodel_name="account.payment", inverse_name="sale_order_id", copy=False)

    paid_amount = fields.Monetary(string="Total Paid Amount", compute='_compute_payment_amount', store=True)
    unpaid_amount = fields.Monetary(string="Total Unpaid Amount", compute='_compute_payment_amount', store=True)
    paid_amount_percent = fields.Float(compute='_compute_payment_amount', store=True, string="Payments %")
    reject_reason_id = fields.Many2one(comodel_name="sale.order.reject", string="Reject Reason", copy=False)
    is_auto_rejected = fields.Boolean(copy=False)
    is_auto_confirm = fields.Boolean(related="company_id.is_auto_confirm", store=True)
    quotation_ref = fields.Char(copy=False, compute="_get_quotation_ref", store=True)
    last_state = fields.Char(copy=False)
    is_confirmed = fields.Boolean(copy=False)
    planned_final_measurement_date = fields.Date(string="", required=False, )
    actual_final_measurement_date = fields.Date(string="", required=False, )

    @api.depends('name', 'state')
    def _get_quotation_ref(self):
        for record in self:
            if record.name and record.state in ['draft', 'sent']:
                record.quotation_ref = record.name
            else:
                record.quotation_ref = record.quotation_ref

    @api.depends('payment_ids.amount',
                 'payment_ids.state', 'amount_total', 'state')
    def _compute_payment_amount(self):
        for rec in self:
            paid_amount = 0.0
            payments = rec.payment_ids.filtered(lambda p:p.state == 'posted')
            for payment in payments:
                paid_amount += payment.currency_id._convert(payment.amount, rec.currency_id, rec.company_id, rec.date_order)

            rec.paid_amount = paid_amount

            rec.paid_amount_percent = (paid_amount / rec.amount_total) * 100 if rec.amount_total else 0.0
            rec.unpaid_amount = rec.amount_total - paid_amount if paid_amount <= rec.amount_total else 0

            if rec.paid_amount_percent > 0.0 and rec.state in ['draft', 'sent']:
                rec.state = 'advance_payment'
                if not rec.company_id.keep_name_so:
                    rec.quotation_ref = rec.name
                    rec.name = self.env["ir.sequence"].next_by_code("sale.order")

            elif rec.paid_amount_percent >= 100 and rec.state in ['final_measurement', 'production_payment']:
                rec.state = 'payment_finalize'

            elif rec.paid_amount_percent >= 75 and rec.paid_amount_percent < 100 and \
                rec.state == 'final_measurement' and rec.company_id.add_production_payment:
                rec.state = 'production_payment'

    def action_set_to_final_measurement(self):
        self.state = 'final_measurement'
        self.actual_final_measurement_date = fields.Date.today()
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
        is_auto_confirm = self.env.company.is_auto_confirm
        if is_auto_confirm:
            auto_orders = self.filtered(lambda s: s.state in ['payment_finalize', 'production_payment']
                                                  and not s.is_confirmed)
            auto_orders.action_confirm()
        return True

    def action_confirm(self):
        """
        Override to keep state as is after confirm
        """
        result = super(SaleOrder, self).action_confirm()
        for order in self:
            order.state = order.last_state
            order.is_confirmed = True
        return result

    def write(self, values):
        if values.get('state') == 'sale':
            for record in self:
                values['last_state'] = record.state
        return super(SaleOrder, self).write(values)

