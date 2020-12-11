# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

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


class order_line_wizard(models.TransientModel):
    _name = 'order.line.wizard'
    _description = "Order Line Wizard"

    sale_order_file = fields.Binary(string="Select File")
    import_option = fields.Selection([('csv', 'CSV File'), ('xls', 'XLS File')], string='Select', default='csv')
    import_prod_option = fields.Selection([('barcode', 'Barcode'), ('code', 'Code'), ('name', 'Name')],
                                          string='Import Product By ', default='name')
    product_details_option = fields.Selection(
        [('from_product', 'Take Details From The Product'), ('from_xls', 'Take Details From The XLS File'),
         ('from_pricelist', 'Take Details With Adapted Pricelist')], default='from_xls')

    def import_sol(self):
        res = False
        if self.import_option == 'csv':
            keys = ['id', 'product', 'quantity', 'uom', 'description', 'price', 'tax']
            try:
                csv_data = base64.b64decode(self.sale_order_file)

                data_file = io.StringIO(csv_data.decode("utf-8"))

                data_file.seek(0)
                file_reader = []
                csv_reader = csv.reader(data_file, delimiter=',')

                file_reader.extend(csv_reader)

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
                        exist_line = self.env['sale.order.line'].sudo().browse(int(field[0])) if field[0] else False

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

            for row_no in range(sheet.nrows):

                val = {}
                if row_no <= 0:
                    fields = map(lambda row: row.value.encode('utf-8'), sheet.row(row_no))

                else:
                    line = list(
                        map(lambda row: isinstance(row.value, bytes) and row.value.encode('utf-8') or str(row.value),
                            sheet.row(row_no)))
                    exist_line = self.env['sale.order.line'].sudo().browse(int(line[0])) if line[0] else False

                    if self.product_details_option == 'from_product':
                        values.update({
                            'product': line[1].split('.')[0],
                            'quantity': line[2]
                        })
                    elif self.product_details_option == 'from_xls':
                        values.update({'product': line[1].split('.')[0],
                                       'quantity': line[2],
                                       'uom': line[3],
                                       'description': line[4],
                                       'price': line[5],
                                       'tax': line[6]
                                       })
                    else:
                        values.update({
                            'product': line[1].split('.')[0],
                            'quantity': line[2],
                        })
                    if exist_line:

                        res = self.update_order_line(exist_line, values)
                    else:
                        res = self.create_order_line(values)

        return res

    def create_order_line(self, values):
        sale_order_brw = self.env['sale.order'].browse(self._context.get('active_id'))
        product = values.get('product')
        if self.product_details_option == 'from_product':
            if self.import_prod_option == 'barcode':
                product_obj_search = self.env['product.product'].search([('barcode', '=', values['product'])])
            elif self.import_prod_option == 'code':
                product_obj_search = self.env['product.product'].search([('default_code', '=', values['product'])])
            else:
                product_obj_search = self.env['product.product'].search([('name', '=', values['product'])])

            if product_obj_search:
                product_id = product_obj_search
            elif not product_obj_search and sale_order_brw.company_id.create_product_import:
                product_id = self.env['product.product'].create([('name', '=', values['product'])])

            else:
                raise ValidationError(_('%s product is not found".') % values.get('product'))

            if sale_order_brw.state == 'draft':
                order_lines = self.env['sale.order.line'].create({
                    'order_id': sale_order_brw.id,
                    'product_id': product_id.id,
                    'name': product_id.name,
                    'product_uom_qty': float(values.get('quantity')),
                    'product_uom': product_id.uom_id.id,
                    'price_unit': float(product_id.lst_price),
                })
            elif sale_order_brw.state == 'sent':
                order_lines = self.env['sale.order.line'].create({
                    'order_id': sale_order_brw.id,
                    'product_id': product_id.id,
                    'name': product_id.name,
                    'product_uom_qty': float(values.get('quantity')),
                    'product_uom': product_id.uom_id.id,
                    'price_unit': float(product_id.lst_price),
                })
            elif sale_order_brw.state != 'sent' or sale_order_brw.state != 'draft':
                raise UserError(_('We cannot import data in validated or confirmed order.'))
        elif self.product_details_option == 'from_xls':
            product_id = False
            uom = values.get('uom')
            if self.import_prod_option == 'barcode':
                product_obj_search = self.env['product.product'].search([('barcode', '=', values['product'])])
            elif self.import_prod_option == 'code':
                product_obj_search = self.env['product.product'].search([('default_code', '=', values['product'])])
            else:
                product_obj_search = self.env['product.product'].search([('name', '=', values['product'])])

            uom_obj_search = self.env['uom.uom'].search([('name', '=', uom)])
            tax_id_lst = []
            if values.get('tax'):
                if ';' in values.get('tax'):
                    tax_names = values.get('tax').split(';')
                    for name in tax_names:
                        tax = self.env['account.tax'].search([('name', '=', name), ('type_tax_use', '=', 'sale')])
                        if not tax:
                            raise ValidationError(_('"%s" Tax not in your system') % name)
                        tax_id_lst.append(tax.id)

                elif ',' in values.get('tax'):
                    tax_names = values.get('tax').split(',')
                    for name in tax_names:
                        tax = self.env['account.tax'].search([('name', '=', name), ('type_tax_use', '=', 'sale')])
                        if not tax:
                            raise ValidationError(_('"%s" Tax not in your system') % name)
                        tax_id_lst.append(tax.id)
                else:
                    tax_names = values.get('tax').split(',')
                    tax = self.env['account.tax'].search([('name', '=', tax_names), ('type_tax_use', '=', 'sale')])
                    if not tax:
                        raise ValidationError(_('"%s" Tax not in your system') % tax_names)
                    tax_id_lst.append(tax.id)

            if not uom_obj_search:
                raise ValidationError(_('UOM "%s" is Not Available') % uom)

            if product_obj_search:
                product_id = product_obj_search
            else:
                if self.import_prod_option == 'name' and sale_order_brw.company_id.create_product_import:
                    product_id = self.env['product.product'].create({'name': product, 'lst_price': values.get('price')})
            if not product_id:
                raise ValidationError(_(
                    '%s product is not found" .\n If you want to create product then first select Import Product By Name option .') % values.get(
                    'product'))

            if sale_order_brw.state == 'draft':
                order_lines = self.env['sale.order.line'].create({
                    'order_id': sale_order_brw.id,
                    'product_id': product_id.id,
                    'name': values.get('description'),
                    'product_uom_qty': float(values.get('quantity')),
                    'product_uom': uom_obj_search.id,
                    'price_unit': values.get('price'),
                })
            elif sale_order_brw.state == 'sent':
                order_lines = self.env['sale.order.line'].create({
                    'order_id': sale_order_brw.id,
                    'product_id': product_id.id,
                    'name': values.get('description'),
                    'product_uom_qty': float(values.get('quantity')),
                    'product_uom': uom_obj_search.id,
                    'price_unit': values.get('price'),
                })
            elif sale_order_brw.state != 'sent' or sale_order_brw.state != 'draft':
                raise UserError(_('We cannot import data in validated or confirmed order.'))
            if tax_id_lst:
                order_lines.write({'tax_id': ([(6, 0, tax_id_lst)])})
        else:
            if self.import_prod_option == 'barcode':
                product_obj_search = self.env['product.product'].search([('barcode', '=', values['product'])])
            elif self.import_prod_option == 'code':
                product_obj_search = self.env['product.product'].search([('default_code', '=', values['product'])])
            else:
                product_obj_search = self.env['product.product'].search([('name', '=', values['product'])])

            if product_obj_search:
                product_id = product_obj_search
            else:
                if self.import_prod_option == 'name' and sale_order_brw.company_id.create_product_import:
                    product_id = self.env['product.product'].create({'name': product, 'lst_price': values.get('price')})
            if not product_id:
                raise ValidationError(_(
                    '%s product is not found" .\n If you want to create product then first select Import Product By Name option .') % values.get(
                    'product'))

            if sale_order_brw.state == 'draft':
                order_lines = self.env['sale.order.line'].create({
                    'order_id': sale_order_brw.id,
                    'product_id': product_id.id,
                    'product_uom_qty': float(values.get('quantity')),
                })
                order_lines.product_id_change()
                order_lines._onchange_discount()

            elif sale_order_brw.state == 'sent':
                order_lines = self.env['sale.order.line'].create({
                    'order_id': sale_order_brw.id,
                    'product_id': product_id.id,
                    'product_uom_qty': float(values.get('quantity')),
                })
                order_lines.product_id_change()
                order_lines._onchange_discount()

            elif sale_order_brw.state != 'sent' or sale_order_brw.state != 'draft':
                raise UserError(_('We cannot import data in validated or confirmed order.'))
        return True

    def update_order_line(self, order_line, values):
        sale_order_brw = self.env['sale.order'].browse(self._context.get('active_id'))
        product = values.get('product')
        if self.product_details_option == 'from_product':
            if self.import_prod_option == 'barcode':
                product_obj_search = self.env['product.product'].search([('barcode', '=', values['product'])])
            elif self.import_prod_option == 'code':
                product_obj_search = self.env['product.product'].search([('default_code', '=', values['product'])])
            else:
                product_obj_search = self.env['product.product'].search([('name', '=', values['product'])])

            if product_obj_search:
                product_id = product_obj_search
            elif not product_obj_search and sale_order_brw.company_id.create_product_import:
                product_id = self.env['product.product'].create([('name', '=', values['product'])])

            else:
                raise ValidationError(_('%s product is not found".') % values.get('product'))

            if sale_order_brw.state in ['draft', 'sent']:
                vals_to_update = {}
                if product:
                    vals_to_update['product_id'] = product_id.id
                    vals_to_update['name'] = product_id.name
                    vals_to_update['product_uom'] = product_id.uom_id.id
                    vals_to_update['price_unit'] = product_id.lst_price
                if values.get('quantity'):
                    vals_to_update['product_uom_qty'] = float(values.get('quantity'))

                order_line.sudo().write(vals_to_update)

            elif sale_order_brw.state != 'sent' or sale_order_brw.state != 'draft':
                raise UserError(_('We cannot import data in validated or confirmed order.'))
        elif self.product_details_option == 'from_xls':
            product_id = False
            uom = values.get('uom')
            if self.import_prod_option == 'barcode':
                product_obj_search = self.env['product.product'].search([('barcode', '=', values['product'])])
            elif self.import_prod_option == 'code':
                product_obj_search = self.env['product.product'].search([('default_code', '=', values['product'])])
            else:
                product_obj_search = self.env['product.product'].search([('name', '=', values['product'])])

            uom_obj_search = self.env['uom.uom'].search([('name', '=', uom)])
            tax_id_lst = []
            if values.get('tax'):
                if ';' in values.get('tax'):
                    tax_names = values.get('tax').split(';')
                    for name in tax_names:
                        tax = self.env['account.tax'].search([('name', '=', name), ('type_tax_use', '=', 'sale')])
                        if not tax:
                            raise ValidationError(_('"%s" Tax not in your system') % name)
                        tax_id_lst.append(tax.id)

                elif ',' in values.get('tax'):
                    tax_names = values.get('tax').split(',')
                    for name in tax_names:
                        tax = self.env['account.tax'].search([('name', '=', name), ('type_tax_use', '=', 'sale')])
                        if not tax:
                            raise ValidationError(_('"%s" Tax not in your system') % name)
                        tax_id_lst.append(tax.id)
                else:
                    tax_names = values.get('tax').split(',')
                    tax = self.env['account.tax'].search([('name', '=', tax_names), ('type_tax_use', '=', 'sale')])
                    if not tax:
                        raise ValidationError(_('"%s" Tax not in your system') % tax_names)
                    tax_id_lst.append(tax.id)

            if product_obj_search:
                product_id = product_obj_search
            else:
                if self.import_prod_option == 'name' and sale_order_brw.company_id.create_product_import:
                    product_id = self.env['product.product'].create({'name': product, 'lst_price': values.get('price')})

            if not product_id and values['product']:
                raise ValidationError(_(
                    '%s product is not found" .\n If you want to create product then first select Import Product By Name option .') % values.get(
                    'product'))
            vals_to_update = {}
            if product:
                vals_to_update['product_id'] = product_id.id
            if values.get('quantity'):
                vals_to_update['product_uom_qty'] = float(values.get('quantity'))
            if values.get('price'):
                vals_to_update['price_unit'] = float(values.get('price'))
            if values.get('description'):
                vals_to_update['name'] = float(values.get('description'))
            if uom:
                vals_to_update['product_uom'] = uom_obj_search.id

            if sale_order_brw.state in ['draft', 'sent']:

                order_line.sudo().write(vals_to_update)

            elif sale_order_brw.state == 'sent':
                order_line.sudo().write({
                    'product_uom': uom_obj_search.id,
                })
            elif sale_order_brw.state != 'sent' or sale_order_brw.state != 'draft':
                raise UserError(_('We cannot import data in validated or confirmed order.'))

            if tax_id_lst:
                order_line.sudo().write({'tax_id': ([(6, 0, tax_id_lst)])})
        else:
            product_id = False
            if self.import_prod_option == 'barcode':
                product_obj_search = self.env['product.product'].search([('barcode', '=', values['product'])])
            elif self.import_prod_option == 'code':
                product_obj_search = self.env['product.product'].search([('default_code', '=', values['product'])])
            else:
                product_obj_search = self.env['product.product'].search([('name', '=', values['product'])])

            if product_obj_search:
                product_id = product_obj_search
            else:
                if self.import_prod_option == 'name' and sale_order_brw.company_id.create_product_import:
                    product_id = self.env['product.product'].create({'name': product, 'lst_price': values.get('price')})
            if not product_id and values['product']:
                raise ValidationError(_(
                    '%s product is not found" .\n If you want to create product then first select Import Product By Name option .') % values.get(
                    'product'))

            if sale_order_brw.state in ['draft', 'sent']:
                order_line.sudo().write({
                    'product_id': product_id.id,
                    'product_uom_qty': float(values.get('quantity')),
                })
                order_line.product_id_change()
                order_line._onchange_discount()

            elif sale_order_brw.state != 'sent' or sale_order_brw.state != 'draft':
                raise UserError(_('We cannot import data in validated or confirmed order.'))
        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
