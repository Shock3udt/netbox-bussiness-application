from netbox.plugins import PluginConfig


class BusinessApplicationConfig(PluginConfig):
    name = "business_application"  # Must match the plugin directory name
    verbose_name = "Business Application"
    description = "Manage business applications and their relationships to virtual machines"
    version = "2.1.0"  # Bumped version for PagerDuty sync feature
    base_url = "business-application"  # URL base for the plugin
    required_settings = []  # Define required settings if applicable
    min_version = "4.1.0"  # Minimum required NetBox version
    max_version = "4.5.0"  # Maximum required NetBox version
    default_settings = {
        # PagerDuty integration settings
        'pagerduty_incident_creation_enabled': True,  # Enable/disable automatic PagerDuty incident creation
        # External Workflow (AAP/N8N) Settings
        'aap_default_url': '',           # Default AAP Controller URL
        'aap_auth_type': 'token',        # Authentication type: 'basic' or 'token'
        'aap_username': '',              # AAP username (for basic auth)
        'aap_password': '',              # AAP password (for basic auth)
        'aap_token': '',                 # AAP OAuth/Bearer token (for token auth)
        'aap_verify_ssl': True,          # Verify SSL for AAP
        'aap_timeout': 30,               # Request timeout in seconds
        'n8n_default_url': '',           # Default N8N instance URL
        'n8n_api_key': '',               # N8N API key (optional)
        'n8n_verify_ssl': True,          # Verify SSL for N8N
        'n8n_timeout': 30,               # Request timeout in seconds
        'workflow_execution_enabled': True,  # Master switch for workflow execution
    }
    installed_apps = [
        'django_htmx',
    ]

    def ready(self):
        """
        Called when Django starts. Import signals to register them.
        """
        super().ready()
        # Import signals to register them
        try:
            from . import signals  # noqa: F401
        except ImportError as e:
            import logging
            logger = logging.getLogger('business_application')
            logger.warning(f"Could not import signals module: {e}")


# Required for NetBox to recognize the plugin
config = BusinessApplicationConfig