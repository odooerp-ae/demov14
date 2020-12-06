# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class Cpm(models.Model):
    _name = 'product.cpm'
    _rec_name = 'name'

    name = fields.Char(required=True)


class CpmLine(models.Model):
    _name = 'product.cpm.line'
    _rec_name = 'cpm_id'

    product_id = fields.Many2one(comodel_name="product.template", required=True, ondelete='cascade')
    cpm_id = fields.Many2one(comodel_name="product.cpm", string="CPM")
    uom_id = fields.Many2one(comodel_name='uom.uom', string='Unit of Measure')
    cpm_height = fields.Float(string="Height")
    cpm_width = fields.Float(string="Width")
    cpm_length = fields.Float(string="length")
    cpm_volume = fields.Float(string="Volume")


class Product(models.Model):
    _inherit = 'product.template'

    cpm_line_ids = fields.One2many(comodel_name="product.cpm.line", inverse_name="product_id")


