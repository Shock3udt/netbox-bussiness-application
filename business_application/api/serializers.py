from rest_framework import serializers
from business_application.models import (
    BusinessApplication, TechnicalService, ServiceDependency, EventSource, Event,
    Maintenance, ChangeType, Change, Incident
)

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

    class Meta:
        model = TechnicalService
        fields = [
            'id',
            'name',
            'service_type',
            'business_apps_count',
            'vms_count',
            'devices_count',
            'clusters_count',
            'upstream_dependencies_count',
            'downstream_dependencies_count',
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