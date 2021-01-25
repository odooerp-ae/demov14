
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from odoo.tools import float_is_zero, float_compare
from datetime import datetime, timedelta


class ProductTemplate(models.Model):
    _inherit = "product.template"

    type = fields.Selection(default='product')
    article_number = fields.Char(string="Article Number")
    article_ar_desc = fields.Char(string="Article Arabic Description")
    phenix_ref = fields.Char(string="Phenix Reference")
    product_line = fields.Char()
    has_manufacture_route = fields.Boolean(compute='_has_manufacture_route')
    is_measure_item = fields.Boolean(string="Measure item")
    sale_uom_ids = fields.Many2many(comodel_name="uom.uom", string="Sale UOMs")
    product_uom_category_id = fields.Many2one('uom.category', related='uom_id.category_id', readonly=True)

    @api.depends('route_from_categ_ids', 'route_from_categ_ids.rule_ids',
                 'route_ids', 'route_ids.rule_ids')
    def _has_manufacture_route(self):
        for product in self:
            has_manufacture_route = False
            all_routes = product.route_from_categ_ids
            if product.route_ids:
                all_routes += product.route_ids
            manufacture_rules = all_routes.mapped('rule_ids').filtered(lambda r: r.action == 'manufacture')
            if manufacture_rules:
                has_manufacture_route = True
            product.has_manufacture_route = has_manufacture_route