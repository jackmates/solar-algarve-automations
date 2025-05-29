{
    "name": "Solar Algarve Automations",
    "version": "16.0.3.0.0",  # Increment version
    "depends": ["sale", "crm", "purchase", "stock", "calendar", "mail"],  # Add calendar and mail
    "author": "MATES Inc",
    "category": "Solar Business Automation",
    "summary": "Complete solar installation business automation with site visit scheduling",
    "description": """
Solar Business Automation Suite
===============================

Complete automation for solar installation companies including:

CORE AUTOMATIONS:
* Lead qualification and quotation process
* Sales order confirmation and equipment procurement  
* Installation scheduling and progress tracking
* Permits, commissioning, and project completion
* Automatic stage progression based on real business events

NEW FEATURES:
* Direct site visit scheduling from CRM
* Quick appointment booking without leaving CRM view
* Automatic email confirmations to customers
* Calendar integration with team availability
* Stage progression when visits scheduled/completed

WORKFLOW:
1. Calendly/Cal.com creates lead
2. Sales call → Schedule site visit from CRM
3. Site visit completed → Auto-create quotation task
4. Customer signs → Equipment procurement automation
5. Installation scheduling and completion tracking

Designed specifically for solar installation companies.
    """,
    "data": [
        "views/crm_views.xml",  # Add this line
    ],
    "license": "LGPL-3",
    "installable": True,
    "auto_install": False,
}
