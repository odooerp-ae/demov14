# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PickingType(models.Model):
    _inherit = "stock.picking.type"

    count_delivery_ready = fields.Integer(compute='_compute_delivery_ready')

    def _compute_delivery_ready(self):

        data = self.env['stock.picking'].read_group([('state', '=', 'assigned'), ('picking_type_id', 'in', self.ids),
                                                     ('sale_id.paid_amount_percent', '>=', 100)
                                                     ],
            ['picking_type_id'], ['picking_type_id'])
        count = {
            x['picking_type_id'][0]: x['picking_type_id_count']
            for x in data if x['picking_type_id']}

        for record in self:
            record.count_delivery_ready = count.get(record.id, 0)


class Picking(models.Model):
    _inherit = "stock.picking"

    def button_validate(self):
        if self.picking_type_code == 'outgoing' and self.sale_id \
                and self.sale_id.paid_amount_percent < 100:
            raise ValidationError(_("Sale Order of this picking is not fully Paid"))

        return super(Picking, self).button_validate()