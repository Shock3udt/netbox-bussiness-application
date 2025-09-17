from django import forms
from .models import (
    BusinessApplication, TechnicalService, ServiceDependency, EventSource, Event,
    Maintenance, ChangeType, Change, Incident
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
            'service_type',
            'business_apps'
        ]

class ServiceDependencyForm(forms.ModelForm):
    """
    Form for creating and editing ServiceDependency objects.
    """
    class Meta:
        model = ServiceDependency
        fields = [
            'name',
            'description',
            'upstream_service',
            'downstream_service',
            'dependency_type'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add help text for dependency types
        self.fields['dependency_type'].help_text = (
            "Normal: Incident occurs if ANY upstream service fails. "
            "Redundancy: Incident occurs only if ALL upstream services fail."
        )

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

class IncidentForm(forms.ModelForm):
    """
    Form for creating and editing Incident objects.
    """
    class Meta:
        model = Incident
        fields = [
            'title',
            'description',
            'status',
            'severity',
            'detected_at',
            'resolved_at',
            'responders',
            'affected_services',
            'events',
            'reporter',
            'commander'
        ]
        widgets = {
            'detected_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'resolved_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'rows': 4}),
        }
