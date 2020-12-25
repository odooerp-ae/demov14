# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import Warning, ValidationError
import binascii
import tempfile
import xlrd
from tempfile import TemporaryFile
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

    def import_sol(self):
        res = False
        if self.import_option == 'csv':
            keys = ['Code Project', 'Sub Project Code', 'SAP Code', 'Color', 'Qty', 'UM', 'price']
            try:
                csv_data = base64.b64decode(self.sale_order_file)

                data_file = io.StringIO(csv_data.decode("utf-8"))

                data_file.seek(0)
                file_reader = []
                csv_reader = csv.reader(data_file, delimiter=',')

                file_reader.extend(csv_reader)
                print("/////////////////////////// file_reader",file_reader)

            except Exception:
                raise ValidationError(_("Please select any file or You have selected invalid file"))

            values = {}
            for i in range(len(file_reader)):
                field = list(map(str, file_reader[i]))
                values = dict(zip(keys, field))
                if values:
                    if i == 0:
                        continue
                    else:
                        exist_line = self.env['sale.order.line'].sudo().browse(int(float(field[0]))) if field[0] else False

                        if self.product_details_option == 'from_product':
                            values.update({
                                'product': field[1],
                                'quantity': field[2]
                            })
                        elif self.product_details_option == 'from_xls':
                            values.update({'product': field[1],
                                           'quantity': field[2],
                                           'uom': field[3],
                                           'description': field[4],
                                           'price': field[5],
                                           'tax': field[6]
                                           })
                        else:
                            values.update({
                                'product': field[1],
                                'quantity': field[2],
                            })
                        if exist_line:

                            res = self.update_order_line(exist_line, values)
                        else:
                            res = self.create_order_line(values)
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
            for row_no in range(sheet.nrows):

                val = {}
                if row_no <= 0:
                    fields = map(lambda row: row.value.encode('utf-8'), sheet.row(row_no))

                else:
                    line = list(
                        map(lambda row: isinstance(row.value, bytes) and row.value.encode('utf-8') or str(row.value),
                            sheet.row(row_no)))
                    print("////////////////////////////////////// line", line)
                    price = float(line[6])
                    if price > 0.0:
                        product_refrence = line[0]
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


            print("////////////////////////////////////// order_lines", order_lines)

        res = self.create_order_line(order_lines)
        return res

    def create_order_line(self, values):
        sale_order = self.env['sale.order'].browse(self._context.get('active_id'))
        print("///////////////////// values")
        for key, line in values.items():
            print("/////////////////////////// line3333", line)
            product = line['product']
            product_id = False
            product_obj_search = self.env['product.product'].search([('default_code', '=', product)])

            if product_obj_search:
                product_id = product_obj_search
            else:
                if sale_order.company_id.create_product_import:
                    product_id = self.env['product.product'].create({'name': line['description'],
                                                                     'default_code': product,
                                                                     'lst_price': line['price'],
                                                                     })
            if not product_id:
                raise ValidationError(_(
                    '%s product is not found" .\n .') % product)

            if sale_order.state in ['draft', 'sent']:
                if line.get('product_uom'):
                    uom_id = self.env['uom.uom'].search([('name', '=', line.get('product_uom'))])
                else:
                    uom_id = product_id.uom_id
                if not uom_id:
                    raise ValidationError("There is no UOM for product  {}".format(product_id))
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


