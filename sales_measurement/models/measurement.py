# -*- coding: utf-8 -*-

from odoo import api,fields, models,  _


class MeasurementRequest(models.Model):
    _name = "measurement.request"
    _inherit = ['mail.thread']
    _description = 'Measurement Requests'

    name = fields.Char(index=True, default='New')
    partner_id = fields.Many2one(comodel_name="res.partner", string="Customer", required=True,
                                 tracking=True,
                                 states={'cancel': [('readonly', True)],'done': [('readonly', True)]})
    state = fields.Selection(selection=[('new', 'New'),
                                        ('measured', 'Measured'),
                                        ('design', 'Design'),
                                        ('done', 'Done'),
                                        ('cancel', 'Cancel'),
                                        ],
                             required=True, default='new', tracking=True)
    schedule_date = fields.Date(states={'cancel': [('readonly', True)], 'done': [('readonly', True)]}, tracking=True)
    employee_id = fields.Many2one(comodel_name="hr.employee", string="Technician",
                                  states={'cancel': [('readonly', True)], 'done': [('readonly', True)]}, tracking=True)
    line_ids = fields.One2many(comodel_name="measurement.request.line", inverse_name="measure_request_id",
                               states={'cancel': [('readonly', True)], 'done': [('readonly', True)]})
    sale_order_id = fields.Many2one(comodel_name="sale.order", copy=False, string="Quotation")
    is_so_created = fields.Boolean(string="Quotation Created", copy=False)

    @api.model
    def create(self, values):
        values['name'] = self.env['ir.sequence'].next_by_code('measurement.request')
        return super(MeasurementRequest, self).create(values)

    def set_to_measured(self):
        self.state = 'measured'
        return True

    def set_to_design(self):
        self.state = 'design'
        return True

    def action_new(self):
        self.state = 'new'
        return True

    def action_cancel(self):
        self.state = 'cancel'
        return True

    def action_create_quotation(self):
        sales_order = self.env["sale.order"].create({
            "partner_id": self.partner_id.id,
            "measure_request_id": self.id,

        })
        self.sale_order_id = sales_order.id
        self.is_so_created = True
        self.state = 'done'
        return True


class MeasurementLine(models.Model):
    _name = "measurement.request.line"

    measure_request_id = fields.Many2one(comodel_name="measurement.request", required=True,
                                 ondelete='cascade')
    product_id = fields.Many2one(comodel_name="product.product", required=True,
                                 domain=[("type", '=', "service")])
    quantity = fields.Float(default=1)
    description = fields.Char()
    price = fields.Float()

    @api.onchange('product_id')
    def product_id_change(self):
        if self.product_id:
            self.description = self.product_id.get_product_multiline_description_sale()
