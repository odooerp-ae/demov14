# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import Warning, ValidationError
import binascii
import tempfile
import xlrd
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)
import io

try:
    import xlrd
except ImportError:
    _logger.debug('Cannot `import xlrd`.')
try:
    import csv
except ImportError:
    _logger.debug('Cannot `import csv`.')
try:
    import base64
except ImportError:
    _logger.debug('Cannot `import base64`.')


class Sale(models.Model):
    _inherit = 'sale.order'

    alu_import_so_lines = fields.Boolean(related="company_id.alu_import_so_lines", store=True)


class order_line_wizard(models.TransientModel):
    _name = 'import.order.line.wizard'
    _description = "Import Order Line Wizard"

    sale_order_file = fields.Binary(string="Select File")
    import_option = fields.Selection([('csv', 'CSV File'), ('xls', 'XLS File')], string='Select', default='csv')
    import_type = fields.Selection(selection=[('order_line', 'Sale Order Line'), ('bom', 'Bill of Material')],
                                   required=True, default='order_line')
    import_line_type = fields.Selection(selection=[('import', 'Import Lines'), ('update', 'Update Lines')],
                                        required=True, default='import')

    def import_sol(self):
        res = False
        sale_order = self.env['sale.order'].browse(self._context.get('active_id'))
        so_lines = sale_order.sudo().order_line
        if self.import_line_type == 'import' and self.import_type == 'order_line':
            so_lines.unlink()
        if self.import_option == 'csv':
            keys = ['Code Project', 'Sub Project Code', 'SAP Code', 'Color', 'Qty', 'UM', 'price']
            try:
                csv_data = base64.b64decode(self.sale_order_file)

                data_file = io.StringIO(csv_data.decode("utf-8"))

                data_file.seek(0)
                file_reader = []
                csv_reader = csv.reader(data_file, delimiter=',')

                file_reader.extend(csv_reader)

            except Exception:
                raise ValidationError(_("Please select any file or You have selected invalid file"))

            order_lines = {}
            bom_lines = {}

            for i in range(len(file_reader)):
                field = list(map(str, file_reader[i]))
                values = dict(zip(keys, field))
                if values:
                    if i == 0:
                        continue
                    else:
                        if self.import_type == "order_line":
                            price = float(field[6])
                            if price > 0.0:
                                product_refrence = field[0]

                                if self.import_line_type == 'update':
                                    matching_so_line = so_lines.filtered(lambda l: l.product_id.default_code == product_refrence)
                                    if not matching_so_line:

                                        continue
                                exist_line = order_lines.get(product_refrence)
                                if not exist_line:
                                    order_lines[product_refrence] = {'product': product_refrence,
                                                                     'description': field[1],
                                                                     'product_uom_qty': 1,
                                                                     'price': float(field[6]),
                                                                     }
                                else:
                                    exist_line['price'] += float(field[6])
                            else:
                                product = field[2].split('.')[0]
                                if self.import_line_type == 'update':
                                    matching_so_line = so_lines.filtered(
                                        lambda l: l.product_id.default_code == product_refrence)
                                    if not matching_so_line:

                                        continue
                                product_obj_search = self.env['product.product'].search([('default_code', '=', product)])
                                exist_line = order_lines.get(product)
                                if not exist_line:
                                    order_lines[product] = {'product': product,
                                                            'description': field[1],
                                                            'product_uom_qty': float(field[4]),
                                                            'product_uom': field[5],
                                                            'price': product_obj_search.lst_price,
                                                            }
                                else:

                                    exist_line['product_uom_qty'] += float(field[4])
                        else:
                            price = float(field[6])
                            if price > 0.0:
                                product_reference = field[0]
                                exist_product = bom_lines.get(product_reference)

                                component = field[2].split('.')[0]

                                if not exist_product:
                                    bom_lines[product_reference] = {'bom_line_ids': {
                                        component: {
                                        'product_qty':  float(field[4]),
                                        'product_uom_id':  field[5],
                                    }}}

                                else:
                                    exist_component = exist_product['bom_line_ids'].get(component)

                                    if not exist_component:
                                        exist_product['bom_line_ids'][component] = {
                                            'product_qty':  float(field[4]),
                                            'product_uom_id':  field[5],
                                        }
                                    else:
                                        exist_component['product_qty'] += float(field[4])


            if bom_lines:
                res = self.update_order_line_bom(bom_lines)

        else:
            try:
                fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
                fp.write(binascii.a2b_base64(self.sale_order_file))

                fp.seek(0)
                values = {}
                workbook = xlrd.open_workbook(fp.name)
                sheet = workbook.sheet_by_index(0)

            except Exception:
                raise ValidationError(_("Please select any file or You have selected invalid file"))
            order_lines = {}
            bom_lines = {}

            for row_no in range(sheet.nrows):

                val = {}
                if row_no <= 0:
                    fields = map(lambda row: row.value.encode('utf-8'), sheet.row(row_no))

                else:
                    line = list(
                        map(lambda row: isinstance(row.value, bytes) and row.value.encode('utf-8') or str(row.value),
                            sheet.row(row_no)))
                    if self.import_type == "order_line":

                        price = float(line[6])
                        if price > 0.0:
                            product_refrence = line[0]
                            if self.import_line_type == 'update':
                                matching_so_line = so_lines.filtered(
                                    lambda l: l.product_id.default_code == product_refrence)
                                if not matching_so_line:

                                    continue
                            exist_line = order_lines.get(product_refrence)
                            if not exist_line:
                                order_lines[product_refrence]= {'product': product_refrence,
                                               'description': line[1],
                                               'product_uom_qty': 1,
                                               'price': float(line[6]),
                                               }
                            else:
                                exist_line['price'] += float(line[6])
                        else:
                            product = line[2].split('.')[0]
                            if self.import_line_type == 'update':
                                matching_so_line = so_lines.filtered(
                                    lambda l: l.product_id.default_code == product)
                                if not matching_so_line:
                                    continue
                            product_obj_search = self.env['product.product'].search([('default_code', '=',product)])
                            exist_line = order_lines.get(product)
                            if not exist_line:
                                order_lines[product] = {'product': product,
                                                                 'description': line[1],
                                                                 'product_uom_qty': float(line[4]),
                                                                 'product_uom': line[5],
                                                                 'price': product_obj_search.lst_price,
                                                                 }
                            else:

                                exist_line['product_uom_qty'] += float(line[4])
                    else:
                        price = float(line[6])
                        if price > 0.0:
                            product_reference = line[0]
                            exist_product = bom_lines.get(product_reference)

                            component = line[2].split('.')[0]

                            if not exist_product:
                                bom_lines[product_reference] = {'bom_line_ids': {
                                    component: {
                                    'product_qty':  float(line[4]),
                                    'product_uom_id':  line[5],
                                }}}

                            else:
                                exist_component = exist_product['bom_line_ids'].get(component)

                                if not exist_component:
                                    exist_product['bom_line_ids'][component] = {
                                        'product_qty':  float(line[4]),
                                        'product_uom_id':  line[5],
                                    }
                                else:
                                    exist_component['product_qty'] += float(line[4])


        if bom_lines:
            res = self.update_order_line_bom(bom_lines)
        if order_lines:
            res = self.create_order_line(order_lines)
        return res

    def create_order_line(self, values):
        sale_order = self.env['sale.order'].browse(self._context.get('active_id'))

        for key, line in values.items():
            product = line['product']
            if self.import_line_type == 'update':
                matching_so_line = sale_order.order_line.filtered(
                    lambda l: l.product_id.default_code == product)
                if matching_so_line:
                    matching_so_line.unlink()
            product_id = False
            product_obj_search = self.env['product.product'].search([('default_code', '=', product)])

            if product_obj_search:
                product_id = product_obj_search
            else:
                if sale_order.company_id.create_product_import:
                    product_vals = {'name': line['description'],
                                    'default_code': product,
                                    'lst_price': line['price'],
                                     }
                    special_categ = self.env['product.category'].sudo().search([('is_special', '=', True)], limit=1)
                    if special_categ:
                        product_vals['categ_id'] = special_categ.id

                    product_id = self.env['product.product'].create(product_vals)
            if not product_id:
                raise ValidationError(_(
                    '%s product is not found" .\n .') % product)

            if sale_order.state in ['draft', 'sent']:
                if line.get('product_uom'):
                    uom_id = self.env['uom.uom'].search([('name', '=', line.get('product_uom'))])
                else:
                    uom_id = product_id.uom_id
                if not uom_id:
                    raise ValidationError("There is no UOM for product  {} with code {}".format(product_id.name, product))
                line_vals = {
                    'order_id': sale_order.id,
                    'product_id': product_id.id,
                    'name': line['description'],
                    'product_uom_qty': float(line['product_uom_qty']),
                    'product_uom': uom_id.id,
                    'price_unit': line['price'],
                }
                order_lines = self.env['sale.order.line'].create(line_vals)

            elif sale_order.state != 'sent' or sale_order.state != 'draft':
                raise UserError(_('We cannot import data in validated or confirmed order.'))

        return True

    def update_order_line_bom(self, all_bom_val):
        for bom_product, bom_values in all_bom_val.items():

            product = self.env['product.product'].sudo().search([('default_code', '=', bom_product)])
            product_tmp = product.product_tmpl_id
            bom_val = {
                'product_tmpl_id': product_tmp.id,
                'product_uom_id': product_tmp.uom_id.id,
                'bom_line_ids': []
                       }
            for key, values in bom_values['bom_line_ids'].items():
                component = self.env['product.product'].sudo().search(['|',('default_code', '=', str(key)), ('name', '=', str(key))])

                component_uom_id = self.env['uom.uom'].sudo().search([('name', '=', values.get('product_uom_id'))], limit=1)

                if not component:
                    raise ValidationError(_("The component with reference {} doesn't exist".format(key)))
                if not component_uom_id:
                    raise ValidationError(_("This UOM {} not found in system".format(values.get('product_uom_id'))))

                bom_val['bom_line_ids'].append((0, 0, {
                    'product_id': component.id,
                    'product_qty': values.get('product_qty'),
                    'product_uom_id': component_uom_id.id
                }))
            bom_id = self.env['mrp.bom'].sudo().create(bom_val)

        return True
