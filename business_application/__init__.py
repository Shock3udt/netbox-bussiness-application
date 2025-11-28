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
        # Note: Routing keys are configured per TechnicalService or BusinessApplication,
        # not as a global setting. See pagerduty_routing_key field on those models.
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