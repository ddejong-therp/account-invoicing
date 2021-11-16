# -*- coding: utf-8 -*-
# Copyright 2018 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import _, api, fields, models
from odoo.addons import decimal_precision


class AccountMove(models.Model):
    _inherit = 'account.move'

    def unlink(self):
        # Unlink analytic lines from the invoice lines:
        self.line_ids.analytic_line_ids.move_id = False
        
        super().unlink()