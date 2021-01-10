# -*- coding: utf-8 -*-
import logging
from odoo import fields, models, _

_logger = logging.getLogger(__name__)


class MeasurementCancelWizard(models.TransientModel):
    _name = 'measurement.cancel.wizard'

    cancel_reason = fields.Text(required=True)

    request_id = fields.Many2one(comodel_name="measurement.request")

    def cancel_request(self):
        request_vals = {
            'cancel_reason': self.cancel_reason,
            'state': 'cancel',

        }
        self.request_id.sudo().write(request_vals)
        return True
