from netbox.plugins import PluginConfig
class BusinessApplicationConfig(PluginConfig):
    name = "business_application"  # Must match the plugin directory name
    verbose_name = "Business Application"
    description = "Manage business applications and their relationships to virtual machines"
    version = "1.0.3"
    base_url = "business-application"  # URL base for the plugin
    required_settings = []  # Define required settings if applicable
    min_version = "4.1.0"  # Minimum required NetBox version
    max_version = "4.1.99"  # Minimum required NetBox version
    default_settings = {
    }
# Required for NetBox to recognize the plugin
config = BusinessApplicationConfig
