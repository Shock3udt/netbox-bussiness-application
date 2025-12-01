from django.conf import settings


class ExternalWorkflowConfig:
    """
    Configuration settings for external workflow integrations (AAP/N8N).
    These can be overridden in Django settings via PLUGINS_CONFIG.

    Example configuration in NetBox's configuration.py:

    PLUGINS_CONFIG = {
        'business_application': {
            # AAP Settings
            'aap_default_url': 'https://aap.example.com',
            'aap_auth_type': 'basic',  # 'basic' or 'token'
            'aap_username': 'admin',   # For basic auth
            'aap_password': 'password', # For basic auth
            'aap_token': 'your-aap-oauth-token',  # For token auth
            'aap_verify_ssl': True,
            'aap_timeout': 30,

            # N8N Settings
            'n8n_default_url': 'https://n8n.example.com',
            'n8n_api_key': '',
            'n8n_verify_ssl': True,
            'n8n_timeout': 30,

            'workflow_execution_enabled': True,
        }
    }
    """

    @property
    def AAP_DEFAULT_URL(self):
        """Default AAP Controller URL."""
        plugin_config = getattr(settings, 'PLUGINS_CONFIG', {}).get('business_application', {})
        return plugin_config.get('aap_default_url', '')

    @property
    def AAP_AUTH_TYPE(self):
        """AAP authentication type: 'basic' or 'token'."""
        plugin_config = getattr(settings, 'PLUGINS_CONFIG', {}).get('business_application', {})
        return plugin_config.get('aap_auth_type', 'token')

    @property
    def AAP_USERNAME(self):
        """AAP username for basic authentication."""
        plugin_config = getattr(settings, 'PLUGINS_CONFIG', {}).get('business_application', {})
        return plugin_config.get('aap_username', '')

    @property
    def AAP_PASSWORD(self):
        """AAP password for basic authentication."""
        plugin_config = getattr(settings, 'PLUGINS_CONFIG', {}).get('business_application', {})
        return plugin_config.get('aap_password', '')

    @property
    def AAP_TOKEN(self):
        """AAP OAuth/Bearer token for authentication."""
        plugin_config = getattr(settings, 'PLUGINS_CONFIG', {}).get('business_application', {})
        return plugin_config.get('aap_token', '')

    @property
    def AAP_VERIFY_SSL(self):
        """Whether to verify SSL certificates for AAP connections."""
        plugin_config = getattr(settings, 'PLUGINS_CONFIG', {}).get('business_application', {})
        return plugin_config.get('aap_verify_ssl', True)

    @property
    def AAP_TIMEOUT(self):
        """Timeout in seconds for AAP API requests."""
        plugin_config = getattr(settings, 'PLUGINS_CONFIG', {}).get('business_application', {})
        return plugin_config.get('aap_timeout', 30)

    @property
    def N8N_DEFAULT_URL(self):
        """Default N8N instance URL."""
        plugin_config = getattr(settings, 'PLUGINS_CONFIG', {}).get('business_application', {})
        return plugin_config.get('n8n_default_url', '')

    @property
    def N8N_API_KEY(self):
        """N8N API key for authenticated webhooks (optional)."""
        plugin_config = getattr(settings, 'PLUGINS_CONFIG', {}).get('business_application', {})
        return plugin_config.get('n8n_api_key', '')

    @property
    def N8N_VERIFY_SSL(self):
        """Whether to verify SSL certificates for N8N connections."""
        plugin_config = getattr(settings, 'PLUGINS_CONFIG', {}).get('business_application', {})
        return plugin_config.get('n8n_verify_ssl', True)

    @property
    def N8N_TIMEOUT(self):
        """Timeout in seconds for N8N webhook requests."""
        plugin_config = getattr(settings, 'PLUGINS_CONFIG', {}).get('business_application', {})
        return plugin_config.get('n8n_timeout', 30)

    @property
    def WORKFLOW_EXECUTION_ENABLED(self):
        """Whether workflow execution is enabled (master switch)."""
        plugin_config = getattr(settings, 'PLUGINS_CONFIG', {}).get('business_application', {})
        return plugin_config.get('workflow_execution_enabled', True)


# Singleton instance
external_workflow_config = ExternalWorkflowConfig()


class IncidentAutomationConfig:
    """
    Configuration settings for incident automation features.
    These can be overridden in Django settings.
    """

    @property
    def ENABLED(self):
        """Whether incident automation is enabled globally."""
        return getattr(settings, 'BUSINESS_APP_AUTO_INCIDENTS_ENABLED', True)

    @property
    def AUTO_RESOLVE_ENABLED(self):
        """Whether incidents should be auto-resolved when all events are OK."""
        return getattr(settings, 'BUSINESS_APP_AUTO_RESOLVE_INCIDENTS', False)

    @property
    def CORRELATION_WINDOW_MINUTES(self):
        """Time window in minutes for correlating events into incidents."""
        return getattr(settings, 'BUSINESS_APP_CORRELATION_WINDOW_MINUTES', 15)

    @property
    def MAX_DEPENDENCY_DEPTH(self):
        """Maximum depth to traverse in dependency graph for correlation."""
        return getattr(settings, 'BUSINESS_APP_MAX_DEPENDENCY_DEPTH', 5)

    @property
    def CORRELATION_THRESHOLD(self):
        """Minimum correlation score (0-1) required to group events."""
        return getattr(settings, 'BUSINESS_APP_CORRELATION_THRESHOLD', 0.3)

    @property
    def NOTIFICATIONS_ENABLED(self):
        """Whether to send notifications for new incidents."""
        return getattr(settings, 'BUSINESS_APP_INCIDENT_NOTIFICATIONS_ENABLED', False)

    @property
    def NOTIFICATION_WEBHOOKS(self):
        """Webhook URLs for incident notifications."""
        return getattr(settings, 'BUSINESS_APP_NOTIFICATION_WEBHOOKS', [])

    @property
    def EXCLUDE_EVENT_SOURCES(self):
        """Event sources to exclude from automatic incident creation."""
        return getattr(settings, 'BUSINESS_APP_EXCLUDE_EVENT_SOURCES', [])

    @property
    def REQUIRE_MINIMUM_SEVERITY(self):
        """Minimum event severity required for incident creation."""
        return getattr(settings, 'BUSINESS_APP_REQUIRE_MINIMUM_SEVERITY', 'warning')

    @property
    def AUTO_ASSIGNMENT_ENABLED(self):
        """Whether to automatically assign incidents to teams/users."""
        return getattr(settings, 'BUSINESS_APP_AUTO_ASSIGNMENT_ENABLED', False)

    @property
    def DEFAULT_INCIDENT_COMMANDER(self):
        """Default incident commander for auto-created incidents."""
        return getattr(settings, 'BUSINESS_APP_DEFAULT_INCIDENT_COMMANDER', 'Ops Team')