from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class Picking(models.Model):
    _inherit = 'stock.picking'

    prevent_return = fields.Boolean(related='picking_type_id.prevent_return')


class Stock(models.Model):
    _inherit = 'stock.picking.type'

    prevent_return = fields.Boolean()
