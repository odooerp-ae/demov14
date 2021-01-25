# -*- coding: utf-8 -*-

from odoo import fields, models, _
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError


class Purchase(models.Model):
    _inherit = "purchase.order"

    def button_confirm(self):
        max_day_to_confirm = self.date_order + relativedelta(days= self.company_id.days_max_rfq)
        if max_day_to_confirm < fields.Datetime.now():
            raise ValidationError(_("You cant confirm as you exceed the max period to confirm"))
        return super(Purchase, self).button_confirm()