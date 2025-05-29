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
            if order.state == "sent" and order.opportunity_id:
                stage = self.env["crm.stage"].search([("name", "=", "Proposition")], limit=1)
                if stage:
                    order.opportunity_id.stage_id = stage.id
            
            elif order.state == "sale" and order.opportunity_id:
                # Mark as won (existing logic)
                if order.opportunity_id.probability < 100:
                    order.opportunity_id.action_set_won()
                
                # Check stock and create appropriate actions
                self._handle_confirmed_order()

    def _handle_confirmed_order(self):
        """Handle confirmed sales order with stock checking and appropriate actions"""
        
        # Analyze stock situation
        stock_analysis = self._analyze_stock_levels()
        
        if stock_analysis['all_in_stock']:
            # Everything in stock - proceed automatically
            self._auto_proceed_with_stock()
        elif stock_analysis['partial_stock']:
            # Some items in stock - create mixed action plan
            self._create_mixed_stock_action_plan(stock_analysis)
        else:
            # Nothing in stock - create procurement action plan
            self._create_procurement_action_plan(stock_analysis)

    def _analyze_stock_levels(self):
        """Analyze current stock levels for all order items"""
        analysis = {
            'all_in_stock': True,
            'partial_stock': False,
            'out_of_stock_items': [],
            'low_stock_items': [],
            'in_stock_items': [],
            'total_items': 0
        }
        
        for line in self.order_line:
            if line.product_id.type == 'product':  # Only check stockable products
                analysis['total_items'] += 1
                available_qty = line.product_id.qty_available
                required_qty = line.product_uom_qty
                
                if available_qty >= required_qty:
                    analysis['in_stock_items'].append({
                        'product': line.product_id,
                        'required': required_qty,
                        'available': available_qty,
                        'line': line
                    })
                elif available_qty > 0:
                    analysis['partial_stock'] = True
                    analysis['all_in_stock'] = False
                    analysis['low_stock_items'].append({
                        'product': line.product_id,
                        'required': required_qty,
                        'available': available_qty,
                        'shortage': required_qty - available_qty,
                        'line': line
                    })
                else:
                    analysis['all_in_stock'] = False
                    analysis['out_of_stock_items'].append({
                        'product': line.product_id,
                        'required': required_qty,
                        'available': 0,
                        'line': line
                    })
        
        return analysis

    def _auto_proceed_with_stock(self):
        """Automatically proceed when all items are in stock"""
        # Move to Ordered stage
        ordered_stage = self.env["crm.stage"].search([("name", "=", "Ordered")], limit=1)
        if ordered_stage and self.opportunity_id:
            self.opportunity_id.stage_id = ordered_stage.id
            
            # Update installation progress
            try:
                if hasattr(self.opportunity_id, 'x_installation_progress'):
                    self.opportunity_id.x_installation_progress = 'equipment_ordered'
            except:
                pass
            
            # Create activity for warehouse team
            self._create_activity(
                'Prepare Equipment for Delivery',
                f'All equipment for {self.opportunity_id.name} is in stock. Please prepare for delivery to installation site.',
                'mail.mail_activity_data_todo',
                days_ahead=1
            )
            
            # Message on opportunity
            self.opportunity_id.message_post(
                body="✅ All equipment in stock - order processing automatically",
                subject="Equipment Available - Ready for Delivery"
            )

    def _create_procurement_action_plan(self, stock_analysis):
        """Create action plan when items need to be procured"""
        
        # Stay in Won stage, don't move to Ordered yet
        try:
            if hasattr(self.opportunity_id, 'x_installation_progress'):
                self.opportunity_id.x_installation_progress = 'equipment_ordered'
        except:
            pass
        
        # Create purchase orders for out of stock items
        purchase_orders_created = self._create_purchase_orders(stock_analysis['out_of_stock_items'])
        
        # Create comprehensive action activity
        shortage_details = []
        for item in stock_analysis['out_of_stock_items']:
            shortage_details.append(f"• {item['product'].name}: Need {item['required']}, Have {item['available']}")
        
        activity_note = f"""
🚨 EQUIPMENT PROCUREMENT REQUIRED

Customer: {self.opportunity_id.partner_id.name if self.opportunity_id else self.partner_id.name}
Order: {self.name}

OUT OF STOCK ITEMS:
{chr(10).join(shortage_details)}

ACTIONS TAKEN:
✅ Purchase orders created: {', '.join([po.name for po in purchase_orders_created])}

NEXT STEPS:
1. Follow up with suppliers on delivery dates
2. Confirm lead times with customer if needed  
3. Update customer on expected delivery timeline
4. Move to "Ordered" stage once procurement confirmed
        """
        
        self._create_activity(
            '🚨 Equipment Procurement Required',
            activity_note,
            'mail.mail_activity_data_warning',  # Warning activity type
            days_ahead=0  # Immediate attention
        )
        
        # Message on opportunity
        self.opportunity_id.message_post(
            body=f"⚠️ Equipment procurement initiated - {len(stock_analysis['out_of_stock_items'])} items out of stock",
            subject="Procurement Required"
        )

    def _create_mixed_stock_action_plan(self, stock_analysis):
        """Handle partial stock situation"""
        
        try:
            if hasattr(self.opportunity_id, 'x_installation_progress'):
                self.opportunity_id.x_installation_progress = 'equipment_ordered'
        except:
            pass
        
        # Create purchase orders for missing items
        missing_items = stock_analysis['out_of_stock_items'] + stock_analysis['low_stock_items']
        purchase_orders_created = self._create_purchase_orders(missing_items)
        
        # Detailed breakdown
        in_stock_details = [f"✅ {item['product'].name}: {item['available']} available" 
                           for item in stock_analysis['in_stock_items']]
        shortage_details = [f"⚠️ {item['product'].name}: Need {item['required']}, Have {item['available']}" 
                           for item in missing_items]
        
        activity_note = f"""
📦 MIXED STOCK SITUATION

Customer: {self.opportunity_id.partner_id.name if self.opportunity_id else self.partner_id.name}
Order: {self.name}

IN STOCK:
{chr(10).join(in_stock_details)}

NEED TO PROCURE:
{chr(10).join(shortage_details)}

ACTIONS TAKEN:
✅ Purchase orders created: {', '.join([po.name for po in purchase_orders_created])}

DECISIONS NEEDED:
1. Partial delivery to customer or wait for complete order?
2. Customer timeline preferences?
3. Storage arrangement for early arriving items?
        """
        
        self._create_activity(
            '📦 Mixed Stock - Decision Required',
            activity_note,
            'mail.mail_activity_data_todo',
            days_ahead=0
        )

    def _create_purchase_orders(self, items_to_procure):
        """Create purchase orders for items that need procurement"""
        purchase_obj = self.env['purchase.order']
        vendor_products = {}
        
        # Group by vendor
        for item in items_to_procure:
            product = item['product']
            quantity = item.get('shortage', item['required'])  # Use shortage for partial stock
            
            if product.seller_ids:
                vendor = product.seller_ids[0].partner_id
                if vendor not in vendor_products:
                    vendor_products[vendor] = []
                vendor_products[vendor].append({
                    'product': product,
                    'quantity': quantity,
                    'price': product.seller_ids[0].price,
                })
        
        created_pos = []
        for vendor, products in vendor_products.items():
            po_vals = {
                'partner_id': vendor.id,
                'origin': self.name,
                'date_order': fields.Datetime.now(),
                'order_line': [],
            }
            
            for product_info in products:
                line_vals = {
                    'product_id': product_info['product'].id,
                    'product_qty': product_info['quantity'],
                    'price_unit': product_info['price'],
                    'date_planned': fields.Datetime.now() + timedelta(days=7),
                }
                po_vals['order_line'].append((0, 0, line_vals))
            
            purchase_order = purchase_obj.create(po_vals)
            created_pos.append(purchase_order)
        
        return created_pos

    def _create_activity(self, summary, note, activity_type_ref, days_ahead=1):
        """Create activity on the opportunity"""
        if not self.opportunity_id:
            return
            
        activity_vals = {
            'res_model': 'crm.lead',
            'res_id': self.opportunity_id.id,
            'activity_type_id': self.env.ref(activity_type_ref).id,
            'summary': summary,
            'note': note,
            'date_deadline': fields.Date.today() + timedelta(days=days_ahead),
            'user_id': self.opportunity_id.user_id.id or self.env.user.id,
        }
        
        self.env['mail.activity'].create(activity_vals)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def write(self, vals):
        res = super().write(vals)
        
        # Check if equipment delivery is complete
        if 'receipt_status' in vals and vals['receipt_status'] == 'full':
            self._check_order_completion()
            
        return res

    def _check_order_completion(self):
        """Check if all equipment for the sales order is now available"""
        # Find related sales order
        sale_orders = self.env['sale.order'].search([('name', '=', self.origin)])
        
        for sale_order in sale_orders:
            if sale_order.opportunity_id:
                # Re-analyze stock levels
                stock_analysis = sale_order._analyze_stock_levels()
                
                if stock_analysis['all_in_stock']:
                    # Everything now available - move to Ordered stage
                    ordered_stage = self.env["crm.stage"].search([("name", "=", "Ordered")], limit=1)
                    if ordered_stage:
                        sale_order.opportunity_id.stage_id = ordered_stage.id
                        
                        # Update progress
                        try:
                            sale_order.opportunity_id.x_installation_progress = 'equipment_delivered'
                        except:
                            pass
                        
                        # Create delivery planning activity
                        sale_order._create_activity(
                            '📦 Equipment Ready - Plan Delivery',
                            f'All equipment for {sale_order.opportunity_id.name} is now available. Please coordinate delivery to installation site.',
                            'mail.mail_activity_data_todo',
                            days_ahead=1
                        )
                        
                        # Notify team
                        sale_order.opportunity_id.message_post(
                            body=f"🎉 All equipment delivered from {self.name} - Ready for site delivery!",
                            subject="Equipment Complete - Ready for Installation"
                        )
