from odoo import models, api, fields
from datetime import timedelta

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
            # Original automation: Move to Proposition when quotation sent
            if order.state == "sent" and order.opportunity_id:
                stage = self.env["crm.stage"].search([("name", "=", "Proposition")], limit=1)
                if stage:
                    order.opportunity_id.stage_id = stage.id
            
            # Enhanced automation: Move to Ordered when sales order confirmed
            elif order.state == "sale" and order.opportunity_id:
                # First, mark as won (your existing logic)
                if order.opportunity_id.probability < 100:
                    order.opportunity_id.action_set_won()
                
                # Then, move to Ordered stage and create purchase orders
                ordered_stage = self.env["crm.stage"].search([("name", "=", "Ordered")], limit=1)
                if ordered_stage:
                    order.opportunity_id.stage_id = ordered_stage.id
                    order.opportunity_id.x_installation_progress = 'equipment_ordered'
                
                # Create purchase orders for equipment
                self._create_equipment_purchase_orders()

    def _create_equipment_purchase_orders(self):
        """Create purchase orders for solar equipment when sales order is confirmed"""
        purchase_obj = self.env['purchase.order']
        
        # Group products by vendor for efficient purchase orders
        vendor_products = {}
        
        for line in self.order_line:
            product = line.product_id
            
            # Only process stockable products (not services)
            if product.type == 'product' and product.seller_ids:
                vendor = product.seller_ids[0].partner_id
                
                if vendor not in vendor_products:
                    vendor_products[vendor] = []
                vendor_products[vendor].append({
                    'product': product,
                    'quantity': line.product_uom_qty,
                    'price': product.seller_ids[0].price,
                })
        
        # Create purchase orders for each vendor
        for vendor, products in vendor_products.items():
            po_vals = {
                'partner_id': vendor.id,
                'origin': self.name,
                'date_order': fields.Datetime.now(),
                'order_line': [],
            }
            
            # Add order lines for each product
            for product_info in products:
                line_vals = {
                    'product_id': product_info['product'].id,
                    'product_qty': product_info['quantity'],
                    'price_unit': product_info['price'],
                    'date_planned': fields.Datetime.now() + timedelta(days=7),
                }
                po_vals['order_line'].append((0, 0, line_vals))
            
            # Create the purchase order
            purchase_order = purchase_obj.create(po_vals)
            
            # Link to opportunity
            if self.opportunity_id:
                self.opportunity_id.message_post(
                    body=f"Purchase Order {purchase_order.name} created for vendor {vendor.name}",
                    subject="Equipment Ordered"
                )


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    def write(self, vals):
        res = super().write(vals)
        
        # Auto-progress stages based on field updates
        if 'x_installation_progress' in vals:
            self._auto_progress_stage()
        elif 'x_installation_meeting_id' in vals and vals['x_installation_meeting_id']:
            self._auto_progress_to_scheduling()
        elif 'x_permits_submitted' in vals and vals['x_permits_submitted']:
            self._auto_progress_to_permits()
        elif 'x_signoff_date' in vals and vals['x_signoff_date'] and self.x_customer_signature:
            self._auto_progress_to_complete()
            
        return res

    def _auto_progress_stage(self):
        """Auto-progress CRM stage based on installation progress"""
        stage_mapping = {
            'equipment_delivered': 'Ready to go',
            'installation_in_progress': 'Installing',
            'system_commissioned': 'Commissioned',
            'project_complete': 'Complete'
        }
        
        if self.x_installation_progress in stage_mapping:
            target_stage_name = stage_mapping[self.x_installation_progress]
            stage = self.env['crm.stage'].search([('name', '=', target_stage_name)], limit=1)
            if stage:
                self.stage_id = stage.id

    def _auto_progress_to_scheduling(self):
        """Move to Scheduling when installation meeting is scheduled"""
        if self.stage_id.name == 'Ready to go':
            stage = self.env['crm.stage'].search([('name', '=', 'Scheduling')], limit=1)
            if stage:
                self.stage_id = stage.id
                self.x_installation_progress = 'installation_scheduled'

    def _auto_progress_to_permits(self):
        """Move to Permits when permits are submitted"""
        if self.stage_id.name == 'Installing':
            stage = self.env['crm.stage'].search([('name', '=', 'Permits')], limit=1)
            if stage:
                self.stage_id = stage.id
                self.x_installation_progress = 'utility_inspection'

    def _auto_progress_to_complete(self):
        """Move to Complete when customer signs off"""
        if self.stage_id.name == 'Commissioned':
            stage = self.env['crm.stage'].search([('name', '=', 'Complete')], limit=1)
            if stage:
                self.stage_id = stage.id
                self.x_installation_progress = 'project_complete'


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def write(self, vals):
        res = super().write(vals)
        
        # Update CRM when equipment is delivered
        if 'receipt_status' in vals and vals['receipt_status'] == 'full':
            self._update_crm_on_delivery()
            
        return res

    def _update_crm_on_delivery(self):
        """Update CRM opportunity when equipment is fully received"""
        # Find the related sales order and CRM opportunity
        sale_orders = self.env['sale.order'].search([('name', '=', self.origin)])
        
        for sale_order in sale_orders:
            if sale_order.opportunity_id:
                opportunity = sale_order.opportunity_id
                
                # Update installation progress
                opportunity.x_installation_progress = 'equipment_delivered'
                
                # Create delivery planning task
                activity_vals = {
                    'res_model': 'crm.lead',
                    'res_id': opportunity.id,
                    'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                    'summary': f'Plan equipment delivery for {opportunity.name}',
                    'note': f'Equipment has arrived. Coordinate delivery to installation site.',
                    'date_deadline': fields.Date.today() + timedelta(days=2),
                    'user_id': opportunity.user_id.id or self.env.user.id,
                }
                
                self.env['mail.activity'].create(activity_vals)
                
                # Add message to opportunity
                opportunity.message_post(
                    body=f"Equipment delivered from Purchase Order {self.name}",
                    subject="Equipment Ready for Site Delivery"
                )
