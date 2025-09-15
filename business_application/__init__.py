from netbox.plugins import PluginConfig

class BusinessApplicationConfig(PluginConfig):
    name = "business_application"  # Must match the plugin directory name
    verbose_name = "Business Application"
    description = "Manage business applications and their relationships to virtual machines"
    version = "2.0.0"
    base_url = "business-application"  # URL base for the plugin
    required_settings = []  # Define required settings if applicable
    min_version = "4.1.0"  # Minimum required NetBox version
    max_version = "4.3.0"  # Minimum required NetBox version
    default_settings = {
    }
    installed_apps = [
        'django_htmx',
    ]
# Required for NetBox to recognize the plugin
config = BusinessApplicationConfig
