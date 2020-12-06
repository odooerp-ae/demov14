# -*- coding: utf-8 -*-
import logging
from odoo import fields, models, api, _

_logger = logging.getLogger(__name__)


class SOReject(models.TransientModel):
    _name = 'sale.order.reject.wizard'

    reject_reason_id = fields.Many2one(comodel_name="sale.order.reject", string="Reject Reason",
                                       required=True)

    sale_order_id = fields.Many2one(comodel_name="sale.order")

    def reject_so(self):
        reject_request_vals = {
            'reject_reason_id': self.reject_reason_id.id,
            'state': 'rejected',

        }
        self.sale_order_id.sudo().write(reject_request_vals)
        return True
