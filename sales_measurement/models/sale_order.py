
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


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'


    def _expected_date(self):
        self.ensure_one()
        order_date = fields.Datetime.from_string(self.order_id.date_order if self.order_id.state in ['sale', 'done', 'payment_finalize', 'production_payment'] else fields.Datetime.now())
        return order_date + timedelta(days=self.customer_lead or 0.0)

    @api.depends('qty_invoiced', 'qty_delivered', 'product_uom_qty', 'order_id.state', 'order_id.write_date')
    def _get_to_invoice_qty(self):
        """
        Compute the quantity to invoice. If the invoice policy is order, the quantity to invoice is
        calculated from the ordered quantity. Otherwise, the quantity delivered is used.
        """
        for line in self:
            if line.order_id.state not in ['cancel', 'rejected']:
                if line.product_id.invoice_policy == 'order':
                    line.qty_to_invoice = line.product_uom_qty - line.qty_invoiced
                else:
                    line.qty_to_invoice = line.qty_delivered - line.qty_invoiced
            else:
                line.qty_to_invoice = 0

    @api.depends('state', 'product_uom_qty', 'qty_delivered', 'qty_to_invoice', 'qty_invoiced')
    def _compute_invoice_status(self):
        """
        Compute the invoice status of a SO line. Possible statuses:
        - no: if the SO is not in status 'sale' or 'done', we consider that there is nothing to
          invoice. This is also hte default value if the conditions of no other status is met.
        - to invoice: we refer to the quantity to invoice of the line. Refer to method
          `_get_to_invoice_qty()` for more information on how this quantity is calculated.
        - upselling: this is possible only for a product invoiced on ordered quantities for which
          we delivered more than expected. The could arise if, for example, a project took more
          time than expected but we decided not to invoice the extra cost to the client. This
          occurs onyl in state 'sale', so that when a SO is set to done, the upselling opportunity
          is removed from the list.
        - invoiced: the quantity invoiced is larger or equal to the quantity ordered.
        """
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for line in self:
            if line.state not in ('sale', 'done', 'payment_finalize', 'production_payment'):
                line.invoice_status = 'no'
            elif line.is_downpayment and line.untaxed_amount_to_invoice == 0:
                line.invoice_status = 'invoiced'
            elif not float_is_zero(line.qty_to_invoice, precision_digits=precision):
                line.invoice_status = 'to invoice'
            elif line.state in ('sale', 'payment_finalize', 'production_payment') and line.product_id.invoice_policy == 'order' and \
                            float_compare(line.qty_delivered, line.product_uom_qty, precision_digits=precision) == 1:
                line.invoice_status = 'upselling'
            elif float_compare(line.qty_invoiced, line.product_uom_qty, precision_digits=precision) >= 0:
                line.invoice_status = 'invoiced'
            else:
                line.invoice_status = 'no'

    @api.depends('state')
    def _compute_product_uom_readonly(self):
        for line in self:
            line.product_uom_readonly = line.state in ['sale', 'done', 'cancel', 'payment_finalize', 'production_payment', 'rejected']


    @api.depends('state', 'price_reduce', 'product_id', 'untaxed_amount_invoiced', 'qty_delivered', 'product_uom_qty')
    def _compute_untaxed_amount_to_invoice(self):
        """ Total of remaining amount to invoice on the sale order line (taxes excl.) as
                total_sol - amount already invoiced
            where Total_sol depends on the invoice policy of the product.

            Note: Draft invoice are ignored on purpose, the 'to invoice' amount should
            come only from the SO lines.
        """
        for line in self:
            amount_to_invoice = 0.0
            if line.state in ['sale', 'done', 'payment_finalize', 'production_payment']:
                # Note: do not use price_subtotal field as it returns zero when the ordered quantity is
                # zero. It causes problem for expense line (e.i.: ordered qty = 0, deli qty = 4,
                # price_unit = 20 ; subtotal is zero), but when you can invoice the line, you see an
                # amount and not zero. Since we compute untaxed amount, we can use directly the price
                # reduce (to include discount) without using `compute_all()` method on taxes.
                price_subtotal = 0.0
                if line.product_id.invoice_policy == 'delivery':
                    price_subtotal = line.price_reduce * line.qty_delivered
                else:
                    price_subtotal = line.price_reduce * line.product_uom_qty
                if len(line.tax_id.filtered(lambda tax: tax.price_include)) > 0:
                    # As included taxes are not excluded from the computed subtotal, `compute_all()` method
                    # has to be called to retrieve the subtotal without them.
                    # `price_reduce_taxexcl` cannot be used as it is computed from `price_subtotal` field. (see upper Note)
                    price_subtotal = line.tax_id.compute_all(price_subtotal)['total_excluded']

                if any(line.invoice_lines.mapped(lambda l: l.discount != line.discount)):
                    # In case of re-invoicing with different discount we try to calculate manually the
                    # remaining amount to invoice
                    amount = 0
                    for l in line.invoice_lines:
                        if len(l.tax_ids.filtered(lambda tax: tax.price_include)) > 0:
                            amount += l.tax_ids.compute_all(l.currency_id._convert(l.price_unit, line.currency_id, line.company_id, l.date or fields.Date.today(), round=False) * l.quantity)['total_excluded']
                        else:
                            amount += l.currency_id._convert(l.price_unit, line.currency_id, line.company_id, l.date or fields.Date.today(), round=False) * l.quantity

                    amount_to_invoice = max(price_subtotal - amount, 0)
                else:
                    amount_to_invoice = price_subtotal - line.untaxed_amount_invoiced

            line.untaxed_amount_to_invoice = amount_to_invoice

    def _check_line_unlink(self):
        """
        Check wether a line can be deleted or not.

        Lines cannot be deleted if the order is confirmed; downpayment
        lines who have not yet been invoiced bypass that exception.
        :rtype: recordset sale.order.line
        :returns: set of lines that cannot be deleted
        """
        return self.filtered(lambda line: line.state in ('sale', 'done', 'payment_finalize', 'production_payment') and (line.invoice_lines or not line.is_downpayment))

    @api.depends('product_id', 'order_id.state', 'qty_invoiced', 'qty_delivered')
    def _compute_product_updatable(self):
        for line in self:
            if line.state in ['done', 'cancel'] or (line.state in ('sale', 'payment_finalize', 'production_payment') and (line.qty_invoiced > 0 or line.qty_delivered > 0)):
                line.product_updatable = False
            else:
                line.product_updatable = True