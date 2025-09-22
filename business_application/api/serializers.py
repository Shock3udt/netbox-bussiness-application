from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta

from business_application.models import (
    BusinessApplication, TechnicalService, ServiceDependency, EventSource, Event,
    Maintenance, ChangeType, Change, Incident
)


class BusinessApplicationSerializer(serializers.ModelSerializer):
    """
    Serializer for the BusinessApplication model.
    Provides representation for API interactions.
    """
    # Add incident-related counts for automation insights
    active_incidents_count = serializers.SerializerMethodField(read_only=True)

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
        ]

    def get_active_incidents_count(self, obj):
        """Count of active incidents affecting this business application."""
        return Incident.objects.filter(
            affected_services__business_apps=obj,
            status__in=['new', 'investigating', 'identified']
        ).distinct().count()


class TechnicalServiceSerializer(serializers.ModelSerializer):
    """
    Serializer for the TechnicalService model with automation enhancements.
    """
    business_apps_count = serializers.IntegerField(source='business_apps.count', read_only=True)
    vms_count = serializers.IntegerField(source='vms.count', read_only=True)
    devices_count = serializers.IntegerField(source='devices.count', read_only=True)
    clusters_count = serializers.IntegerField(source='clusters.count', read_only=True)
    upstream_dependencies_count = serializers.SerializerMethodField(read_only=True)
    downstream_dependencies_count = serializers.SerializerMethodField(read_only=True)

    # Enhanced fields for incident automation
    health_status = serializers.CharField(read_only=True)
    active_incidents_count = serializers.SerializerMethodField(read_only=True)
    recent_events_count = serializers.SerializerMethodField(read_only=True)
    dependency_depth = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = TechnicalService
        fields = [
            'id',
            'name',
            'service_type',
            'health_status',
            'business_apps_count',
            'vms_count',
            'devices_count',
            'clusters_count',
            'upstream_dependencies_count',
            'downstream_dependencies_count',
            'active_incidents_count',
            'recent_events_count',
            'dependency_depth',
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

        # Count events from devices and VMs associated with this service
        from django.contrib.contenttypes.models import ContentType
        from dcim.models import Device
        from virtualization.models import VirtualMachine

        device_ct = ContentType.objects.get_for_model(Device)
        vm_ct = ContentType.objects.get_for_model(VirtualMachine)
        service_ct = ContentType.objects.get_for_model(TechnicalService)

        return Event.objects.filter(
            created_at__gte=last_24h
        ).filter(
            models.Q(content_type=service_ct, object_id=obj.id) |
            models.Q(content_type=device_ct, object_id__in=obj.devices.values_list('id', flat=True)) |
            models.Q(content_type=vm_ct, object_id__in=obj.vms.values_list('id', flat=True))
        ).count()

    def get_dependency_depth(self, obj):
        """Calculate the maximum depth of this service in the dependency chain."""
        try:
            # Simple depth calculation - count upstream levels
            visited = set()
            max_depth = 0

            def calculate_depth(service, current_depth=0):
                nonlocal max_depth
                if service.id in visited or current_depth > 10:  # Prevent infinite loops
                    return current_depth

                visited.add(service.id)
                max_depth = max(max_depth, current_depth)

                for dep in service.get_upstream_dependencies():
                    calculate_depth(dep.upstream_service, current_depth + 1)

                return max_depth

            return calculate_depth(obj)
        except Exception:
            return 0


class ServiceDependencySerializer(serializers.ModelSerializer):
    """
    Serializer for the ServiceDependency model with correlation insights.
    """
    upstream_service_name = serializers.CharField(source='upstream_service.name', read_only=True)
    downstream_service_name = serializers.CharField(source='downstream_service.name', read_only=True)
    upstream_service_health = serializers.CharField(source='upstream_service.health_status', read_only=True)
    downstream_service_health = serializers.CharField(source='downstream_service.health_status', read_only=True)
    correlation_strength = serializers.SerializerMethodField(read_only=True)

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
            'correlation_strength',
            'created',
            'last_updated',
        ]

    def get_correlation_strength(self, obj):
        """Calculate how often incidents propagate through this dependency."""
        # Simple correlation metric based on recent incident patterns
        last_30d = timezone.now() - timedelta(days=30)

        upstream_incidents = Incident.objects.filter(
            affected_services=obj.upstream_service,
            created_at__gte=last_30d
        ).count()

        downstream_incidents = Incident.objects.filter(
            affected_services=obj.downstream_service,
            created_at__gte=last_30d
        ).count()

        if upstream_incidents == 0:
            return 0.0

        # Return ratio of downstream incidents that could be related to upstream
        return min(downstream_incidents / upstream_incidents, 1.0)


class EventSourceSerializer(serializers.ModelSerializer):
    """
    Serializer for the EventSource model with automation metrics.
    """
    events_count = serializers.IntegerField(source='event_set.count', read_only=True)
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
        return (events_with_incidents / total_events) * 100


class EventSerializer(serializers.ModelSerializer):
    """
    Enhanced Event serializer with incident correlation information.
    """
    event_source_name = serializers.CharField(source='event_source.name', read_only=True)
    content_type_name = serializers.CharField(source='content_type.model', read_only=True)

    # Enhanced fields for incident automation
    incidents_count = serializers.IntegerField(source='incidents.count', read_only=True)
    incident_ids = serializers.SerializerMethodField(read_only=True)
    correlation_score = serializers.SerializerMethodField(read_only=True)
    affected_services = serializers.SerializerMethodField(read_only=True)
    time_to_incident = serializers.SerializerMethodField(read_only=True)

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
            'incidents_count',
            'incident_ids',
            'correlation_score',
            'affected_services',
            'time_to_incident',
            'raw',
            'created',
            'last_updated',
        ]

    def get_incident_ids(self, obj):
        """List of incident IDs associated with this event."""
        return list(obj.incidents.values_list('id', flat=True))

    def get_correlation_score(self, obj):
        """Best correlation score if this event was correlated with incidents."""
        # This would be calculated during correlation process
        # For now, return a simple metric based on incident association
        if obj.incidents.exists():
            return 0.8  # High correlation if assigned to incident
        return 0.0

    def get_affected_services(self, obj):
        """Services that could be affected by this event."""
        services = []

        try:
            # Get services directly related to the event's object
            if hasattr(obj.obj, 'technical_services'):
                services.extend(obj.obj.technical_services.values('id', 'name'))
            elif hasattr(obj, 'obj') and obj.obj:
                # Check if object is a service itself
                if obj.content_type.model == 'technicalservice':
                    services.append({'id': obj.obj.id, 'name': obj.obj.name})
        except Exception:
            pass

        return services

    def get_time_to_incident(self, obj):
        """Time in minutes from event creation to first incident assignment."""
        first_incident = obj.incidents.order_by('created_at').first()
        if first_incident:
            delta = first_incident.created_at - obj.created_at
            return int(delta.total_seconds() / 60)
        return None


class IncidentSerializer(serializers.ModelSerializer):
    """
    Enhanced Incident serializer with automation and correlation data.
    """
    responders_count = serializers.IntegerField(source='responders.count', read_only=True)
    affected_services_count = serializers.IntegerField(source='affected_services.count', read_only=True)
    events_count = serializers.IntegerField(source='events.count', read_only=True)

    # Enhanced fields for automation insights
    affected_services = serializers.SerializerMethodField(read_only=True)
    event_sources = serializers.SerializerMethodField(read_only=True)
    correlation_window = serializers.SerializerMethodField(read_only=True)
    blast_radius = serializers.SerializerMethodField(read_only=True)
    duration_minutes = serializers.SerializerMethodField(read_only=True)
    auto_created = serializers.SerializerMethodField(read_only=True)

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
            'affected_services',
            'event_sources',
            'correlation_window',
            'blast_radius',
            'duration_minutes',
            'auto_created',
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
                'health_status': service.health_status
            }
            for service in obj.affected_services.all()
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
        """Estimated blast radius based on affected services and their dependencies."""
        affected_services = obj.affected_services.all()

        # Count downstream services that could be impacted
        downstream_count = 0
        business_apps_count = 0

        for service in affected_services:
            downstream_count += service.get_downstream_dependencies().count()
            business_apps_count += service.business_apps.count()

        return {
            'affected_services': affected_services.count(),
            'potential_downstream_services': downstream_count,
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


# Additional serializers for automation endpoints

class AutomationStatusSerializer(serializers.Serializer):
    """Serializer for automation status information."""
    enabled = serializers.BooleanField()
    events_last_24h = serializers.IntegerField()
    incidents_last_24h = serializers.IntegerField()
    unprocessed_events = serializers.IntegerField()
    open_incidents = serializers.IntegerField()
    correlation_threshold = serializers.FloatField()
    correlation_window_minutes = serializers.IntegerField()


class CorrelationAnalysisSerializer(serializers.Serializer):
    """Serializer for correlation analysis data."""
    total_incidents = serializers.IntegerField()
    incidents_by_service_count = serializers.DictField()
    events_per_incident = serializers.DictField()
    correlation_patterns = serializers.ListField()
    unprocessed_events = serializers.IntegerField()
    average_correlation_time = serializers.FloatField()


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