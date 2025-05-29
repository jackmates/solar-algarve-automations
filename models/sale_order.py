from odoo import models, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def write(self, vals):
        res = super(SaleOrder, self).write(vals)

        # Check if state changed to 'sale' (i.e. signed)
        if 'state' in vals and vals['state'] == 'sale':
            for order in self:
                if order.opportunity_id and order.opportunity_id.probability < 100:
                    order.opportunity_id.action_set_won()
        return res
