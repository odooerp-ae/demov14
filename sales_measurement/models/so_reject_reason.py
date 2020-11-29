# -*- coding: utf-8 -*-
import logging
from odoo import fields, models, api, _

_logger = logging.getLogger(__name__)


class SOReject(models.Model):
    _name = 'sale.order.reject'

    name = fields.Char(required=True, translate=True)
