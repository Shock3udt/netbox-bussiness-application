from netbox.plugins import PluginConfig
import os

class BusinessApplicationConfig(PluginConfig):
    name = "business_application"  # Must match the plugin directory name
    verbose_name = "Business Application"
    description = "Manage business applications and their relationships to virtual machines"
    version = "2.0.0"
    base_url = "business-application"  # URL base for the plugin
    required_settings = []  # Define required settings if applicable
    min_version = "4.1.0"  # Minimum required NetBox version
    max_version = "4.5.0"  # Minimum required NetBox version
    default_settings = {
        'pagerduty_events_api_key': os.environ.get('PAGERDUTY_EVENTS_API_KEY'),  # PagerDuty Events API v2 routing key for incident creation
        'pagerduty_incident_creation_enabled': True,  # Enable/disable automatic PagerDuty incident creation
    }
    installed_apps = [
        'django_htmx',
    ]
# Required for NetBox to recognize the plugin
config = BusinessApplicationConfig
