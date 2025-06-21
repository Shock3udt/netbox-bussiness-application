from django import forms
from .models import (
    BusinessApplication, TechnicalService, EventSource, Event,
    Maintenance, ChangeType, Change
)

class BusinessApplicationForm(forms.ModelForm):
    """
    Form for creating and editing BusinessApplication objects.
    """
    class Meta:
        model = BusinessApplication
        fields = [
            'name',
            'appcode',
            'description',
            'owner',
            'delegate',
            'servicenow',
            'virtual_machines',
            'devices'
        ]

class TechnicalServiceForm(forms.ModelForm):
    """
    Form for creating and editing TechnicalService objects.
    """
    class Meta:
        model = TechnicalService
        fields = [
            'name',
            'parent',
            'business_apps',
            'vms',
            'devices',
            'clusters'
        ]

class EventSourceForm(forms.ModelForm):
    """
    Form for creating and editing EventSource objects.
    """
    class Meta:
        model = EventSource
        fields = [
            'name',
            'description'
        ]

class EventForm(forms.ModelForm):
    """
    Form for creating and editing Event objects.
    """
    class Meta:
        model = Event
        fields = [
            'last_seen_at',
            'content_type',
            'object_id',
            'message',
            'dedup_id',
            'status',
            'criticallity',
            'event_source',
            'raw'
        ]

class MaintenanceForm(forms.ModelForm):
    """
    Form for creating and editing Maintenance objects.
    """
    class Meta:
        model = Maintenance
        fields = [
            'status',
            'description',
            'planned_start',
            'planned_end',
            'contact',
            'content_type',
            'object_id'
        ]

class ChangeTypeForm(forms.ModelForm):
    """
    Form for creating and editing ChangeType objects.
    """
    class Meta:
        model = ChangeType
        fields = [
            'name',
            'description'
        ]

class ChangeForm(forms.ModelForm):
    """
    Form for creating and editing Change objects.
    """
    class Meta:
        model = Change
        fields = [
            'type',
            'description',
            'content_type',
            'object_id'
        ]
