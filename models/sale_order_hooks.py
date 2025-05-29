from odoo import models, api, fields
from datetime import timedelta

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # Add site visit event field
    x_site_visit_event_id = fields.Many2one('calendar.event', string='Site Visit Appointment')
    x_fully_qualified = fields.Boolean(string="Fully Qualified", help="Tick to confirm lead is qualified and ready for quotation")
    x_installation_photo_ids = fields.One2many('installation.photo', 'lead_id', string="Installation Photos")
    x_installation_meeting_id = fields.Many2one(
        'calendar.event', string='Installation Appointment',
        help="Schedule the installation meeting")

    def write(self, vals):
        res = super().write(vals)
        
        # Check for stage changes and create appropriate activities
        if 'stage_id' in vals:
            self._create_stage_based_activity(vals['stage_id'])
        
        # Auto-progress stages based on field updates
        self._check_stage_progression(vals)
            
        return res

    @api.model
    def create(self, vals):
        """Create initial activity when new opportunity is created"""
        lead = super().create(vals)

        # Create initial activity for new leads
        if lead.stage_id.name in ['New', 'Lead']:
            lead._create_stage_based_activity(lead.stage_id.id)
        
        return lead

    def _create_stage_based_activity(self, stage_id):
        """Create appropriate activity based on current stage"""
        stage = self.env['crm.stage'].browse(stage_id)
        activity_configs = {
            'New': {
                'title': '📞 First Contact – Qualification Script',
                'note': f"""
<h3>📞 FIRST CONTACT – {self.name}</h3>

<b>Customer:</b> {self.partner_id.name if self.partner_id else self.contact_name or 'Contact details needed'}<br/>
<b>Phone:</b> {self.phone or 'Phone number needed'}<br/>
<b>Email:</b> {self.email_from or 'Email needed'}<br/>
<b>Address:</b> {self._get_full_address() or 'Address needed'}<br/>

<h4>QUALIFICATION CHECKLIST:</h4>
□ Confirm customer goals and timeline<br/>
□ Discuss current electricity usage and costs<br/>
□ Identify decision-makers and budget expectations<br/>
□ Explain site visit and assessment process<br/>
□ Schedule site visit using the “Schedule Site Visit” button on this page<br/>
□ Record any relevant notes in the CRM<br/>

<h4>OPTIONAL QUESTIONS TO DEEPEN QUALIFICATION:</h4>
□ Property ownership (own vs rent)<br/>
□ Roof condition and age<br/>
□ Current monthly electricity cost<br/>
□ Interest level and timeline<br/>
□ Budget considerations<br/>
□ Decision-making process<br/>
□ Will they be home during the site visit?<br/>
□ Any special access or roof concerns?<br/>

<h4>NEXT STEP:</h4>
Schedule site visit and move to 'Qualified' stage
  """,
                'days': 0,
                'type': 'mail.mail_activity_data_call'
            },
            
            'Qualified': {
                'title': '🏠 Conduct Site Visit & Create Quotation',
                'note': f"""
<h3>🔍 SITE VISIT & ASSESSMENT - {self.name}</h3>

<b>Customer:</b> {self.partner_id.name if self.partner_id else self.contact_name}<br/>
<b>Site Visit:</b> {self.x_site_visit_event_id.name if hasattr(self, 'x_site_visit_event_id') and self.x_site_visit_event_id else 'Schedule appointment'}<br/>

<h4>SITE VISIT CHECKLIST:</h4>
□ Arrive on time and introduce yourself professionally<br/>
□ Assess roof condition, size, and orientation<br/>
□ Check electrical panel and available space<br/>
□ Measure roof dimensions and note obstacles<br/>
□ <b>Take photos of roof, electrical panel, and site</b><br/>
<i>Upload photos in the <b>Photos & Documentation</b> tab below. Use the image uploader to add multiple images and view thumbnails directly.</i><br/>
□ Discuss energy usage and electricity bills<br/>
□ Explain solar system design options<br/>
□ Answer customer questions and concerns<br/>

<h4>TECHNICAL ASSESSMENT:</h4>
□ Roof material and structural integrity<br/>
□ Shading analysis (trees, buildings, etc.)<br/>
□ Electrical system compatibility<br/>
□ Available roof space for panels<br/>
□ Grid connection requirements<br/>
□ Permit requirements for area<br/>

<h4>POST-VISIT TASKS:</h4>
□ Update customer record with site visit notes<br/>
□ Design preliminary solar system layout<br/>
□ Calculate system size and production estimates<br/>
□ Prepare detailed quotation with options<br/>
□ Include financial analysis and payback period<br/>
□ Schedule quotation presentation<br/>

<h4>NEXT STEP:</h4>
Create and send quotation, move to 'Proposition' stage
                """,
                'days': 1,
                'type': 'mail.mail_activity_data_meeting'
            },
            
            'Proposition': {
                'title': '💰 Quotation Follow-up & Customer Support',
                'note': f"""
<h3>📋 QUOTATION FOLLOW-UP - {self.name}</h3>

<b>Customer:</b> {self.partner_id.name if self.partner_id else self.contact_name}<br/>
<b>Quotation Sent:</b> {fields.Date.today().strftime('%Y-%m-%d')}<br/>

<h4>FOLLOW-UP CHECKLIST:</h4>
□ Confirm customer received quotation (call within 24h)<br/>
□ Schedule presentation call/meeting to review quotation<br/>
□ Answer any questions about system design<br/>
□ Explain financing options and incentives<br/>
□ Address concerns about installation process<br/>
□ Provide references from satisfied customers<br/>
□ Clarify warranty and maintenance terms<br/>

<h4>COMMON QUESTIONS TO PREPARE FOR:</h4>
□ How long will installation take?<br/>
□ What happens during bad weather?<br/>
□ Will system work during power outages?<br/>
□ Maintenance requirements and costs<br/>
□ Warranty coverage details<br/>
□ Permit and inspection process<br/>
□ Property value impact<br/>

<h4>SALES SUPPORT:</h4>
□ Calculate return on investment<br/>
□ Compare with competitors if needed<br/>
□ Explain company credentials and experience<br/>
□ Provide financing assistance if needed<br/>
□ Offer system monitoring demonstration<br/>
□ Schedule second opinion visit if requested<br/>

<h4>FOLLOW-UP SCHEDULE:</h4>
• Day 1: Confirm receipt<br/>
• Day 3: Presentation call<br/>
• Day 7: Check-in call<br/>
• Day 14: Final follow-up<br/>

<h4>NEXT STEP:</h4>
Close sale and move to 'Won' stage when customer signs
                """,
                'days': 1,
                'type': 'mail.mail_activity_data_call'
            },
            
            'Won': {
                'title': '📋 Stock Assessment & Procurement Planning',
                'note': f"""
<h3>📋 STOCK ASSESSMENT & PROCUREMENT - {self.name}</h3>

<b>Customer:</b> {self.partner_id.name if self.partner_id else self.contact_name}<br/>
<b>Sale Amount:</b> {self.expected_revenue or 'Update amount'}<br/>

<h4>STOCK AVAILABILITY CHECK:</h4>
□ Review all equipment requirements from quotation<br/>
□ Check current stock levels for each item<br/>
□ Identify items that need to be ordered<br/>
□ Confirm vendor availability and lead times<br/>
□ Calculate total procurement timeline<br/>

<h4>PROCUREMENT ACTIONS:</h4>
□ Create purchase orders for out-of-stock items<br/>
□ Follow up with suppliers on delivery dates<br/>
□ Arrange equipment storage if needed<br/>
□ Update procurement timeline based on vendor responses<br/>

<h4>CUSTOMER COMMUNICATION:</h4>
□ Email customer with project timeline update<br/>
□ Explain equipment ordering process and lead times<br/>
□ Provide realistic installation date estimates<br/>
□ Set expectations for next communication milestone<br/>
□ Send welcome packet with company information<br/>

<h4>PROJECT SETUP:</h4>
□ Assign project manager and installation team<br/>
□ Create customer project file<br/>
□ Begin permit application preparation<br/>
□ Schedule internal project kickoff meeting<br/>

<h4>TIMELINE COMMUNICATION TEMPLATE:</h4>
<i>"Thank you for choosing us for your solar installation! We're now ordering your equipment and preparing permits. Based on current supplier lead times, we expect to begin installation in [X] weeks. We'll keep you updated weekly on our progress."</i><br/>

<b>NOTE:</b> If all equipment is in stock, project will automatically move to "Ready to go" stage for installation scheduling.
                """,
                'days': 0,
                'type': 'mail.mail_activity_data_todo'
            },
            
            'Ordered': {
                'title': '📦 Track Equipment Procurement & Delivery',
                'note': f"""
<h3>📦 PROCUREMENT TRACKING - {self.name}</h3>

<b>Customer:</b> {self.partner_id.name if self.partner_id else self.contact_name}<br/>
<b>Status:</b> Equipment procurement in progress<br/>

<h4>PROCUREMENT MONITORING:</h4>
□ Review purchase order status for all suppliers<br/>
□ Follow up on delivery dates and lead times<br/>
□ Track shipment progress and expected arrivals<br/>
□ Coordinate with suppliers on any delays<br/>
□ Update customer on procurement timeline<br/>

<h4>INVENTORY MANAGEMENT:</h4>
□ Process receipts when equipment arrives<br/>
□ Inspect equipment quality and completeness<br/>
□ Update inventory system with received goods<br/>
□ Arrange equipment storage and handling<br/>
□ Verify all items against original order<br/>

<h4>DELIVERY COORDINATION:</h4>
□ Monitor delivery order status in system<br/>
□ Coordinate equipment delivery to installation site<br/>
□ Confirm site access and delivery logistics<br/>
□ Schedule equipment delivery timing<br/>

<h4>CUSTOMER COMMUNICATION:</h4>
□ Provide weekly procurement status updates<br/>
□ Notify customer of any delivery delays<br/>
□ Confirm installation timeline based on equipment arrival<br/>
□ Prepare customer for next phase (installation scheduling)<br/>

<h4>SYSTEM INTEGRATION:</h4>
<i>The system automatically tracks:</i><br/>
• Purchase order receipts and inventory updates<br/>
• Delivery order fulfillment capability<br/>
• Stock reservation status for your order<br/>
• Auto-progression to "Ready to go" when equipment complete<br/>

<h4>NEXT STEP:</h4>
System will automatically move to "Ready to go" when all equipment is available for delivery
                """,
                'days': 2,
                'type': 'mail.mail_activity_data_todo'
            },
            
            'Ready to go': {
                'title': '📅 Installation Scheduling & Team Coordination',
                'note': f"""
<h3>📅 SCHEDULE INSTALLATION - {self.name}</h3>

<b>Customer:</b> {self.partner_id.name if self.partner_id else self.contact_name}<br/>
<b>Status:</b> All equipment ready for installation<br/>

<h4>CUSTOMER SCHEDULING:</h4>
□ Call customer to schedule installation dates<br/>
□ Offer 2-3 available installation windows<br/>
□ Confirm customer availability during installation<br/>
□ Discuss any site preparation requirements<br/>
□ Confirm access arrangements (keys, parking, etc.)<br/>
□ Send installation confirmation email with dates<br/>

<h4>INSTALLATION TEAM COORDINATION:</h4>
□ Assign installation crew and team leader<br/>
□ Confirm team availability for scheduled dates<br/>
□ Brief team on site-specific requirements<br/>
□ Prepare installation drawings and documentation<br/>
□ Ensure all tools and safety equipment ready<br/>
□ Plan equipment delivery to site<br/>

<h4>PRE-INSTALLATION CHECKLIST:</h4>
□ Verify permits are approved and available<br/>
□ Check weather forecast for installation period<br/>
□ Confirm electrical panel accessibility<br/>
□ Arrange equipment delivery timing<br/>
□ Prepare customer communication materials<br/>
□ Schedule any required inspections<br/>

<h4>INSTALLATION LOGISTICS:</h4>
□ Confirm site access and parking arrangements<br/>
□ Notify neighbors if appropriate<br/>
□ Plan backup dates for weather delays<br/>
□ Prepare installation timeline for customer<br/>
□ Set up daily progress communication plan<br/>

<h4>CUSTOMER COMMUNICATION:</h4>
□ Provide installation team contact information<br/>
□ Explain installation process and timeline<br/>
□ Set expectations for daily progress updates<br/>
□ Confirm any customer responsibilities<br/>

<h4>NEXT STEP:</h4>
Create installation meeting in calendar and move to 'Scheduling' stage
                """,
                'days': 1,
                'type': 'mail.mail_activity_data_call'
            }
        }
        
        if stage.name in activity_configs:
            config = activity_configs[stage.name]
            self._safe_create_activity(
                config['title'],
                config['note'],
                config['type'],
                days_ahead=config['days']
            )

    # _create_intro_call_activity method removed

    def _get_full_address(self):
        """Get formatted full address"""
        address_parts = []
        if self.street:
            address_parts.append(self.street)
        if self.street2:
            address_parts.append(self.street2)
        if self.city:
            address_parts.append(self.city)
        if self.state_id:
            address_parts.append(self.state_id.name)
        if self.zip:
            address_parts.append(self.zip)
        if self.country_id:
            address_parts.append(self.country_id.name)
        
        return ', '.join(address_parts) if address_parts else None

    def action_schedule_site_visit(self):
        """Action to schedule a site visit calendar event"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Schedule Site Visit',
            'res_model': 'calendar.event',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_name': f'Site Visit - {self.name}',
                'default_description': f'Solar site assessment for {self.partner_id.name if self.partner_id else self.contact_name}',
                'default_duration': 2.0,
                'default_opportunity_id': self.id,
                'default_partner_ids': [(6, 0, [self.partner_id.id] if self.partner_id else [])],
            },
            'on_close': {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }
        }

    @api.multi
    def action_schedule_installation(self):
        """Action to schedule the installation meeting"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Schedule Installation',
            'res_model': 'calendar.event',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_name': f'Installation - {self.name}',
                'default_description': f'Installation for {self.partner_id.name or self.contact_name}',
                'default_duration': 4.0,
                'default_opportunity_id': self.id,
                'default_partner_ids': [(6, 0, [self.partner_id.id] if self.partner_id else [])],
            },
            'on_close': {'type': 'ir.actions.client', 'tag': 'reload'},
        }

    def _check_stage_progression(self, vals):
        """Check if stage should progress based on field updates"""
        
        # Site visit completed -> move to Qualified (if not already)
        if 'x_site_visit_event_id' in vals and vals['x_site_visit_event_id']:
            if self.stage_id.name == 'New':
                qualified_stage = self.env['crm.stage'].search([('name', '=', 'Qualified')], limit=1)
                if qualified_stage:
                    self.stage_id = qualified_stage.id
                    self._create_stage_based_activity(qualified_stage.id)
                    self.message_post(
                        body="📅 <b>Site Visit Scheduled</b><br/>Moving to Qualified stage for site assessment.",
                        subject="Site Visit Scheduled"
                    )
        
        # Fully qualified checkbox ticked -> move to Qualified (if not already)
        elif 'x_fully_qualified' in vals and vals['x_fully_qualified']:
            if self.stage_id.name == 'New':
                qualified_stage = self.env['crm.stage'].search([('name', '=', 'Qualified')], limit=1)
                if qualified_stage:
                    self.stage_id = qualified_stage.id
                    self._create_stage_based_activity(qualified_stage.id)
                    self.message_post(
                        body="✅ <b>Lead Fully Qualified</b><br/>Moved to Qualified stage based on manual confirmation.",
                        subject="Lead Qualified"
                    )
        
        # Installation meeting scheduled -> Scheduling stage
        elif 'x_installation_meeting_id' in vals and vals['x_installation_meeting_id']:
            self._auto_progress_to_scheduling()
        
        # Installation progress updates -> various stage progressions
        elif 'x_installation_progress' in vals:
            self._auto_progress_by_installation_status(vals['x_installation_progress'])
        
        # Permits submitted -> Permits stage
        elif 'x_permits_submitted' in vals and vals['x_permits_submitted']:
            self._auto_progress_to_permits()
        
        # Customer sign-off -> Complete stage
        elif ('x_signoff_date' in vals and vals['x_signoff_date']) or \
             ('x_customer_signature' in vals and vals['x_customer_signature']):
            self._check_project_completion()

    def _auto_progress_to_scheduling(self):
        """Move to Scheduling when installation meeting is scheduled"""
        if self.stage_id.name in ['Ordered', 'Ready to go']:
            stage = self.env['crm.stage'].search([('name', '=', 'Scheduling')], limit=1)
            if stage:
                self.stage_id = stage.id
                
                # Update installation progress
                try:
                    if hasattr(self, 'x_installation_progress'):
                        self.x_installation_progress = 'installation_scheduled'
                except:
                    pass
                
                # Create preparation checklist
                self._create_installation_preparation_activity()
                
                self.message_post(
                    body="📅 <b>Installation Scheduled</b><br/>Installation meeting created. Moving to scheduling phase.",
                    subject="Installation Meeting Scheduled"
                )

    def _auto_progress_by_installation_status(self, progress_value):
        """Auto-progress stage based on installation progress value"""
        
        stage_mappings = {
            'equipment_delivered': ('Ready to go', "Equipment has been delivered and is ready for installation."),
            'installation_in_progress': ('Installing', "Installation work has begun on site."),
            'electrical_complete': ('Installing', "Electrical work completed, continuing installation phase."),
            'system_testing': ('Installing', "System testing in progress."),
            'utility_inspection': ('Permits', "System ready for utility inspection."),
            'interconnection_approved': ('Permits', "Utility interconnection approved."),
            'system_commissioned': ('Commissioned', "System has been commissioned and is operational."),
            'project_complete': ('Complete', "Project completed successfully.")
        }
        
        if progress_value in stage_mappings:
            target_stage_name, message = stage_mappings[progress_value]
            stage = self.env['crm.stage'].search([('name', '=', target_stage_name)], limit=1)
            
            if stage and self.stage_id.name != target_stage_name:
                self.stage_id = stage.id
                
                # Create appropriate follow-up activities
                self._create_progress_based_activity(progress_value)
                
                self.message_post(
                    body=f"⚡ <b>Progress Update</b><br/>{message}",
                    subject=f"Installation Progress: {progress_value.replace('_', ' ').title()}"
                )

    def _auto_progress_to_permits(self):
        """Move to Permits when permits are submitted"""
        if self.stage_id.name == 'Installing':
            stage = self.env['crm.stage'].search([('name', '=', 'Permits')], limit=1)
            if stage:
                self.stage_id = stage.id
                
                # Update installation progress
                try:
                    if hasattr(self, 'x_installation_progress'):
                        self.x_installation_progress = 'utility_inspection'
                except:
                    pass
                
                # Create permit tracking activity
                self._create_permit_tracking_activity()
                
                self.message_post(
                    body="📋 <b>Permits Submitted</b><br/>Installation permits have been submitted for approval.",
                    subject="Permits Submitted for Approval"
                )

    def _check_project_completion(self):
        """Check if project can be marked as complete"""
        try:
            has_signoff_date = hasattr(self, 'x_signoff_date') and self.x_signoff_date
            has_customer_signature = hasattr(self, 'x_customer_signature') and self.x_customer_signature
            
            if has_signoff_date and has_customer_signature and self.stage_id.name == 'Commissioned':
                stage = self.env['crm.stage'].search([('name', '=', 'Complete')], limit=1)
                if stage:
                    self.stage_id = stage.id
                    
                    # Update installation progress
                    try:
                        if hasattr(self, 'x_installation_progress'):
                            self.x_installation_progress = 'project_complete'
                    except:
                        pass
                    
                    # Create post-completion follow-up
                    self._create_project_completion_activity()
                    
                    self.message_post(
                        body="🎉 <b>Project Completed!</b><br/>Customer has signed off and project is officially complete.",
                        subject="Solar Installation Project Complete"
                    )
        except Exception as e:
            # Log but don't break the flow
            import logging
            _logger = logging.getLogger(__name__)
            _logger.warning(f"Error in project completion check: {e}")

    def _create_installation_preparation_activity(self):
        """Create activity for installation preparation"""
        activity_note = f"""
<h3>🔧 INSTALLATION PREPARATION CHECKLIST</h3>

<b>Project:</b> {self.name}<br/>
<b>Customer:</b> {self.partner_id.name if self.partner_id else 'N/A'}<br/>

<h4>PRE-INSTALLATION TASKS:</h4>
□ Confirm equipment delivery to site<br/>
□ Verify installation team availability<br/>
□ Check weather forecast for installation dates<br/>
□ Confirm site access and parking arrangements<br/>
□ Review safety requirements and protocols<br/>
□ Prepare installation documentation<br/>
□ Contact customer 24h before installation<br/>

<b>Installation Meeting:</b> {self.x_installation_meeting_id.name if hasattr(self, 'x_installation_meeting_id') and self.x_installation_meeting_id else 'Scheduled'}
        """
        
        self._safe_create_activity(
            '🔧 Installation Preparation Checklist',
            activity_note,
            'mail.mail_activity_data_todo',
            days_ahead=1
        )
        # reminder one week ahead of the installation meeting
        if self.x_installation_meeting_id and self.x_installation_meeting_id.start:
            install_dt = self.x_installation_meeting_id.start
            # parse if it's a string
            if isinstance(install_dt, str):
                install_dt = fields.Datetime.from_string(install_dt)
            from datetime import timedelta as _timedelta
            reminder_date = (install_dt - _timedelta(days=7)).date()
            days_until_reminder = (reminder_date - fields.Date.today()).days
            if days_until_reminder > 0:
                self._safe_create_activity(
                    '🔔 Installation Scheduling Reminder',
                    '<h4>Prepare for installation:</h4>□ Contact customer to arrange installation based on weather and timing<br/>□ Begin building BRES boxes and other pre-install tasks',
                    'mail.mail_activity_data_todo',
                    days_ahead=days_until_reminder
                )

    def _create_progress_based_activity(self, progress_value):
        """Create appropriate activity based on installation progress"""
        
        activity_configs = {
            'installation_in_progress': {
                'title': '⚡ Monitor Installation Progress',
                'note': f"""
Installation started for {self.name}

DAILY MONITORING TASKS:
□ Check installation team progress
□ Monitor safety compliance
□ Update customer on progress
□ Document any issues or delays
□ Take progress photos
□ Ensure quality standards

Expected completion: Check with installation team
                """,
                'days': 0
            },
            'system_testing': {
                'title': '🔍 System Testing & Quality Check', 
                'note': f"""
System testing phase for {self.name}

TESTING CHECKLIST:
□ Solar panel output verification
□ Inverter functionality test
□ Electrical connections check
□ Safety systems test
□ Performance monitoring setup
□ Documentation of test results

Next: Prepare for utility inspection
                """,
                'days': 1
            },
            'system_commissioned': {
                'title': '📋 Prepare Customer Handover',
                'note': f"""
System commissioned for {self.name} - Prepare handover

HANDOVER PREPARATION:
□ Prepare system documentation
□ Create customer operation manual
□ Schedule customer training session
□ Prepare warranty information
□ Set up monitoring access for customer
□ Prepare final invoice

Schedule customer sign-off meeting
                """,
                'days': 2
            }
        }
        
        if progress_value in activity_configs:
            config = activity_configs[progress_value]
            self._safe_create_activity(
                config['title'],
                config['note'],
                'mail.mail_activity_data_todo',
                days_ahead=config['days']
            )

    def _create_permit_tracking_activity(self):
        """Create activity for permit tracking"""
        activity_note = f"""
📋 PERMIT TRACKING - {self.name}

PERMIT STATUS MONITORING:
□ Confirm permit application received
□ Track approval status with utility company
□ Follow up on any additional requirements
□ Schedule utility inspection when approved
□ Prepare for interconnection process

TYPICAL TIMELINE:
• Initial review: 5-10 business days
• Site inspection: 2-5 business days after approval
• Final approval: 1-3 business days after inspection

Contact utility company if no response within expected timeframe.
        """
        
        self._safe_create_activity(
            '📋 Track Permit Approval Progress',
            activity_note,
            'mail.mail_activity_data_todo',
            days_ahead=3
        )

    def _create_project_completion_activity(self):
        """Create post-completion follow-up activity"""
        activity_note = f"""
🎉 POST-COMPLETION FOLLOW-UP - {self.name}

COMPLETION TASKS:
□ Send completion confirmation to customer
□ Provide final system documentation
□ Set up monitoring system access
□ Schedule 30-day performance check
□ Create maintenance schedule
□ Process final invoicing
□ Request customer review/testimonial
□ Update CRM records and close project

FOLLOW-UP SCHEDULE:
• 30 days: Performance check
• 6 months: System maintenance
• 12 months: Annual inspection
        """
        
        self._safe_create_activity(
            '🎉 Project Completion Follow-up',
            activity_note,
            'mail.mail_activity_data_todo',
            days_ahead=1
        )

    def _safe_create_activity(self, summary, note, activity_type_ref, days_ahead=1):
        """Safely create activity with error handling"""
        try:
            # Get the model ID for crm.lead
            model_id = self.env['ir.model'].search([('model', '=', 'crm.lead')], limit=1)
            
            # Get activity type - fallback to TODO if specific type not found
            try:
                activity_type = self.env.ref(activity_type_ref)
            except:
                activity_type = self.env.ref('mail.mail_activity_data_todo')
            
            activity_vals = {
                'res_model': 'crm.lead',
                'res_model_id': model_id.id,
                'res_id': self.id,
                'activity_type_id': activity_type.id,
                'summary': summary,
                'note': note,
                'date_deadline': fields.Date.today() + timedelta(days=days_ahead),
                'user_id': self.user_id.id or self.env.user.id,
            }
            
            self.env['mail.activity'].create(activity_vals)
            
        except Exception as e:
            # If activity creation fails, at least post a message
            import logging
            _logger = logging.getLogger(__name__)
            _logger.warning(f"Could not create activity: {e}")
            
            # Convert line breaks to HTML for message posting
            formatted_note = note.replace('\n', '<br/>')
            
            self.message_post(
                body=f"<b>{summary}</b><br/>{formatted_note}",
                subject=summary
            )


# Extend Calendar Event to link back to opportunities
class CalendarEvent(models.Model):
    _inherit = 'calendar.event'
    
    opportunity_id = fields.Many2one('crm.lead', string='Related Opportunity')
    
    def write(self, vals):
        res = super().write(vals)
        
        # If this is a site visit and it's marked as done, update the opportunity
        if 'state' in vals and vals['state'] == 'done':
            for event in self:
                if event.opportunity_id and 'Site Visit' in event.name:
                    # Mark site visit as completed and create follow-up activity
                    event.opportunity_id.message_post(
                        body=f"✅ <b>Site Visit Completed</b><br/>Site assessment finished. Ready for quotation preparation.",
                        subject="Site Visit Completed"
                    )
        
        return res


# Gallery-friendly image model
class InstallationPhoto(models.Model):
    _name = 'installation.photo'
    _description = 'Installation Photo'

    name = fields.Char('Description')
    image = fields.Binary('Image', attachment=True)
    lead_id = fields.Many2one('crm.lead', string='Opportunity')

    @api.model
    def create(self, vals):
        record = super().create(vals)

        # Also create a standard ir.attachment record for visibility in chatter
        if record.image and record.lead_id:
            self.env['ir.attachment'].create({
                'name': record.name or 'Installation Photo',
                'datas': record.image,
                'res_model': 'crm.lead',
                'res_id': record.lead_id.id,
                'type': 'binary',
                'mimetype': 'image/png',  # optionally detect from filename
            })

        return record

