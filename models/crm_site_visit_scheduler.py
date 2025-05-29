# -*- coding: utf-8 -*-
"""
CRM Site Visit Scheduler

Direct calendar event creation from CRM opportunity view for site visits.
Includes quick scheduling, team assignment, and automatic stage progression.
"""

from odoo import models, api, fields
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    """
    Enhanced CRM Lead with direct site visit scheduling capabilities
    """
    _inherit = 'crm.lead'

    # Site visit fields
    x_site_visit_event_id = fields.Many2one(
        'calendar.event',
        string='Site Visit Appointment',
        help='Scheduled site visit calendar event'
    )
    
    x_site_visit_status = fields.Selection([
        ('not_scheduled', 'Not Scheduled'),
        ('scheduled', 'Scheduled'), 
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Site Visit Status', compute='_compute_site_visit_status', store=True)
    
    # Quick scheduling fields (for the popup form)
    x_proposed_visit_date = fields.Datetime(
        string='Proposed Visit Date',
        help='Suggested date/time for site visit (temporary field for scheduling)'
    )
    
    x_visit_duration = fields.Float(
        string='Visit Duration (Hours)',
        default=2.0,
        help='Expected duration of site visit'
    )
    
    x_visit_notes = fields.Text(
        string='Visit Preparation Notes',
        help='Special instructions or requirements for the site visit'
    )

    @api.depends('x_site_visit_event_id.state')
    def _compute_site_visit_status(self):
        """Compute site visit status based on linked calendar event"""
        for lead in self:
            if not lead.x_site_visit_event_id:
                lead.x_site_visit_status = 'not_scheduled'
            elif lead.x_site_visit_event_id.state == 'done':
                lead.x_site_visit_status = 'completed'
            elif lead.x_site_visit_event_id.state == 'cancelled':
                lead.x_site_visit_status = 'cancelled'
            else:
                lead.x_site_visit_status = 'scheduled'

    def action_quick_schedule_site_visit(self):
        """
        Open quick scheduling popup for site visit
        
        Returns:
            dict: Action to open scheduling wizard
        """
        # Get suggested time slots
        suggested_times = self._get_suggested_time_slots()
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Schedule Site Visit - {self.name}',
            'res_model': 'site.visit.scheduler.wizard',
            'view_mode': 'form',
            'target': 'new',  # Opens as popup
            'context': {
                'default_opportunity_id': self.id,
                'default_customer_name': self.partner_id.name if self.partner_id else self.contact_name,
                'default_customer_phone': self.phone,
                'default_customer_email': self.email_from,
                'default_visit_address': self._get_visit_address(),
                'default_suggested_times': suggested_times,
                'default_duration': 2.0,
                'default_assigned_user_id': self.user_id.id,
            }
        }

    def action_schedule_site_visit_full(self):
        """
        Open full calendar event form for site visit (if quick scheduler isn't enough)
        
        Returns:
            dict: Action to open calendar event form
        """
        return {
            'type': 'ir.actions.act_window',
            'name': f'Schedule Site Visit - {self.name}',
            'res_model': 'calendar.event',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_name': f'Site Visit - {self.name}',
                'default_description': self._build_site_visit_description(),
                'default_start': self._get_next_business_day(),
                'default_stop': self._get_next_business_day() + timedelta(hours=2),
                'default_duration': 2.0,
                'default_opportunity_id': self.id,
                'default_partner_ids': [(6, 0, [self.partner_id.id] if self.partner_id else [])],
                'default_location': self._get_visit_address(),
                'default_event_type': 'site_visit',
                'default_user_id': self.user_id.id,
                'default_alarm_ids': [(6, 0, [
                    self.env.ref('calendar.alarm_notif_1', raise_if_not_found=False).id,
                    self.env.ref('calendar.alarm_notif_2', raise_if_not_found=False).id
                ])]
            }
        }

    def action_view_site_visit(self):
        """
        View the scheduled site visit event
        
        Returns:
            dict: Action to view calendar event
        """
        if not self.x_site_visit_event_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'No site visit scheduled yet.',
                    'type': 'info'
                }
            }
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Site Visit Details',
            'res_model': 'calendar.event',
            'res_id': self.x_site_visit_event_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _get_suggested_time_slots(self):
        """
        Get suggested time slots for the next week
        
        Returns:
            list: List of suggested datetime slots
        """
        suggestions = []
        start_date = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        
        # Look for next 7 business days
        current_date = start_date
        while len(suggestions) < 10:  # Suggest up to 10 slots
            current_date += timedelta(days=1)
            
            # Skip weekends
            if current_date.weekday() >= 5:
                continue
            
            # Morning and afternoon slots
            for hour in [9, 14]:  # 9 AM and 2 PM
                slot_time = current_date.replace(hour=hour)
                
                # Check if user is available (simplified check)
                if self._is_user_available(slot_time, self.user_id):
                    suggestions.append({
                        'datetime': slot_time,
                        'display': slot_time.strftime('%A, %B %d at %I:%M %p'),
                        'timestamp': slot_time.isoformat()
                    })
        
        return suggestions[:10]  # Return first 10 suggestions

    def _is_user_available(self, check_time, user):
        """
        Simple availability check for user
        
        Args:
            check_time (datetime): Time to check
            user (res.users): User to check availability for
            
        Returns:
            bool: True if available
        """
        # Check for conflicting events (2-hour window)
        end_time = check_time + timedelta(hours=2)
        
        conflicts = self.env['calendar.event'].search([
            ('user_id', '=', user.id),
            ('start', '<', end_time),
            ('stop', '>', check_time),
            ('state', '!=', 'cancelled')
        ])
        
        return len(conflicts) == 0

    def _get_next_business_day(self):
        """Get next business day at 9 AM"""
        next_day = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
        
        # Skip to Monday if it's weekend
        while next_day.weekday() >= 5:
            next_day += timedelta(days=1)
        
        return next_day

    def _get_visit_address(self):
        """Get formatted address for site visit"""
        if self.partner_id:
            return self.partner_id._display_address() or 'Address to be confirmed'
        
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
        
        return ', '.join(address_parts) if address_parts else 'Address to be confirmed'

    def _build_site_visit_description(self):
        """Build comprehensive description for site visit event"""
        return f"""
SOLAR SITE ASSESSMENT VISIT

Customer: {self.partner_id.name if self.partner_id else self.contact_name}
Phone: {self.phone or 'Phone needed'}
Email: {self.email_from or 'Email needed'}
Property: {self._get_visit_address()}

VISIT OBJECTIVES:
• Assess roof condition, size, and orientation
• Evaluate electrical system compatibility  
• Measure available space for solar panels
• Discuss energy usage and requirements
• Take photos and site measurements
• Explain installation process and timeline

EQUIPMENT TO BRING:
• Measuring tape and laser measure
• Camera for documentation
• Roof assessment tools
• Electrical testing equipment
• iPad/tablet for notes and photos
• Business cards and brochures

CUSTOMER INFORMATION:
• Property type: {getattr(self, 'x_property_type', 'To be determined')}
• Current electricity cost: {getattr(self, 'x_monthly_electric_bill', 'To be discussed')}
• Solar interest level: {getattr(self, 'x_solar_interest', 'High')}

PREPARATION NOTES:
{self.description or 'No additional notes'}

Duration: Approximately 2 hours
Weather dependent: Check forecast before visit
        """

    @api.model
    def create(self, vals):
        """Override create to handle Calendly/Cal.com integration"""
        lead = super().create(vals)
        
        # If this lead came from Calendly/Cal.com (check source or origin)
        if vals.get('source_id') or 'calendly' in (vals.get('description', '').lower()):
            # Create initial contact activity
            lead._create_initial_contact_activity()
        
        return lead

    def _create_initial_contact_activity(self):
        """Create activity for initial sales call follow-up"""
        try:
            model_id = self.env['ir.model'].search([('model', '=', 'crm.lead')], limit=1)
            
            activity_vals = {
                'res_model': 'crm.lead',
                'res_model_id': model_id.id,
                'res_id': self.id,
                'activity_type_id': self.env.ref('mail.mail_activity_data_call').id,
                'summary': '📞 Sales Call - Profile & Schedule Site Visit',
                'note': f"""
<h3>📞 INITIAL SALES CALL - {self.name}</h3>

<b>Lead Source:</b> Calendly/Cal.com booking<br/>
<b>Customer:</b> {self.partner_id.name if self.partner_id else self.contact_name}<br/>
<b>Phone:</b> {self.phone or 'Phone number needed'}<br/>
<b>Email:</b> {self.email_from or 'Email needed'}<br/>

<h4>CALL OBJECTIVES:</h4>
□ Confirm customer contact information<br/>
□ Understand their solar interest and motivation<br/>
□ Gather property details (roof type, age, size)<br/>
□ Discuss current electricity costs<br/>
□ Explain our process and timeline<br/>
□ <b>Schedule site visit appointment</b><br/>
□ Send follow-up email with next steps<br/>

<h4>QUALIFICATION QUESTIONS:</h4>
□ Do you own or rent the property?<br/>
□ What's your average monthly electric bill?<br/>
□ What motivated you to consider solar?<br/>
□ What's your timeline for installation?<br/>
□ Who else is involved in the decision?<br/>

<h4>NEXT STEPS:</h4>
• Complete profile information in CRM<br/>
• Use "Schedule Site Visit" button to book appointment<br/>
• Send confirmation email to customer<br/>
• Move to "Qualified" stage after site visit scheduled<br/>

<b>💡 TIP:</b> Use the "Quick Schedule Site Visit" button below to book their appointment without leaving this page!
                """,
                'date_deadline': fields.Date.today(),  # Today
                'user_id': self.user_id.id or self.env.user.id,
            }
            
            self.env['mail.activity'].create(activity_vals)
            
        except Exception as e:
            _logger.warning(f"Could not create initial contact activity: {e}")


class SiteVisitSchedulerWizard(models.TransientModel):
    """
    Quick site visit scheduling wizard
    """
    _name = 'site.visit.scheduler.wizard'
    _description = 'Site Visit Quick Scheduler'

    # Opportunity link
    opportunity_id = fields.Many2one('crm.lead', string='Opportunity', required=True)
    
    # Customer information (read-only, for reference)
    customer_name = fields.Char(string='Customer', readonly=True)
    customer_phone = fields.Char(string='Phone', readonly=True)
    customer_email = fields.Char(string='Email', readonly=True)
    visit_address = fields.Text(string='Visit Address', readonly=True)
    
    # Scheduling fields
    visit_date = fields.Datetime(string='Visit Date & Time', required=True)
    duration = fields.Float(string='Duration (Hours)', default=2.0, required=True)
    assigned_user_id = fields.Many2one('res.users', string='Assigned To', required=True)
    
    # Optional fields
    visit_notes = fields.Text(string='Special Instructions')
    send_confirmation = fields.Boolean(string='Send Email Confirmation', default=True)
    
    # Suggested times (for UI convenience)
    suggested_times = fields.Text(string='Suggested Times', readonly=True)

    @api.model
    def default_get(self, fields_list):
        """Set default visit date to next business day"""
        defaults = super().default_get(fields_list)
        
        if 'visit_date' in fields_list:
            # Default to tomorrow at 9 AM if it's a business day
            tomorrow = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
            while tomorrow.weekday() >= 5:  # Skip weekends
                tomorrow += timedelta(days=1)
            defaults['visit_date'] = tomorrow
        
        return defaults

    def action_schedule_visit(self):
        """
        Create the calendar event and update opportunity
        
        Returns:
            dict: Action to close wizard and refresh CRM view
        """
        # Create calendar event
        event_vals = {
            'name': f'Site Visit - {self.opportunity_id.name}',
            'description': self._build_event_description(),
            'start': self.visit_date,
            'stop': self.visit_date + timedelta(hours=self.duration),
            'duration': self.duration,
            'user_id': self.assigned_user_id.id,
            'partner_ids': [(6, 0, [self.opportunity_id.partner_id.id] if self.opportunity_id.partner_id else [])],
            'opportunity_id': self.opportunity_id.id,
            'event_type': 'site_visit',
            'location': self.visit_address,
            'alarm_ids': [(6, 0, [
                self.env.ref('calendar.alarm_notif_1', raise_if_not_found=False).id,  # 1 hour before
                self.env.ref('calendar.alarm_notif_2', raise_if_not_found=False).id   # 1 day before
            ])],
        }
        
        # Add special instructions to description if provided
        if self.visit_notes:
            event_vals['description'] += f"\n\nSPECIAL INSTRUCTIONS:\n{self.visit_notes}"
        
        event = self.env['calendar.event'].create(event_vals)
        
        # Link event to opportunity
        self.opportunity_id.x_site_visit_event_id = event.id
        
        # Move to Qualified stage
        qualified_stage = self.env['crm.stage'].search([('name', '=', 'Qualified')], limit=1)
        if qualified_stage:
            self.opportunity_id.stage_id = qualified_stage.id
        
        # Send confirmation email if requested
        if self.send_confirmation and self.opportunity_id.email_from:
            self._send_confirmation_email(event)
        
        # Post message to opportunity
        self.opportunity_id.message_post(
            body=f"""
<b>✅ Site Visit Scheduled</b><br/>
<b>Date:</b> {self.visit_date.strftime('%A, %B %d, %Y at %I:%M %p')}<br/>
<b>Duration:</b> {self.duration} hours<br/>
<b>Assigned to:</b> {self.assigned_user_id.name}<br/>
<b>Address:</b> {self.visit_address}<br/>
{f'<b>Notes:</b> {self.visit_notes}<br/>' if self.visit_notes else ''}
            """,
            subject='Site Visit Scheduled'
        )
        
        # Return action to close wizard and show success
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Site Visit Scheduled!',
                'message': f'Visit scheduled for {self.visit_date.strftime("%A, %B %d at %I:%M %p")}',
                'type': 'success',
                'sticky': False,
            }
        }

    def _build_event_description(self):
        """Build detailed description for calendar event"""
        return f"""
SOLAR SITE ASSESSMENT VISIT

Customer: {self.customer_name}
Phone: {self.customer_phone or 'N/A'}
Email: {self.customer_email or 'N/A'}
Address: {self.visit_address}

OBJECTIVES:
• Roof assessment and measurements
• Electrical system evaluation
• Energy usage discussion
• System design consultation
• Installation process explanation

EQUIPMENT NEEDED:
• Measuring tools and camera
• Roof assessment equipment
• Electrical testing tools
• Sales materials

Duration: {self.duration} hours
        """

    def _send_confirmation_email(self, event):
        """Send confirmation email to customer"""
        try:
            # Build email content
            email_subject = f'Solar Site Visit Confirmed - {event.start.strftime("%B %d")}'
            email_body = f"""
<div style="font-family: Arial, sans-serif; max-width: 600px;">
    <h2>Your Solar Site Visit is Confirmed!</h2>
    
    <p>Dear {self.customer_name},</p>
    
    <p>Thank you for your interest in solar energy! Your site assessment visit has been scheduled.</p>
    
    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
        <h3>Appointment Details:</h3>
        <p><strong>Date:</strong> {event.start.strftime('%A, %B %d, %Y')}</p>
        <p><strong>Time:</strong> {event.start.strftime('%I:%M %p')}</p>
        <p><strong>Duration:</strong> Approximately {self.duration} hours</p>
        <p><strong>Address:</strong> {self.visit_address}</p>
        <p><strong>Your Solar Consultant:</strong> {self.assigned_user_id.name}</p>
    </div>
    
    <h3>What to Expect:</h3>
    <ul>
        <li>Comprehensive roof and property assessment</li>
        <li>Electrical system evaluation</li>
        <li>Discussion of your energy needs and goals</li>
        <li>Custom solar system design presentation</li>
        <li>Q&A about the solar installation process</li>
    </ul>
    
    <h3>Please Prepare:</h3>
    <ul>
        <li>Recent electricity bills (last 2-3 months)</li>
        <li>Clear access to electrical panel</li>
        <li>Any questions about solar energy</li>
    </ul>
    
    <p>We're excited to help you explore solar energy for your home!</p>
    
    <p>Questions? Reply to this email or call us at [Your Phone Number].</p>
    
    <p>Best regards,<br/>
    {self.assigned_user_id.name}<br/>
    [Your Company Name]</p>
</div>
            """
            
            # Send email
            mail_values = {
                'subject': email_subject,
                'body_html': email_body,
                'email_to': self.customer_email,
                'email_from': self.assigned_user_id.email or 'noreply@yourcompany.com',
            }
            
            mail = self.env['mail.mail'].create(mail_values)
            mail.send()
            
        except Exception as e:
            _logger.warning(f"Could not send confirmation email: {e}")


class CalendarEvent(models.Model):
    """
    Enhanced calendar event for site visit integration
    """
    _inherit = 'calendar.event'
    
    # Link back to opportunity
    opportunity_id = fields.Many2one('crm.lead', string='Related Opportunity')
    
    # Event type for filtering
    event_type = fields.Selection([
        ('site_visit', 'Site Visit'),
        ('installation', 'Installation'),
        ('follow_up', 'Follow-up'),
        ('meeting', 'Meeting'),
        ('other', 'Other')
    ], string='Event Type', default='other')

    def write(self, vals):
        """Handle event completion and trigger CRM progression"""
        res = super().write(vals)
        
        # When site visit is marked as done
        if 'state' in vals and vals['state'] == 'done':
            for event in self:
                if event.opportunity_id and event.event_type == 'site_visit':
                    event._handle_site_visit_completion()
        
        return res

    def _handle_site_visit_completion(self):
        """Handle CRM progression when site visit is completed"""
        opportunity = self.opportunity_id
        
        # Create post-site visit activity for quotation preparation
        try:
            model_id = self.env['ir.model'].search([('model', '=', 'crm.lead')], limit=1)
            
            activity_vals = {
                'res_model': 'crm.lead',
                'res_model_id': model_id.id,
                'res_id': opportunity.id,
                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                'summary': '📋 Prepare Solar Quotation',
                'note': f"""
<h3>📋 POST-SITE VISIT: QUOTATION PREPARATION</h3>

<b>Site Visit Completed:</b> {self.start.strftime('%Y-%m-%d %H:%M')}<br/>
<b>Customer:</b> {opportunity.partner_id.name if opportunity.partner_id else opportunity.contact_name}<br/>

<h4>QUOTATION TASKS:</h4>
□ Review site visit photos and measurements<br/>
□ Design optimal solar system layout<br/>
□ Calculate system size based on energy needs<br/>
□ Prepare detailed pricing with options<br/>
□ Include ROI analysis and financing options<br/>
□ Schedule quotation presentation call<br/>

<h4>FOLLOW-UP ACTIONS:</h4>
□ Send thank you email within 24 hours<br/>
□ Upload site photos to customer file<br/>
□ Create system design in design software<br/>
□ Prepare quotation within 48 hours<br/>
□ Schedule presentation appointment<br/>

<b>Target:</b> Send quotation within 48 hours and move to "Proposition" stage
                """,
                'date_deadline': fields.Date.today() + timedelta(days=2),
                'user_id': opportunity.user_id.id or self.env.user.id,
            }
            
            self.env['mail.activity'].create(activity_vals)
            
        except Exception as e:
            _logger.warning(f"Could not create post-site visit activity: {e}")
        
        # Log completion in opportunity chatter
        opportunity.message_post(
            body=f"""
<b>✅ Site Visit Completed Successfully</b><br/>
<b>Date:</b> {self.start.strftime('%A, %B %d, %Y at %I:%M %p')}<br/>
<b>Duration:</b> {self.duration} hours<br/>
<b>Consultant:</b> {self.user_id.name}<br/>
<b>Next Step:</b> Quotation preparation (activity created)
            """,
            subject='Site Visit Completed'
        )
