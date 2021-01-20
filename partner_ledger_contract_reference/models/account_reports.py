# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools.misc import format_date


class PartnerLedger(models.AbstractModel):
    _inherit = "account.partner.ledger"

    @api.model
    def _get_report_line_total(self, options, initial_balance, debit, credit, balance):
        result = super(PartnerLedger, self)._get_report_line_total(options, initial_balance, debit, credit, balance)
        result['colspan'] = 7
        return result

    @api.model
    def _get_report_line_partner(self, options, partner, initial_balance, debit, credit, balance):
        result = super(PartnerLedger, self)._get_report_line_partner(options, partner, initial_balance, debit, credit, balance)
        result['colspan'] = 7
        return result

    @api.model
    def _get_report_line_move_line(self, options, partner, aml, cumulated_init_balance, cumulated_balance):
        """"
        Override to add sale order ref of lines
        """
        if aml['payment_id']:
            caret_type = 'account.payment'
            contract_reference = self.env['account.payment'].sudo().search([('id', '=', aml['payment_id'])]).sale_order_id.name
        else:
            caret_type = 'account.move'
            contract_reference = self.env['account.move.line'].sudo().search([('move_name', '=', aml['move_name'])]).sale_order_id.name

        date_maturity = aml['date_maturity'] and format_date(self.env, fields.Date.from_string(aml['date_maturity']))
        columns = [
            {'name': aml['journal_code']},
            {'name': aml['account_code']},
            {'name': self._format_aml_name(aml['name'], aml['ref'], aml['move_name'])},
            {'name': date_maturity or '', 'class': 'date'},
            {'name': aml['matching_number'] or ''},
            {'name': contract_reference or ''},
            {'name': self.format_value(cumulated_init_balance), 'class': 'number'},
            {'name': self.format_value(aml['debit'], blank_if_zero=True), 'class': 'number'},
            {'name': self.format_value(aml['credit'], blank_if_zero=True), 'class': 'number'},
        ]
        if self.user_has_groups('base.group_multi_currency'):
            if aml['currency_id']:
                currency = self.env['res.currency'].browse(aml['currency_id'])
                formatted_amount = self.format_value(aml['amount_currency'], currency=currency, blank_if_zero=True)
                columns.append({'name': formatted_amount, 'class': 'number'})
            else:
                columns.append({'name': ''})
        columns.append({'name': self.format_value(cumulated_balance), 'class': 'number'})
        return {
            'id': aml['id'],
            'parent_id': 'partner_%s' % (partner.id if partner else 0),
            'name': format_date(self.env, aml['date']),
            'class': 'text' + aml.get('class', ''),  # do not format as date to prevent text centering
            'columns': columns,
            'caret_options': caret_type,
            'level': 2,
        }

    def _get_columns_name(self, options):
        """"
        Override to add contract ref in header
        """
        columns = [
            {},
            {'name': _('JRNL')},
            {'name': _('Account')},
            {'name': _('Ref')},
            {'name': _('Due Date'), 'class': 'date'},
            {'name': _('Matching Number')},
            {'name': _('Contract Ref')},
            {'name': _('Initial Balance'), 'class': 'number'},
            {'name': _('Debit'), 'class': 'number'},
            {'name': _('Credit'), 'class': 'number'}]

        if self.user_has_groups('base.group_multi_currency'):
            columns.append({'name': _('Amount Currency'), 'class': 'number'})

        columns.append({'name': _('Balance'), 'class': 'number'})
        return columns
