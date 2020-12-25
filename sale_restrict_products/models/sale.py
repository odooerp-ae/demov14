from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProductCategory(models.Model):
    _inherit = 'product.category'

    prevent_so_with_no_quantities = fields.Boolean(string="Restrict SO with no quantities")


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.constrains('order_line')
    def _check_lines_qty(self):
        for order in self:
            lines = order.order_line.filtered(lambda p: p.product_id.categ_id.prevent_so_with_no_quantities and
                                                        p.product_type == 'product' and p.product_uom_qty > 0.0)
            if lines:
                products = lines.mapped("product_id")
                for product in products:
                    product_lines = lines.filtered(lambda p: p.product_id.id == product.id)
                    total_product_uom_qty = sum(product_lines.mapped("product_uom_qty"))
                    if total_product_uom_qty > (product.qty_available - product.outgoing_qty):
                        raise ValidationError(_("You cannot save a S.O as product {} has not available quantity".format(product.name)))
