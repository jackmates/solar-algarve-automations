from odoo import models, api, fields
from datetime import timedelta

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # Add site visit event field
    x_site_visit_event_id = fields.Many2one('calendar.event', string='Site Visit Appointment')

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
        
        # Create initial contact activity for new leads
        if lead.stage_id.name in ['New', 'Lead']:
            lead._create_stage_based_activity(lead.stage_id.id)
            
        return lead

    def _create_stage_based_activity(self, stage_id):
        """Create appropriate activity based on current stage"""
        stage = self.env['crm.stage'].browse(stage_id)
        
        activity_configs = {
            'New': {
                'title': '📞 Initial Customer Contact & Site Visit Setup',
                'note': f"""
<h3>🏠 NEW SOLAR LEAD - {self.name}</h3>

<b>Customer:</b> {self.partner_id.name if self.partner_id else self.contact_name or 'Contact details needed'}<br/>
<b>Phone:</b> {self.phone or 'Phone number needed'}<br/>
<b>Email:</b> {self.email_from or 'Email needed'}<br/>
<b>Address:</b> {self._get_full_address() or 'Address needed'}<br/>

<h4>INITIAL CONTACT CHECKLIST:</h4>
□ Call customer to introduce company and services<br/>
□ Verify contact information and property address<br/>
□ Ask about current electricity bills and usage<br/>
□ Explain solar benefits and our process<br/>
□ Schedule site visit appointment<br/>
□ Send welcome email with company information<br/>
□ Gather preliminary roof/property information<br/>

<h4>QUALIFICATION QUESTIONS:</h4>
□ Property ownership (own vs rent)<br/>
□ Roof condition and age<br/>
□ Current monthly electricity cost<br/>
□ Interest level and timeline<br/>
□ Budget considerations<br/>
□ Decision-making process<br/>

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
□ Take photos of roof, electrical panel, and site<br/>
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
                'title': '🎉 Contract Signed - Initiate Project Setup',
                'note': f"""
<h3>✅ CONTRACT SIGNED - {self.name}</h3>

<b>Customer:</b> {self.partner_id.name if self.partner_id else self.contact_name}<br/>
<b>Sale Amount:</b> {self.expected_revenue or 'Update amount'}<br/>

<h4>IMMEDIATE POST-SALE TASKS:</h4>
□ Send welcome packet with next steps timeline<br/>
□ Create customer file with all documentation<br/>
□ Verify final system specifications<br/>
□ Confirm installation address and access<br/>
□ Schedule permit application submission<br/>
□ Order equipment based on final design<br/>
□ Assign project manager and installation team<br/>
□ Update customer with project timeline<br/>

<h4>DOCUMENTATION CHECKLIST:</h4>
□ Signed contract and terms<br/>
□ Site assessment photos and notes<br/>
□ System design specifications<br/>
□ Electrical panel photos<br/>
□ Property survey (if required)<br/>
□ HOA approval (if applicable)<br/>
□ Utility account information<br/>

<h4>PERMIT PREPARATION:</h4>
□ Gather property surveys and site plans<br/>
□ Prepare electrical drawings<br/>
□ Submit utility interconnection application<br/>
□ Apply for local building permits<br/>
□ Schedule utility pre-inspection (if required)<br/>

<h4>CUSTOMER COMMUNICATION:</h4>
□ Send project timeline and milestones<br/>
□ Provide contact information for project team<br/>
□ Explain permit and inspection process<br/>
□ Set expectations for installation timing<br/>

<i>The system will automatically check equipment availability and create purchase orders if needed.</i>
                """,
                'days': 0,
                'type': 'mail.mail_activity_data_todo'
            },
            
            'Ordered': {
                'title': '📦 Equipment Management & Delivery Coordination',
                'note': f"""
<h3>📦 EQUIPMENT PHASE - {self.name}</h3>

<b>Customer:</b> {self.partner_id.name if self.partner_id else self.contact_name}<br/>
<b>Equipment Status:</b> Ordered/In Transit<br/>

<h4>EQUIPMENT COORDINATION:</h4>
□ Track equipment delivery status with suppliers<br/>
□ Confirm delivery timeline with customer<br/>
□ Arrange equipment storage if needed<br/>
□ Inspect equipment upon delivery<br/>
□ Verify equipment matches order specifications<br/>
□ Update customer on equipment arrival<br/>
□ Coordinate site delivery timing<br/>

<h4>PERMIT STATUS CHECK:</h4>
□ Follow up on building permit application<br/>
□ Track utility interconnection approval<br/>
□ Resolve any permit issues or requirements<br/>
□ Schedule inspections once permits approved<br/>
□ Notify customer of permit approval status<br/>

<h4>INSTALLATION PREPARATION:</h4>
□ Confirm installation team availability<br/>
□ Schedule installation dates with customer<br/>
□ Arrange equipment delivery to site<br/>
□ Verify site access and parking arrangements<br/>
□ Confirm any special installation requirements<br/>

<h4>CUSTOMER UPDATE:</h4>
□ Provide weekly progress updates<br/>
□ Confirm contact information for installation<br/>
□ Discuss any site preparation needs<br/>
□ Schedule pre-installation walkthrough<br/>

<h4>NEXT STEP:</h4>
Move to 'Ready to go' when all equipment arrives
                """,
                'days': 2,
                'type': 'mail.mail_activity_data_todo'
            },
            
            'Ready to go': {
                'title': '🚛 Installation Scheduling & Site Preparation',
                'note': f"""
<h3>🚛 READY FOR INSTALLATION - {self.name}</h3>

<b>Customer:</b> {self.partner_id.name if self.partner_id else self.contact_name}<br/>
<b>Equipment:</b> All delivered and ready<br/>

<h4>INSTALLATION SCHEDULING:</h4>
□ Contact customer to schedule installation dates<br/>
□ Confirm 2-3 day installation window<br/>
□ Check weather forecast for installation period<br/>
□ Schedule installation team and equipment<br/>
□ Arrange delivery of equipment to site<br/>
□ Confirm site access and parking arrangements<br/>

<h4>PRE-INSTALLATION REQUIREMENTS:</h4>
□ Verify permits are approved and available<br/>
□ Confirm electrical panel accessibility<br/>
□ Check roof access and safety requirements<br/>
□ Arrange for any required site preparation<br/>
□ Notify neighbors if appropriate<br/>
□ Confirm customer will be available during installation<br/>

<h4>CUSTOMER COMMUNICATION:</h4>
□ Call customer to schedule installation<br/>
□ Send installation confirmation with dates<br/>
□ Provide installation team contact information<br/>
□ Explain what to expect during installation<br/>
□ Confirm any special requirements or concerns<br/>
□ Schedule pre-installation walkthrough if needed<br/>

<h4>TEAM PREPARATION:</h4>
□ Brief installation team on site specifics<br/>
□ Prepare installation drawings and specifications<br/>
□ Ensure all tools and safety equipment ready<br/>
□ Confirm backup plans for weather delays<br/>

<h4>NEXT STEP:</h4>
Create installation meeting and move to 'Scheduling'
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
                'default_duration': 2.0,  # 2 hours
                'default_opportunity_id': self.id,
                'default_partner_ids': [(6, 0, [self.partner_id.id] if self.partner_id else [])],
            }
        }

    def _check_stage_progression(self, vals):
        """Check if stage should progress based on field updates"""
        
        # Site visit completed -> move to Qualified (if not already)
        if 'x_site_visit_event_id' in vals and vals['x_site_visit_event_id']:
            if self.stage_id.name == 'New':
                qualified_stage = self.env['crm.stage'].search([('name', '=', 'Qualified')], limit=1)
                if qualified_stage:
                    self.stage_id = qualified_stage.id
                    self.message_post(
                        body="📅 <b>Site Visit Scheduled</b><br/>Moving to Qualified stage for site assessment.",
                        subject="Site Visit Scheduled"
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
            
            self.message_post(
                body=f"<b>{summary}</b><br/>{note.replace(chr(10), '<br/>')}",
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
