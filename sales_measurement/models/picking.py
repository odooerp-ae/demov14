# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class Picking(models.Model):
    _inherit = "stock.picking"

    def button_validate(self):
        if self.picking_type_code == 'outgoing' and self.sale_id \
                and self.sale_id.paid_amount_percent < 100:
            raise ValidationError(_("Sale Order of this picking is not fully Paid"))

        return super(Picking, self).button_validate()