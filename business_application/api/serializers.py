from rest_framework import serializers
from business_application.models import (
    BusinessApplication, TechnicalService, EventSource, Event,
    Maintenance, ChangeType, Change
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
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    business_apps_count = serializers.IntegerField(source='business_apps.count', read_only=True)
    vms_count = serializers.IntegerField(source='vms.count', read_only=True)
    devices_count = serializers.IntegerField(source='devices.count', read_only=True)
    clusters_count = serializers.IntegerField(source='clusters.count', read_only=True)

    class Meta:
        model = TechnicalService
        fields = [
            'id',
            'name',
            'parent',
            'parent_name',
            'business_apps_count',
            'vms_count',
            'devices_count',
            'clusters_count',
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