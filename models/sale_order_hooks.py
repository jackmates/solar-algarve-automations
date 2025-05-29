from odoo import models, api

class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.model
    def create(self, vals):
        order = super().create(vals)
        order._trigger_custom_automations()
        return order

    def write(self, vals):
        res = super().write(vals)
        if "state" in vals:
            self._trigger_custom_automations()
        return res

    def _trigger_custom_automations(self):
        for order in self:
            if order.state == "sent" and order.opportunity_id:
                stage = self.env["crm.stage"].search([("name", "=", "Proposition")], limit=1)
                if stage:
                    order.opportunity_id.stage_id = stage.id
