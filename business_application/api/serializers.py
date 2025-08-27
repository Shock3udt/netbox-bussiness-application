from rest_framework import serializers
from business_application.models import (
    BusinessApplication, TechnicalService, ServiceDependency, EventSource, Event,
    Maintenance, ChangeType, Change, Incident, PagerDutyTemplate
)

from django.utils import timezone
from datetime import datetime

class BusinessApplicationSerializer(serializers.ModelSerializer):
    """
    Serializer for the BusinessApplication model.
    Provides representation for API interactions.
    """
    class Meta:
        model = BusinessApplication
        fields = [
            'id',
            'name',
            'appcode',
            'description',
            'owner',
            'delegate',
            'servicenow',
        ]

class TechnicalServiceSerializer(serializers.ModelSerializer):
    """
    Serializer for the TechnicalService model.
    """
    business_apps_count = serializers.IntegerField(source='business_apps.count', read_only=True)
    vms_count = serializers.IntegerField(source='vms.count', read_only=True)
    devices_count = serializers.IntegerField(source='devices.count', read_only=True)
    clusters_count = serializers.IntegerField(source='clusters.count', read_only=True)
    upstream_dependencies_count = serializers.SerializerMethodField(read_only=True)
    downstream_dependencies_count = serializers.SerializerMethodField(read_only=True)
    has_pagerduty_integration = serializers.ReadOnlyField()

    class Meta:
        model = TechnicalService
        fields = [
            'id',
            'name',
            'service_type',
            'devices',
            'vms',
            'clusters',
            'business_apps',
            'business_apps_count',
            'vms_count',
            'devices_count',
            'clusters_count',
            'upstream_dependencies_count',
            'downstream_dependencies_count',
            'pagerduty_service_definition',
            'pagerduty_router_rule',
            'pagerduty_config',
            'has_pagerduty_integration',
            'created',
            'last_updated',
        ]

    def get_upstream_dependencies_count(self, obj):
        return obj.get_upstream_dependencies().count()

    def get_downstream_dependencies_count(self, obj):
        return obj.get_downstream_dependencies().count()

class ServiceDependencySerializer(serializers.ModelSerializer):
    """
    Serializer for the ServiceDependency model.
    """
    upstream_service_name = serializers.CharField(source='upstream_service.name', read_only=True)
    downstream_service_name = serializers.CharField(source='downstream_service.name', read_only=True)

    class Meta:
        model = ServiceDependency
        fields = [
            'id',
            'name',
            'description',
            'upstream_service',
            'upstream_service_name',
            'downstream_service',
            'downstream_service_name',
            'dependency_type',
            'created',
            'last_updated',
        ]

class EventSourceSerializer(serializers.ModelSerializer):
    """
    Serializer for the EventSource model.
    """
    events_count = serializers.IntegerField(source='event_set.count', read_only=True)

    class Meta:
        model = EventSource
        fields = [
            'id',
            'name',
            'description',
            'events_count',
            'created',
            'last_updated',
        ]

class EventSerializer(serializers.ModelSerializer):
    """
    Serializer for the Event model.
    """
    event_source_name = serializers.CharField(source='event_source.name', read_only=True)
    content_type_name = serializers.CharField(source='content_type.model', read_only=True)

    class Meta:
        model = Event
        fields = [
            'id',
            'created_at',
            'last_seen_at',
            'updated_at',
            'content_type',
            'content_type_name',
            'object_id',
            'message',
            'dedup_id',
            'status',
            'criticallity',
            'event_source',
            'event_source_name',
            'raw',
            'created',
            'last_updated',
        ]

class MaintenanceSerializer(serializers.ModelSerializer):
    """
    Serializer for the Maintenance model.
    """
    content_type_name = serializers.CharField(source='content_type.model', read_only=True)

    class Meta:
        model = Maintenance
        fields = [
            'id',
            'status',
            'description',
            'planned_start',
            'planned_end',
            'contact',
            'content_type',
            'content_type_name',
            'object_id',
            'created',
            'last_updated',
        ]

class ChangeTypeSerializer(serializers.ModelSerializer):
    """
    Serializer for the ChangeType model.
    """
    changes_count = serializers.IntegerField(source='change_set.count', read_only=True)

    class Meta:
        model = ChangeType
        fields = [
            'id',
            'name',
            'description',
            'changes_count',
            'created',
            'last_updated',
        ]

class ChangeSerializer(serializers.ModelSerializer):
    """
    Serializer for the Change model.
    """
    type_name = serializers.CharField(source='type.name', read_only=True)
    content_type_name = serializers.CharField(source='content_type.model', read_only=True)

    class Meta:
        model = Change
        fields = [
            'id',
            'type',
            'type_name',
            'created_at',
            'description',
            'content_type',
            'content_type_name',
            'object_id',
            'created',
            'last_updated',
        ]

class IncidentSerializer(serializers.ModelSerializer):
    """
    Serializer for the Incident model.
    """
    responders_count = serializers.IntegerField(source='responders.count', read_only=True)
    affected_services_count = serializers.IntegerField(source='affected_services.count', read_only=True)
    events_count = serializers.IntegerField(source='events.count', read_only=True)

    class Meta:
        model = Incident
        fields = [
            'id',
            'title',
            'description',
            'status',
            'severity',
            'created_at',
            'updated_at',
            'detected_at',
            'resolved_at',
            'responders_count',
            'affected_services_count',
            'events_count',
            'reporter',
            'commander',
            'created',
            'last_updated',
        ]


class PagerDutyTemplateSerializer(serializers.ModelSerializer):
    """
    Serializer for the PagerDutyTemplate model.
    """
    services_using_template = serializers.ReadOnlyField()

    class Meta:
        model = PagerDutyTemplate
        fields = [
            'id',
            'name',
            'description',
            'template_type',
            'pagerduty_config',
            'services_using_template',
            'created',
            'last_updated',
        ]


class TargetSerializer(serializers.Serializer):
    """Serializer for alert target information."""
    type = serializers.ChoiceField(choices=['device', 'vm', 'service'])
    identifier = serializers.CharField(max_length=255)


class GenericAlertSerializer(serializers.Serializer):
    """
    Serializer for generic alert endpoint.
    Validates standardized alert payload format.
    """
    source = serializers.CharField(max_length=100)
    timestamp = serializers.DateTimeField(default=timezone.now)
    severity = serializers.ChoiceField(
        choices=['critical', 'high', 'medium', 'low']
    )
    status = serializers.ChoiceField(
        choices=['triggered', 'ok', 'suppressed']
    )
    message = serializers.CharField()
    dedup_id = serializers.CharField(max_length=255)
    target = TargetSerializer()
    raw_data = serializers.JSONField(required=False, default=dict)

    def validate_dedup_id(self, value):
        """Ensure dedup_id is unique enough."""
        if not value:
            raise serializers.ValidationError(
                "dedup_id cannot be empty"
            )
        return value

    def validate_timestamp(self, value):
        """Ensure timestamp is not in the future."""
        if value > timezone.now():
            raise serializers.ValidationError(
                "Timestamp cannot be in the future"
            )
        return value


class CapacitorAlertSerializer(serializers.Serializer):
    """
    Serializer for Capacitor-specific alerts.
    Based on typical Capacitor alert format.
    """
    alert_id = serializers.CharField()
    device_name = serializers.CharField()
    description = serializers.CharField()
    priority = serializers.IntegerField(min_value=1, max_value=5)
    state = serializers.CharField()
    alert_time = serializers.DateTimeField(required=False)

    # Additional Capacitor-specific fields
    metric_name = serializers.CharField(required=False)
    metric_value = serializers.FloatField(required=False)
    threshold = serializers.FloatField(required=False)

    def validate_state(self, value):
        """Validate Capacitor alert states."""
        valid_states = ['ALARM', 'OK', 'INSUFFICIENT_DATA']
        if value.upper() not in valid_states:
            raise serializers.ValidationError(
                f"State must be one of {valid_states}"
            )
        return value.upper()


class SignalFXAlertSerializer(serializers.Serializer):
    """
    Serializer for SignalFX webhook payload.
    Based on SignalFX Events API v2 format.
    """
    incidentId = serializers.CharField()
    alertState = serializers.CharField()
    alertMessage = serializers.CharField()
    severity = serializers.CharField(required=False, default='medium')
    timestamp = serializers.IntegerField(required=False)  # Unix timestamp

    dimensions = serializers.DictField(required=False, default=dict)
    detectorName = serializers.CharField(required=False)
    detectorUrl = serializers.CharField(required=False)
    rule = serializers.CharField(required=False)

    def validate_alertState(self, value):
        """Validate SignalFX alert states."""
        valid_states = ['TRIGGERED', 'RESOLVED', 'STOPPED']
        if value.upper() not in valid_states:
            raise serializers.ValidationError(
                f"alertState must be one of {valid_states}"
            )
        return value

    def validate_timestamp(self, value):
        """Convert Unix timestamp to datetime if provided."""
        if value:
            try:
                # Fix: Use datetime.timezone.utc instead of timezone.utc
                from datetime import timezone as dt_timezone
                return datetime.fromtimestamp(
                    value / 1000, tz=dt_timezone.utc
                )
            except (ValueError, TypeError):
                raise serializers.ValidationError(
                    "Invalid timestamp format"
                )
        return timezone.now()


class EmailAlertSerializer(serializers.Serializer):
    """
    Serializer for email alerts processed by N8N.
    Expects pre-parsed email content.
    """
    message_id = serializers.CharField(max_length=255)
    subject = serializers.CharField()
    body = serializers.CharField()
    sender = serializers.EmailField()
    timestamp = serializers.DateTimeField(required=False, default=timezone.now)

    # Parsed alert information (extracted by N8N)
    severity = serializers.ChoiceField(
        choices=['critical', 'high', 'medium', 'low'],
        required=False,
        default='medium'
    )
    target_type = serializers.ChoiceField(
        choices=['device', 'vm', 'service'],
        required=False,
        default='service'
    )
    target_identifier = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True
    )

    headers = serializers.DictField(required=False, default=dict)
    attachments = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list
    )

    def validate(self, data):
        """
        Ensure we have enough information to create an alert.
        """
        if not data.get('target_identifier'):
            if 'server' in data['subject'].lower():
                data['target_type'] = 'device'
            elif 'vm' in data['subject'].lower():
                data['target_type'] = 'vm'
            data['target_identifier'] = 'unknown'

        return data

class WebhookSignatureSerializer(serializers.Serializer):
    """
    Base serializer for webhook signature validation.
    Each integration can extend this for specific validation.
    """
    signature = serializers.CharField(required=False)

    def validate_signature(self, request, secret):
        """
        Validate webhook signature.
        Must be implemented by subclasses.
        """
        raise NotImplementedError(
            "Subclasses must implement signature validation"
        )

