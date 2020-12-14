# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import Warning, ValidationError
import binascii
import tempfile
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


class ProductBillwizard(models.TransientModel):
    _name = 'product.bom.wizard'
    _description = "Product Bill of Material Wizard"

    import_file = fields.Binary(string="Select File")
    import_option = fields.Selection([('csv', 'CSV File'), ('xls', 'XLS File')], string='Select', default='csv')

    def import_bom(self):
        res = False
        if self.import_option == 'xls':
            try:
                fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
                fp.write(binascii.a2b_base64(self.import_file))

                fp.seek(0)
                values = {}
                workbook = xlrd.open_workbook(fp.name)
                sheet = workbook.sheet_by_index(0)

            except Exception:
                raise ValidationError(_("Please select any file or You have selected invalid file"))
            all_bom_val = {}

            current_product = False
            for row_no in range(sheet.nrows):

                if row_no <= 0:
                    fields = map(lambda row: row.value.encode('utf-8'), sheet.row(row_no))

                else:
                    line = list(map(lambda row: isinstance(row.value, bytes) and row.value.encode('utf-8') or str(row.value),
                            sheet.row(row_no)))
                    component = self.env['product.product'].sudo().search([('name', '=', line[7])])
                    component_uom_id = self.env['uom.uom'].sudo().search([('name', '=', line[9])])

                    if line[0]:

                        current_product = product_tmp = self.env['product.template'].sudo().search([('name', '=', line[0])])
                        product = self.env['product.product'].sudo().search([('name', '=', line[1])])
                        product_uom_id = self.env['uom.uom'].sudo().search([('name', '=', line[3])])
                        company = self.env['res.company'].sudo().search([('name', '=', line[6])])
                        if line[5] == 'Kit':
                            bom_type = 'phantom'

                        elif line[5] == 'Manufacture this product':
                            bom_type = 'normal'
                        else:
                            bom_type = False
                        bom_vals = {
                                'product_tmpl_id': product_tmp.id,
                                'product_id': product.id,
                                'product_qty': line[2],
                                'product_uom_id': product_uom_id.id,
                                'code': line[4],
                                'type': bom_type,
                                'company_id': company.id,
                                'bom_line_ids': [(0,0, {
                                    'product_id': component.id,
                                    'product_qty': line[8],
                                    'product_uom_id': component_uom_id.id
                                })]
                                    }
                        all_bom_val[product_tmp.id] = bom_vals
                    else:
                        components = all_bom_val.get(current_product.id).get('bom_line_ids')
                        components.append((0, 0, {
                                    'product_id': component.id,
                                    'product_qty': line[8],
                                    'product_uom_id': component_uom_id.id
                                }))

            if all_bom_val:
                res = self.update_order_line_bom(all_bom_val)

        else:
            keys = ['product', 'product variant', 'quantity', 'uom', 'reference', 'bom type', 'company',
                    'component name', 'component quantity', 'component uom']
            try:
                csv_data = base64.b64decode(self.import_file)
                data_file = io.StringIO(csv_data.decode("utf-8"))

                data_file.seek(0)
                file_reader = []
                csv_reader = csv.reader(data_file, delimiter=',')

                file_reader.extend(csv_reader)

            except Exception:
                raise ValidationError(_("Please select any file or You have selected invalid file"))

            all_bom_val = {}
            current_product = False
            for i in range(len(file_reader)):
                field = list(map(str, file_reader[i]))
                values = dict(zip(keys, field))

                if values:
                    if i == 0:
                        continue
                    else:
                        component = self.env['product.product'].sudo().search([('name', '=', field[7])])
                        component_uom_id = self.env['uom.uom'].sudo().search([('name', '=', field[9])])
                        if field[0]:

                            current_product = product_tmp = self.env['product.template'].sudo().search(
                                [('name', '=', field[0])])
                            product = self.env['product.product'].sudo().search([('name', '=', field[1])])
                            product_uom_id = self.env['uom.uom'].sudo().search([('name', '=', field[3])])
                            company = self.env['res.company'].sudo().search([('name', '=', field[6])])
                            if field[5] == 'Kit':
                                bom_type = 'phantom'

                            elif field[5] == 'Manufacture this product':
                                bom_type = 'normal'
                            else:
                                bom_type = False
                            bom_vals = {
                                'product_tmpl_id': product_tmp.id,
                                'product_id': product.id,
                                'product_qty': field[2],
                                'product_uom_id': product_uom_id.id,
                                'code': field[4],
                                'type': bom_type,
                                'company_id': company.id,
                                'bom_line_ids': [(0, 0, {
                                    'product_id': component.id,
                                    'product_qty': field[8],
                                    'product_uom_id': component_uom_id.id
                                })]
                            }
                            all_bom_val[product_tmp.id] = bom_vals
                        else:
                            components = all_bom_val.get(current_product.id).get('bom_line_ids')
                            components.append((0, 0, {
                                'product_id': component.id,
                                'product_qty': field[8],
                                'product_uom_id': component_uom_id.id
                            }))


            if all_bom_val:
                res = self.update_order_line_bom(all_bom_val)

        return res

    def update_order_line_bom(self, all_bom_val):
        bom_vales = all_bom_val.values()
        for bom_val in bom_vales:
            product_tmp = self.env['product.template'].sudo().browse(bom_val.get("product_tmpl_id"))

            if not product_tmp.bom_ids:
                bom_id = self.env['mrp.bom'].sudo().create(bom_val)
            else:
                vals_to_be_updated = {}
                for key in bom_val.keys():
                    if bom_val.get(key) and key != 'product_tmpl_id'and key != 'bom_line_ids':
                        vals_to_be_updated[key] = bom_val.get(key)

                product_tmp.bom_ids.sudo().write(vals_to_be_updated)
                bom_lines = bom_val.get("bom_line_ids")
                for line in bom_lines:
                    matched_line = product_tmp.bom_ids.bom_line_ids.sudo().filtered(lambda m: m.product_id.id == line[2].get("product_id"))
                    line_vals = {}
                    if float(line[2].get("product_qty")):
                        line_vals["product_qty"] = line[2].get("product_qty")

                    if line[2].get("product_uom_id"):
                        line_vals["product_uom_id"] = line[2].get("product_uom_id")

                    matched_line.write(line_vals)

        return True
