from django.conf import settings

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