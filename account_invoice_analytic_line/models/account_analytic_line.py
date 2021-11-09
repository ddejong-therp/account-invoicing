# -*- coding: utf-8 -*-
# Copyright 2018 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    invoice_discount_id = fields.Many2one(
        'account.move.analytic.line.discount',
        ondelete='restrict', string='Discount',
        default=lambda self:
        self.env.ref('account_invoice_analytic_line.discount_none', False),
    )

    def _account_invoice_analytic_line(self):
        """Create invoices for lines in self"""
        invoices = self.env['account.move']
        for lines in self._account_invoice_analytic_line_group_invoice():
            invoice = self.search(
                lines['__domain']
            )._account_invoice_analytic_line_create_invoice()

            invoices += invoice
        
        action = self.env['ir.actions.act_window']._for_xml_id(
            'account.action_move_out_invoice_type'
        )
        action['domain'] = str([('id', 'in', invoices.ids)])

        return action

    def _account_invoice_analytic_line_create_invoice(self):
        """Actually create an invoice for lines. We assume they have the same
        partner"""
        if not self:
            return self.env['account.move']
        first = self[:1]
        partner = first._find_partner()
        if not partner:
            raise UserError(_("No customer specified for selected lines"))
        
        invoice_vals = {
            'partner_id':
            partner.commercial_partner_id.address_get(['invoice'])
            .get('invoice', partner.commercial_partner_id.id),
            'move_type': 'out_invoice',
        }
        invoice_vals.update(self.env['account.move'].play_onchanges(
            invoice_vals, ['partner_id'],
        ))
        invoice = self.env['account.move'].create(invoice_vals)
        for lines in self._account_invoice_analytic_line_group_invoice_lines():
            self.search(
                lines['__domain']
            )._account_invoice_analytic_line_create_invoice_line(invoice)

        invoice._compute_amount()
        return invoice
    
    def _account_invoice_analytic_line_create_invoice_line(self, invoice):
        """Actually create an invoice line from lines in self. We assume they
        have the same product, project and discount"""
        if not self:
            return self.env['account.move.line']
        first = self[:1]
        quantity = sum(self.mapped('unit_amount'))
        product = (
            first.product_id or
            first.project_id.account_invoice_analytic_line_product_id or
            invoice.partner_id.account_invoice_analytic_line_product_id
        )
        if not product:
            raise UserError(_(
                'Neither your line, nor the project nor the partner define a '
                'product to use for invoicing, you need to set one of them.'
            ))

        price = product.with_context(
            pricelist=invoice.partner_id.property_product_pricelist.id,
            partner=invoice.partner_id.id,
            quantity=quantity,
        ).price
        total_price = quantity * price
            
        invoice_line_vals1 = {
            'product_id': product.id,
            'discount': first.invoice_discount_id.discount,
            'quantity': quantity,
            'price_unit': price,
            'exclude_from_invoice_tab': False,
        }
        invoice_line_vals2 = {
            'product_id': product.id,
            'discount': first.invoice_discount_id.discount,
            'quantity': 1.0,
            'price_unit': -total_price,
            'account_id':
                invoice.partner_id.property_account_receivable_id.id,
            'exclude_from_invoice_tab': True,
        }
        invoice_line_vals1.update(
            self.env['account.move.line'].play_onchanges(
                invoice_line_vals1,
                ['product_id', 'price_unit', 'discount', 'quantity'],
            )
        )
        invoice_line_vals2.update(
            self.env['account.move.line'].play_onchanges(
                invoice_line_vals2,
                ['product_id', 'price_unit', 'discount', 'quantity'],
            )
        )
        
        invoice_line_vals1['name'] = first.project_id.name
        invoice_line_vals1['credit'] = invoice_line_vals1['price_subtotal'] if 'price_subtotal' in invoice_line_vals1 else 0.0
        invoice_line_vals2['debit']  = invoice_line_vals1['credit']
        
        invoice.line_ids = [
            (0, 0, invoice_line_vals1),
            (0, 0, invoice_line_vals2)
        ]
        #first.move_id = invoice.line_ids[-2].id

    def _account_invoice_analytic_line_group_invoice_lines(self):
        """Group lines that are supposed to be an invoice line"""
        return self.read_group(
            [('id', 'in', self.ids)],
            ['product_id', 'invoice_discount_id', 'project_id'],
            ['product_id', 'invoice_discount_id', 'project_id'],
            lazy=False,
        )

    def _account_invoice_analytic_line_group_invoice(self):
        """Group lines to invoice"""
        return self.read_group(
            [('id', 'in', self.ids)], ['partner_id'], ['partner_id'],
        )

    def _find_partner(self):
        """Returns the partner connected to a account.analytic.line"""
        return self.partner_id or \
            self.task_id.partner_id if self.task_id != False else (
                self.project_id.partner_id if self.project_id != False \
                    else self.task_id.project_id.partner_id
            )