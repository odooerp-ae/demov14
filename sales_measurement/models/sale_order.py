
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from odoo.tools import float_is_zero, float_compare
from datetime import datetime, timedelta


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
    is_final_approve = fields.Boolean(copy=False)
    planned_final_measurement_date = fields.Date(copy=False)
    actual_final_measurement_date = fields.Date(copy=False)
    final_approve_date = fields.Date(copy=False)

    @api.depends('state', 'order_line.invoice_status')
    def _get_invoice_status(self):
        """
        Compute the invoice status of a SO. Possible statuses:
        - no: if the SO is not in status 'sale' or 'done', we consider that there is nothing to
          invoice. This is also the default value if the conditions of no other status is met.
        - to invoice: if any SO line is 'to invoice', the whole SO is 'to invoice'
        - invoiced: if all SO lines are invoiced, the SO is invoiced.
        - upselling: if all SO lines are invoiced or upselling, the status is upselling.
        """
        unconfirmed_orders = self.filtered(lambda so: so.state not in ['sale','done','production_payment', 'payment_finalize'])
        unconfirmed_orders.invoice_status = 'no'
        confirmed_orders = self - unconfirmed_orders
        if not confirmed_orders:
            return
        line_invoice_status_all = [
            (d['order_id'][0], d['invoice_status'])
            for d in self.env['sale.order.line'].read_group([
                    ('order_id', 'in', confirmed_orders.ids),
                    ('is_downpayment', '=', False),
                    ('display_type', '=', False),
                ],
                ['order_id', 'invoice_status'],
                ['order_id', 'invoice_status'], lazy=False)]
        for order in confirmed_orders:
            line_invoice_status = [d[1] for d in line_invoice_status_all if d[0] == order.id]
            if order.state not in ('sale', 'done', 'production_payment', 'payment_finalize'):
                order.invoice_status = 'no'
            elif any(invoice_status == 'to invoice' for invoice_status in line_invoice_status):
                order.invoice_status = 'to invoice'
            elif line_invoice_status and all(invoice_status == 'invoiced' for invoice_status in line_invoice_status):
                order.invoice_status = 'invoiced'
            elif line_invoice_status and all(invoice_status in ('invoiced', 'upselling') for invoice_status in line_invoice_status):
                order.invoice_status = 'upselling'
            else:
                order.invoice_status = 'no'

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

    @api.constrains('planned_final_measurement_date', 'state')
    def _check_planned_final_measurement_date(self):
        for order in self:
            if order.state not in ('draft', 'sent', 'cancel', 'rejected') and not order.planned_final_measurement_date:
                raise UserError(_("You must insert Planned final measure date "))

    def action_set_to_final_measurement(self):
        self.state = 'final_measurement'
        self.actual_final_measurement_date = fields.Date.today()
        return True

    def action_final_approve(self):
        self.is_final_approve = True
        self.final_approve_date = fields.Date.today()

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

    def _force_lines_to_invoice_policy_order(self):
        for line in self.order_line:
            if self.state in ['sale', 'done', 'payment_finalize', 'production_payment']:
                line.qty_to_invoice = line.product_uom_qty - line.qty_invoiced
            else:
                line.qty_to_invoice = 0


