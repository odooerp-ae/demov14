# -*- coding: utf-8 -*-

from odoo import fields, models


class Repair(models.Model):
    _inherit = 'repair.order'

    so_id = fields.Many2one('sale.order', string="Sale Order")
