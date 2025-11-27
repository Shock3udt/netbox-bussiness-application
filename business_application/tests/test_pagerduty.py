"""
Django unit tests for PagerDuty integration.

Tests cover:
- PagerDutyConfig settings
- PagerDutyClient methods
- Helper functions (severity mapping, dedup keys)
- Signal handlers
- API views
"""

from datetime import timedelta
from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType

from business_application.models import (
    Event, Incident, EventStatus, EventCrit, TechnicalService,
    EventSource, IncidentStatus, IncidentSeverity
)
from business_application.utils.pagerduty import (
    PagerDutyClient,
    PagerDutyConfig,
    PagerDutyError,
    PagerDutyEventSeverity,
    PagerDutyEventAction,
    pagerduty_config,
    map_netbox_severity_to_pagerduty,
    map_netbox_status_to_pagerduty_action,
    generate_dedup_key,
    send_event_to_pagerduty,
    send_incident_to_pagerduty,
)


class PagerDutyConfigTestCase(TestCase):
    """Test PagerDutyConfig reads settings correctly."""

    def test_default_values(self):
        """Test default configuration values."""
        config = PagerDutyConfig()
        self.assertFalse(config.enabled)
        self.assertIsNone(config.routing_key)
        self.assertEqual(config.source, 'netbox')
        self.assertEqual(config.timeout, 30)
        self.assertTrue(config.send_on_event_create)
        self.assertTrue(config.send_on_incident_create)

    @override_settings(PAGERDUTY_ENABLED=True)
    def test_enabled_setting(self):
        """Test PAGERDUTY_ENABLED setting."""
        config = PagerDutyConfig()
        self.assertTrue(config.enabled)

    @override_settings(PAGERDUTY_ROUTING_KEY='test-routing-key-12345')
    def test_routing_key_setting(self):
        """Test PAGERDUTY_ROUTING_KEY setting."""
        config = PagerDutyConfig()
        self.assertEqual(config.routing_key, 'test-routing-key-12345')

    @override_settings(PAGERDUTY_SOURCE='custom-source')
    def test_source_setting(self):
        """Test PAGERDUTY_SOURCE setting."""
        config = PagerDutyConfig()
        self.assertEqual(config.source, 'custom-source')

    @override_settings(PAGERDUTY_SEND_ON_EVENT_CREATE=False)
    def test_send_on_event_create_setting(self):
        """Test PAGERDUTY_SEND_ON_EVENT_CREATE setting."""
        config = PagerDutyConfig()
        self.assertFalse(config.send_on_event_create)


class PagerDutyClientTestCase(TestCase):
    """Test PagerDutyClient functionality."""

    def test_is_configured_false_when_disabled(self):
        """Test is_configured returns False when disabled."""
        client = PagerDutyClient()
        self.assertFalse(client.is_configured)

    @override_settings(PAGERDUTY_ENABLED=True, PAGERDUTY_ROUTING_KEY='test-key')
    def test_is_configured_true_when_enabled(self):
        """Test is_configured returns True when properly configured."""
        client = PagerDutyClient()
        self.assertTrue(client.is_configured)

    def test_routing_key_override(self):
        """Test routing key can be overridden in constructor."""
        client = PagerDutyClient(routing_key='override-key')
        self.assertEqual(client.routing_key, 'override-key')

    @override_settings(PAGERDUTY_ENABLED=True, PAGERDUTY_ROUTING_KEY='test-key')
    @patch('business_application.utils.pagerduty.urlopen')
    def test_trigger_success(self, mock_urlopen):
        """Test successful trigger event."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"status": "success", "dedup_key": "test-key"}'
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        client = PagerDutyClient()
        result = client.trigger(
            summary="Test alert",
            severity="warning",
            dedup_key="test-dedup-001"
        )

        self.assertEqual(result['status'], 'success')
        mock_urlopen.assert_called_once()

    @override_settings(PAGERDUTY_ENABLED=True, PAGERDUTY_ROUTING_KEY='test-key')
    @patch('business_application.utils.pagerduty.urlopen')
    def test_resolve_success(self, mock_urlopen):
        """Test successful resolve event."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"status": "success"}'
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        client = PagerDutyClient()
        result = client.resolve(dedup_key="test-dedup-001")

        self.assertEqual(result['status'], 'success')

    @override_settings(PAGERDUTY_ENABLED=True, PAGERDUTY_ROUTING_KEY='test-key')
    @patch('business_application.utils.pagerduty.urlopen')
    def test_acknowledge_success(self, mock_urlopen):
        """Test successful acknowledge event."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"status": "success"}'
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        client = PagerDutyClient()
        result = client.acknowledge(dedup_key="test-dedup-001")

        self.assertEqual(result['status'], 'success')

    def test_trigger_skipped_when_not_configured(self):
        """Test trigger is skipped when not configured."""
        client = PagerDutyClient()
        result = client.trigger(summary="Test", severity="warning")

        self.assertEqual(result['status'], 'skipped')


class SeverityMappingTestCase(TestCase):
    """Test severity and status mapping functions."""

    def test_map_critical_severity(self):
        """Test CRITICAL maps to critical."""
        self.assertEqual(
            map_netbox_severity_to_pagerduty('CRITICAL'),
            PagerDutyEventSeverity.CRITICAL
        )

    def test_map_high_severity(self):
        """Test HIGH maps to error."""
        self.assertEqual(
            map_netbox_severity_to_pagerduty('HIGH'),
            PagerDutyEventSeverity.ERROR
        )

    def test_map_medium_severity(self):
        """Test MEDIUM maps to warning."""
        self.assertEqual(
            map_netbox_severity_to_pagerduty('MEDIUM'),
            PagerDutyEventSeverity.WARNING
        )

    def test_map_low_severity(self):
        """Test LOW maps to info."""
        self.assertEqual(
            map_netbox_severity_to_pagerduty('LOW'),
            PagerDutyEventSeverity.INFO
        )

    def test_map_unknown_severity(self):
        """Test unknown severity defaults to warning."""
        self.assertEqual(
            map_netbox_severity_to_pagerduty('UNKNOWN'),
            PagerDutyEventSeverity.WARNING
        )

    def test_map_lowercase_severity(self):
        """Test lowercase severity values."""
        self.assertEqual(
            map_netbox_severity_to_pagerduty('critical'),
            PagerDutyEventSeverity.CRITICAL
        )


class StatusMappingTestCase(TestCase):
    """Test status to action mapping."""

    def test_triggered_maps_to_trigger(self):
        """Test triggered status maps to trigger action."""
        self.assertEqual(
            map_netbox_status_to_pagerduty_action('triggered'),
            PagerDutyEventAction.TRIGGER
        )

    def test_new_maps_to_trigger(self):
        """Test new status maps to trigger action."""
        self.assertEqual(
            map_netbox_status_to_pagerduty_action('new'),
            PagerDutyEventAction.TRIGGER
        )

    def test_ok_maps_to_resolve(self):
        """Test ok status maps to resolve action."""
        self.assertEqual(
            map_netbox_status_to_pagerduty_action('ok'),
            PagerDutyEventAction.RESOLVE
        )

    def test_resolved_maps_to_resolve(self):
        """Test resolved status maps to resolve action."""
        self.assertEqual(
            map_netbox_status_to_pagerduty_action('resolved'),
            PagerDutyEventAction.RESOLVE
        )

    def test_monitoring_maps_to_acknowledge(self):
        """Test monitoring status maps to acknowledge action."""
        self.assertEqual(
            map_netbox_status_to_pagerduty_action('monitoring'),
            PagerDutyEventAction.ACKNOWLEDGE
        )

    def test_unknown_returns_none(self):
        """Test unknown status returns None."""
        self.assertIsNone(
            map_netbox_status_to_pagerduty_action('unknown_status')
        )


class DedupKeyTestCase(TestCase):
    """Test deduplication key generation."""

    def test_generate_dedup_key(self):
        """Test dedup key generation."""
        key = generate_dedup_key('event', 123, 'device')
        self.assertEqual(key, 'netbox-event-device-123')

    def test_generate_dedup_key_default_type(self):
        """Test dedup key with default type."""
        key = generate_dedup_key('incident', 456)
        self.assertEqual(key, 'netbox-incident-generic-456')


class SendEventToPagerDutyTestCase(TestCase):
    """Test send_event_to_pagerduty helper function."""

    def setUp(self):
        """Set up test data."""
        self.event_source = EventSource.objects.create(
            name='test-source',
            description='Test event source'
        )
        self.service = TechnicalService.objects.create(
            name='test-service',
            service_type='technical'
        )

    def test_returns_none_when_disabled(self):
        """Test returns None when PagerDuty is disabled."""
        event = Event.objects.create(
            message="Test event",
            status=EventStatus.TRIGGERED,
            criticallity=EventCrit.WARNING,
            dedup_id="test-001",
            last_seen_at=timezone.now(),
            event_source=self.event_source
        )

        result = send_event_to_pagerduty(event)
        self.assertIsNone(result)

    @override_settings(PAGERDUTY_ENABLED=True, PAGERDUTY_ROUTING_KEY='test-key')
    @patch('business_application.utils.pagerduty.PagerDutyClient.trigger')
    def test_sends_triggered_event(self, mock_trigger):
        """Test triggered event is sent to PagerDuty."""
        mock_trigger.return_value = {'status': 'success'}

        event = Event.objects.create(
            message="Test triggered event",
            status=EventStatus.TRIGGERED,
            criticallity=EventCrit.CRITICAL,
            dedup_id="test-002",
            last_seen_at=timezone.now(),
            event_source=self.event_source
        )

        result = send_event_to_pagerduty(event)

        self.assertIsNotNone(result)
        mock_trigger.assert_called_once()

    @override_settings(PAGERDUTY_ENABLED=True, PAGERDUTY_ROUTING_KEY='test-key')
    @patch('business_application.utils.pagerduty.PagerDutyClient.resolve')
    def test_sends_ok_event_as_resolve(self, mock_resolve):
        """Test OK event sends resolve to PagerDuty."""
        mock_resolve.return_value = {'status': 'success'}

        event = Event.objects.create(
            message="Test OK event",
            status=EventStatus.OK,
            criticallity=EventCrit.INFO,
            dedup_id="test-003",
            last_seen_at=timezone.now(),
            event_source=self.event_source
        )

        result = send_event_to_pagerduty(event)

        self.assertIsNotNone(result)
        mock_resolve.assert_called_once()


class SendIncidentToPagerDutyTestCase(TestCase):
    """Test send_incident_to_pagerduty helper function."""

    def setUp(self):
        """Set up test data."""
        self.service = TechnicalService.objects.create(
            name='test-service',
            service_type='technical'
        )

    def test_returns_none_when_disabled(self):
        """Test returns None when PagerDuty is disabled."""
        incident = Incident.objects.create(
            title="Test incident",
            status=IncidentStatus.NEW,
            severity=IncidentSeverity.HIGH,
            description="Test description"
        )

        result = send_incident_to_pagerduty(incident)
        self.assertIsNone(result)

    @override_settings(PAGERDUTY_ENABLED=True, PAGERDUTY_ROUTING_KEY='test-key')
    @patch('business_application.utils.pagerduty.PagerDutyClient.trigger')
    def test_sends_new_incident(self, mock_trigger):
        """Test new incident is sent to PagerDuty."""
        mock_trigger.return_value = {'status': 'success'}

        incident = Incident.objects.create(
            title="Test incident",
            status=IncidentStatus.NEW,
            severity=IncidentSeverity.CRITICAL,
            description="Critical test incident"
        )
        incident.affected_services.add(self.service)

        result = send_incident_to_pagerduty(incident)

        self.assertIsNotNone(result)
        mock_trigger.assert_called_once()

    @override_settings(PAGERDUTY_ENABLED=True, PAGERDUTY_ROUTING_KEY='test-key')
    @patch('business_application.utils.pagerduty.PagerDutyClient.resolve')
    def test_sends_resolved_incident(self, mock_resolve):
        """Test resolved incident sends resolve to PagerDuty."""
        mock_resolve.return_value = {'status': 'success'}

        incident = Incident.objects.create(
            title="Test incident",
            status=IncidentStatus.RESOLVED,
            severity=IncidentSeverity.HIGH,
            description="Resolved incident",
            resolved_at=timezone.now()
        )

        result = send_incident_to_pagerduty(incident, action=PagerDutyEventAction.RESOLVE)

        self.assertIsNotNone(result)
        mock_resolve.assert_called_once()


class PagerDutySignalTestCase(TestCase):
    """Test PagerDuty signal handlers."""

    def setUp(self):
        """Set up test data."""
        self.event_source = EventSource.objects.create(
            name='test-source',
            description='Test source'
        )

    @override_settings(
        PAGERDUTY_ENABLED=True,
        PAGERDUTY_ROUTING_KEY='test-key',
        BUSINESS_APP_AUTO_INCIDENTS_ENABLED=False  # Disable auto incidents for this test
    )
    @patch('business_application.signals.send_event_to_pagerduty')
    def test_event_creation_triggers_pagerduty(self, mock_send):
        """Test creating an event triggers PagerDuty send."""
        mock_send.return_value = {'status': 'success'}

        event = Event.objects.create(
            message="Signal test event",
            status=EventStatus.TRIGGERED,
            criticallity=EventCrit.WARNING,
            dedup_id="signal-test-001",
            last_seen_at=timezone.now(),
            event_source=self.event_source
        )

        mock_send.assert_called()

    @override_settings(PAGERDUTY_ENABLED=False)
    @patch('business_application.signals.send_event_to_pagerduty')
    def test_event_creation_skipped_when_disabled(self, mock_send):
        """Test event creation doesn't trigger PagerDuty when disabled."""
        event = Event.objects.create(
            message="Disabled test event",
            status=EventStatus.TRIGGERED,
            criticallity=EventCrit.WARNING,
            dedup_id="disabled-test-001",
            last_seen_at=timezone.now(),
            event_source=self.event_source
        )

        # Should not be called because PagerDuty is disabled
        mock_send.assert_not_called()


class PagerDutyErrorHandlingTestCase(TestCase):
    """Test error handling in PagerDuty integration."""

    @override_settings(PAGERDUTY_ENABLED=True, PAGERDUTY_ROUTING_KEY='test-key')
    @patch('business_application.utils.pagerduty.urlopen')
    def test_http_error_raises_pagerduty_error(self, mock_urlopen):
        """Test HTTP errors are converted to PagerDutyError."""
        from urllib.error import HTTPError

        mock_urlopen.side_effect = HTTPError(
            url='https://events.pagerduty.com/v2/enqueue',
            code=400,
            msg='Bad Request',
            hdrs={},
            fp=None
        )

        client = PagerDutyClient()

        with self.assertRaises(PagerDutyError):
            client.trigger(summary="Test", severity="warning")

    @override_settings(PAGERDUTY_ENABLED=True, PAGERDUTY_ROUTING_KEY='test-key')
    @patch('business_application.utils.pagerduty.urlopen')
    def test_url_error_raises_pagerduty_error(self, mock_urlopen):
        """Test URL errors are converted to PagerDutyError."""
        from urllib.error import URLError

        mock_urlopen.side_effect = URLError(reason='Connection refused')

        client = PagerDutyClient()

        with self.assertRaises(PagerDutyError):
            client.trigger(summary="Test", severity="warning")

    @override_settings(PAGERDUTY_ENABLED=True, PAGERDUTY_ROUTING_KEY='test-key')
    @patch('business_application.utils.pagerduty.urlopen')
    def test_invalid_json_raises_pagerduty_error(self, mock_urlopen):
        """Test invalid JSON response raises PagerDutyError."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'not valid json'
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        client = PagerDutyClient()

        with self.assertRaises(PagerDutyError):
            client.trigger(summary="Test", severity="warning")