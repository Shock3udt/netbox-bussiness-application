from rest_framework import serializers
from business_application.models import (
    BusinessApplication, TechnicalService, ServiceDependency, EventSource, Event,
    Maintenance, ChangeType, Change, Incident, PagerDutyTemplate
)
from dcim.models import Device
from virtualization.models import VirtualMachine
from django.utils import timezone
from django.db import models
from django.db.models import Q
from datetime import datetime, timedelta


class BusinessApplicationSerializer(serializers.ModelSerializer):
    """
    Serializer for the BusinessApplication model.
    Provides representation for API interactions.
    """
    # Enhanced: Add incident-related counts for automation insights
    active_incidents_count = serializers.SerializerMethodField(read_only=True)
    recent_events_count = serializers.SerializerMethodField(read_only=True)

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
            'active_incidents_count',
            'recent_events_count',
        ]

    def get_active_incidents_count(self, obj):
        """Count of active incidents affecting this business application."""
        return Incident.objects.filter(
            affected_services__business_apps=obj,
            status__in=['new', 'investigating', 'identified']
        ).distinct().count()

    def get_recent_events_count(self, obj):
        """Count of recent events (last 24h) affecting this business application."""
        last_24h = timezone.now() - timedelta(hours=24)
        from django.contrib.contenttypes.models import ContentType

        # Count events from devices and VMs associated with this business app
        device_ct = ContentType.objects.get_for_model(Device)
        vm_ct = ContentType.objects.get_for_model(VirtualMachine)

        return Event.objects.filter(
            created_at__gte=last_24h
        ).filter(
            models.Q(content_type=device_ct, object_id__in=obj.devices.values_list('id', flat=True)) |
            models.Q(content_type=vm_ct, object_id__in=obj.virtual_machines.values_list('id', flat=True))
        ).count()


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

    # Enhanced: Add incident automation fields
    health_status = serializers.CharField(read_only=True)
    active_incidents_count = serializers.SerializerMethodField(read_only=True)
    recent_events_count = serializers.SerializerMethodField(read_only=True)
    blast_radius_estimate = serializers.SerializerMethodField(read_only=True)

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
            'health_status',
            'active_incidents_count',
            'recent_events_count',
            'blast_radius_estimate',
            'created',
            'last_updated',
        ]

    def get_upstream_dependencies_count(self, obj):
        return obj.get_upstream_dependencies().count()

    def get_downstream_dependencies_count(self, obj):
        return obj.get_downstream_dependencies().count()

    def get_active_incidents_count(self, obj):
        """Count of active incidents affecting this service."""
        return obj.incidents.filter(
            status__in=['new', 'investigating', 'identified']
        ).count()

    def get_recent_events_count(self, obj):
        """Count of recent events (last 24h) for this service's infrastructure."""
        last_24h = timezone.now() - timedelta(hours=24)
        from django.contrib.contenttypes.models import ContentType

        service_ct = ContentType.objects.get_for_model(TechnicalService)
        device_ct = ContentType.objects.get_for_model(Device)
        vm_ct = ContentType.objects.get_for_model(VirtualMachine)

        service_events = Event.objects.filter(
            created_at__gte=last_24h,
            content_type=service_ct,
            object_id=obj.id
        ).count()
        
        device_events = Event.objects.filter(
            created_at__gte=last_24h,
            content_type=device_ct,
            object_id__in=obj.devices.values_list('id', flat=True)
        ).count()
        
        vm_events = Event.objects.filter(
            created_at__gte=last_24h,
            content_type=vm_ct,
            object_id__in=obj.vms.values_list('id', flat=True)
        ).count()
        
        return service_events + device_events + vm_events

    def get_blast_radius_estimate(self, obj):
        """Estimate potential blast radius for incidents affecting this service."""
        downstream_services = obj.get_downstream_dependencies().count()
        business_apps = obj.business_apps.count()

        return {
            'downstream_services': downstream_services,
            'business_applications': business_apps,
            'total_devices_vms': obj.devices.count() + obj.vms.count()
        }


class ServiceDependencySerializer(serializers.ModelSerializer):
    """
    Serializer for the ServiceDependency model.
    """
    upstream_service_name = serializers.CharField(source='upstream_service.name', read_only=True)
    downstream_service_name = serializers.CharField(source='downstream_service.name', read_only=True)

    # Enhanced: Add health status and correlation metrics
    upstream_service_health = serializers.CharField(source='upstream_service.health_status', read_only=True)
    downstream_service_health = serializers.CharField(source='downstream_service.health_status', read_only=True)
    incident_correlation_strength = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ServiceDependency
        fields = [
            'id',
            'name',
            'description',
            'upstream_service',
            'upstream_service_name',
            'upstream_service_health',
            'downstream_service',
            'downstream_service_name',
            'downstream_service_health',
            'dependency_type',
            'incident_correlation_strength',
            'created',
            'last_updated',
        ]

    def get_incident_correlation_strength(self, obj):
        """Calculate how often incidents propagate through this dependency."""
        last_30d = timezone.now() - timedelta(days=30)

        upstream_incidents = Incident.objects.filter(
            affected_services=obj.upstream_service,
            created_at__gte=last_30d
        ).count()

        if upstream_incidents == 0:
            return 0.0

        # Count incidents that affected both services within correlation window
        correlated_incidents = 0
        for incident in Incident.objects.filter(
                affected_services=obj.upstream_service,
                created_at__gte=last_30d
        ):
            # Check if downstream service was also affected within 30 minutes
            correlation_window = incident.created_at + timedelta(minutes=30)
            if Incident.objects.filter(
                    affected_services=obj.downstream_service,
                    created_at__gte=incident.created_at,
                    created_at__lte=correlation_window
            ).exists():
                correlated_incidents += 1

        return (correlated_incidents / upstream_incidents) * 100


class EventSourceSerializer(serializers.ModelSerializer):
    """
    Serializer for the EventSource model.
    """
    events_count = serializers.IntegerField(source='event_set.count', read_only=True)

    # Enhanced: Add automation metrics
    recent_events_count = serializers.SerializerMethodField(read_only=True)
    incident_creation_rate = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = EventSource
        fields = [
            'id',
            'name',
            'description',
            'events_count',
            'recent_events_count',
            'incident_creation_rate',
            'created',
            'last_updated',
        ]

    def get_recent_events_count(self, obj):
        """Count of events from this source in the last 24 hours."""
        last_24h = timezone.now() - timedelta(hours=24)
        return obj.event_set.filter(created_at__gte=last_24h).count()

    def get_incident_creation_rate(self, obj):
        """Percentage of events from this source that create incidents."""
        total_events = obj.event_set.count()
        if total_events == 0:
            return 0.0

        events_with_incidents = obj.event_set.filter(incidents__isnull=False).distinct().count()
        return round((events_with_incidents / total_events) * 100, 2)


class EventSerializer(serializers.ModelSerializer):
    """
    Serializer for the Event model.
    """
    event_source_name = serializers.CharField(source='event_source.name', read_only=True)
    content_type_name = serializers.CharField(source='content_type.model', read_only=True)
    has_valid_target = serializers.ReadOnlyField()
    target_display = serializers.ReadOnlyField()

    # Enhanced: Add incident automation fields
    incidents_count = serializers.IntegerField(source='incidents.count', read_only=True)
    incident_ids = serializers.SerializerMethodField(read_only=True)
    time_to_incident = serializers.SerializerMethodField(read_only=True)
    correlation_score = serializers.SerializerMethodField(read_only=True)

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
            'is_valid',
            'has_valid_target',
            'target_display',
            'incidents_count',
            'incident_ids',
            'time_to_incident',
            'correlation_score',
            'created',
            'last_updated',
        ]

    def get_incident_ids(self, obj):
        """List of incident IDs associated with this event."""
        return list(obj.incidents.values_list('id', flat=True))

    def get_time_to_incident(self, obj):
        """Time in minutes from event creation to first incident assignment."""
        first_incident = obj.incidents.order_by('created_at').first()
        if first_incident:
            delta = first_incident.created_at - obj.created_at
            return int(delta.total_seconds() / 60)
        return None

    def get_correlation_score(self, obj):
        """Basic correlation score based on incident association."""
        if obj.incidents.exists():
            # Higher score if event was quickly correlated
            time_to_incident = self.get_time_to_incident(obj)
            if time_to_incident is not None and time_to_incident <= 5:
                return 0.9  # Very high correlation
            elif time_to_incident is not None and time_to_incident <= 15:
                return 0.7  # Good correlation
            else:
                return 0.5  # Moderate correlation
        return 0.0


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
    affected_devices_count = serializers.IntegerField(source='affected_devices.count', read_only=True)
    events_count = serializers.IntegerField(source='events.count', read_only=True)

    # Enhanced: Add automation insights
    affected_services = serializers.SerializerMethodField(read_only=True)
    affected_devices = serializers.SerializerMethodField(read_only=True)
    event_sources = serializers.SerializerMethodField(read_only=True)
    correlation_window = serializers.SerializerMethodField(read_only=True)
    blast_radius = serializers.SerializerMethodField(read_only=True)
    duration_minutes = serializers.SerializerMethodField(read_only=True)
    auto_created = serializers.SerializerMethodField(read_only=True)
    device_discovery_metadata = serializers.SerializerMethodField(read_only=True)

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
            'affected_devices_count',
            'events_count',
            'affected_services',
            'affected_devices',
            'event_sources',
            'correlation_window',
            'blast_radius',
            'duration_minutes',
            'auto_created',
            'device_discovery_metadata',
            'reporter',
            'commander',
            'created',
            'last_updated',
        ]

    def get_affected_services(self, obj):
        """Detailed information about affected services."""
        return [
            {
                'id': service.id,
                'name': service.name,
                'service_type': service.service_type,
                'health_status': getattr(service, 'health_status', 'unknown')
            }
            for service in obj.affected_services.all()
        ]

    def get_affected_devices(self, obj):
        """Detailed information about affected devices."""
        return [
            {
                'id': device.id,
                'name': device.name,
                'device_type': str(device.device_type) if device.device_type else 'unknown',
                'status': device.status if hasattr(device, 'status') else 'unknown',
                'site': device.site.name if device.site else None,
                'rack': device.rack.name if device.rack else None
            }
            for device in obj.affected_devices.all()
        ]

    def get_event_sources(self, obj):
        """Unique event sources that contributed to this incident."""
        sources = obj.events.filter(event_source__isnull=False).values_list(
            'event_source__name', flat=True
        ).distinct()
        return list(sources)

    def get_correlation_window(self, obj):
        """Time window over which events were correlated into this incident."""
        if obj.events.count() <= 1:
            return 0

        first_event = obj.events.order_by('created_at').first()
        last_event = obj.events.order_by('-created_at').first()

        if first_event and last_event:
            delta = last_event.created_at - first_event.created_at
            return int(delta.total_seconds() / 60)  # minutes
        return 0

    def get_blast_radius(self, obj):
        """Estimated blast radius based on affected services, devices and their dependencies."""
        affected_services = obj.affected_services.all()
        affected_devices = obj.affected_devices.all()

        downstream_count = 0
        business_apps_count = 0
        connected_devices_count = 0

        for service in affected_services:
            downstream_count += service.get_downstream_dependencies().count()
            business_apps_count += service.business_apps.count()

        # Estimate connected devices via cable connections
        try:
            from business_application.utils.correlation import AlertCorrelationEngine
            correlation_engine = AlertCorrelationEngine()
            
            for device in affected_devices:
                try:
                    if hasattr(correlation_engine, '_find_devices_via_cables'):
                        connected_devices = getattr(correlation_engine, '_find_devices_via_cables')(device)
                        connected_devices_count += len(connected_devices)
                except Exception:
                    pass  # Ignore errors in blast radius calculation
        except ImportError:
            # Handle circular import gracefully
            pass

        return {
            'affected_services': affected_services.count(),
            'affected_devices': affected_devices.count(),
            'potential_downstream_services': downstream_count,
            'potential_connected_devices': connected_devices_count,
            'affected_business_applications': business_apps_count
        }

    def get_duration_minutes(self, obj):
        """Duration of the incident in minutes."""
        end_time = obj.resolved_at or timezone.now()
        start_time = obj.detected_at or obj.created_at

        delta = end_time - start_time
        return int(delta.total_seconds() / 60)

    def get_auto_created(self, obj):
        """Whether this incident was automatically created."""
        return obj.reporter == "Auto-Incident System"

    def get_device_discovery_metadata(self, obj):
        """Metadata about how devices were discovered as affected."""
        affected_devices = obj.affected_devices.all()
        
        if not affected_devices:
            return {
                'total_devices': 0,
                'discovery_methods': []
            }

        # For each device, determine how it was likely discovered
        discovery_methods = []
        service_based_count = 0
        cable_based_count = 0

        for device in affected_devices:
            # Check if device is associated with any affected services (service-based discovery)
            device_services = device.technical_services.all()
            affected_services = obj.affected_services.all()
            
            if any(service in affected_services for service in device_services):
                service_based_count += 1
                discovery_methods.append('service-based')
            else:
                # Likely discovered via cable connections
                cable_based_count += 1
                discovery_methods.append('cable-based')

        return {
            'total_devices': len(affected_devices),
            'service_based_devices': service_based_count,
            'cable_based_devices': cable_based_count,
            'discovery_methods': list(set(discovery_methods))  # Unique methods
        }


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


class GitLabSerializer(serializers.Serializer):
    """
    Serializer for GitLab webhook payload.
    Based on GitLab  Events webhook format.
    """
    object_kind = serializers.CharField()
    object_attributes = serializers.DictField()
    project = serializers.DictField()
    commit = serializers.DictField(required=False)
    user = serializers.DictField(required=False)

    def validate_object_kind(self, value):
        """Validate that this is a pipeline or merge request event."""
        if value not in ['pipeline', 'merge_request']:
            raise serializers.ValidationError(
                "This endpoint only accepts pipeline or merge request events"
            )
        return value
    
    # Validate the entire payload, as object_attributes can be different for pipeline and merge request events.
    # We cannot use validate_object_attributes because it does not have access to the object_kind.
    def validate(self, attrs):
        """Validate the entire payload."""
        if attrs['object_kind'] == 'pipeline':
            required_fields = ['id', 'status', 'source']
        elif attrs['object_kind'] == 'merge_request':
            required_fields = ['id', 'state', 'source']
        else:
            raise serializers.ValidationError(
                "Invalid object kind: " + attrs['object_kind']
            )
        for field in required_fields:
            if field not in attrs['object_attributes']:
                raise serializers.ValidationError(
                    f"Missing required field in object_attributes: {field}"
                )
        return attrs

    def validate_project(self, value):
        """Validate project contains required fields."""
        if 'path_with_namespace' not in value:
            raise serializers.ValidationError(
                "Missing required field in project: path_with_namespace"
            )
        return value


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


# ============================================================================
# NEW SERIALIZERS FOR INCIDENT AUTOMATION
# ============================================================================

class AutomationStatusSerializer(serializers.Serializer):
    """Serializer for automation status information."""
    enabled = serializers.BooleanField()
    events_last_24h = serializers.IntegerField()
    incidents_last_24h = serializers.IntegerField()
    unprocessed_events = serializers.IntegerField()
    open_incidents = serializers.IntegerField()
    correlation_threshold = serializers.FloatField()
    correlation_window_minutes = serializers.IntegerField()
    recent_incident_trend = serializers.DictField()


class CorrelationAnalysisSerializer(serializers.Serializer):
    """Serializer for correlation analysis data."""
    total_incidents = serializers.IntegerField()
    incidents_by_service_count = serializers.DictField()
    events_per_incident = serializers.DictField()
    correlation_patterns = serializers.ListField()
    unprocessed_events = serializers.IntegerField()


class ProcessEventRequestSerializer(serializers.Serializer):
    """Serializer for event processing requests."""
    event_id = serializers.IntegerField()


class ProcessEventResponseSerializer(serializers.Serializer):
    """Serializer for event processing responses."""
    success = serializers.BooleanField()
    message = serializers.CharField()
    incident_id = serializers.IntegerField(allow_null=True)
    incident_title = serializers.CharField(allow_null=True)
    action = serializers.CharField()  # 'created', 'updated', 'none'


class ProcessUnprocessedRequestSerializer(serializers.Serializer):
    """Serializer for batch processing requests."""
    hours = serializers.IntegerField(default=24, min_value=1, max_value=168)


class ProcessUnprocessedResponseSerializer(serializers.Serializer):
    """Serializer for batch processing responses."""
    success = serializers.BooleanField()
    message = serializers.CharField()
    unprocessed_events_found = serializers.IntegerField()
    events_processed = serializers.IntegerField()
    time_window_hours = serializers.IntegerField()


class ForceCorrelateRequestSerializer(serializers.Serializer):
    """Serializer for force correlation requests."""
    hours = serializers.IntegerField(default=24, min_value=1, max_value=168)
    incident_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list
    )


class ForceCorrelateResponseSerializer(serializers.Serializer):
    """Serializer for force correlation responses."""
    success = serializers.BooleanField()
    message = serializers.CharField()
    total_events_reprocessed = serializers.IntegerField()
    events_successfully_processed = serializers.IntegerField()
    time_window_hours = serializers.IntegerField()


class IncidentAutomationEventSerializer(serializers.ModelSerializer):
    """
    Simplified event serializer for automation endpoints.
    Focuses on correlation-relevant data.
    """
    content_type_name = serializers.CharField(source='content_type.model', read_only=True)
    event_source_name = serializers.CharField(source='event_source.name', read_only=True)
    incidents_count = serializers.IntegerField(source='incidents.count', read_only=True)

    class Meta:
        model = Event
        fields = [
            'id',
            'message',
            'status',
            'criticallity',
            'created_at',
            'content_type_name',
            'object_id',
            'event_source_name',
            'incidents_count',
            'dedup_id'
        ]


class IncidentAutomationIncidentSerializer(serializers.ModelSerializer):
    """
    Simplified incident serializer for automation endpoints.
    Focuses on correlation and automation data.
    """
    events_count = serializers.IntegerField(source='events.count', read_only=True)
    affected_services_count = serializers.IntegerField(source='affected_services.count', read_only=True)
    auto_created = serializers.SerializerMethodField()
    correlation_window = serializers.SerializerMethodField()

    class Meta:
        model = Incident
        fields = [
            'id',
            'title',
            'status',
            'severity',
            'created_at',
            'resolved_at',
            'events_count',
            'affected_services_count',
            'auto_created',
            'correlation_window',
            'reporter'
        ]

    def get_auto_created(self, obj):
        return obj.reporter == "Auto-Incident System"

    def get_correlation_window(self, obj):
        """Time window over which events were correlated (in minutes)."""
        if obj.events.count() <= 1:
            return 0

        first_event = obj.events.order_by('created_at').first()
        last_event = obj.events.order_by('-created_at').first()

        if first_event and last_event:
            delta = last_event.created_at - first_event.created_at
            return int(delta.total_seconds() / 60)
        return 0
