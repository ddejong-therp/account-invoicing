# -*- coding: utf-8 -*-
# Copyright 2018 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models


class AccountConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    account_invoice_analytic_line_product_id = fields.Many2one(
        'product.product', string='Invoice product for analytic lines',
        help='This product will be used to 6 analytic lines there is no '
        'explicit product configured on the customer or the project',
    )

    def set_values(self):
        res = super().set_values()
        self.env['ir.config_parameter'].set_param(
            'account_invoice_analytic_line.' \
            'account_invoice_analytic_line_product_id',
            self.account_invoice_analytic_line_product_id.id
        )
        return res

    @api.model
    def get_values(self):
        res = super().get_values()
        icp_sudo = self.env['ir.config_parameter'].sudo()
        product_id = icp_sudo.get_param(
            'account_invoice_analytic_line.' \
            'account_invoice_analytic_line_product_id'
        )
        res.update(account_invoice_analytic_line_product_id=int(product_id))
        return res
