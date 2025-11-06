from pydoc import text
from django import forms
import json
from .models import (
    BusinessApplication, TechnicalService, ServiceDependency, EventSource, Event,
    Maintenance, ChangeType, Change, Incident, PagerDutyTemplate, PagerDutyTemplateTypeChoices
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
            'business_apps',
            'pagerduty_service_definition',
            'pagerduty_router_rule',
            'pagerduty_routing_key'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Filter PagerDuty templates by type
        self.fields['pagerduty_service_definition'].queryset = PagerDutyTemplate.objects.filter(
            template_type=PagerDutyTemplateTypeChoices.SERVICE_DEFINITION,
        )
        self.fields['pagerduty_router_rule'].queryset = PagerDutyTemplate.objects.filter(
            template_type=PagerDutyTemplateTypeChoices.ROUTER_RULE,
        )

        self.fields['pagerduty_routing_key'].widget = forms.PasswordInput(attrs={
            'placeholder': 'Enter PagerDuty routing key'
        })
        self.fields['pagerduty_routing_key'].help_text = 'PagerDuty routing key for this service'

class PagerDutyTemplateForm(forms.ModelForm):
    """
    Form for creating and editing PagerDutyTemplate objects.
    """
    pagerduty_config = forms.JSONField(
        help_text='PagerDuty service configuration in JSON format',
        widget=forms.Textarea(attrs={
            'rows': 15,
            'placeholder': '''{
  "name": "Service Name",
  "description": "Service Description",
  "auto_resolve_timeout": 0,
  "acknowledgement_timeout": 0,
  "status": "active",
  "escalation_policy": {
    "id": "ABCDEFG",
    "type": "escalation_policy_reference"
  },
  "incident_urgency_rule": {
    "type": "constant",
    "urgency": "high"
  },
  "support_hours": null,
  "scheduled_actions": [],
  "alert_grouping_parameters": {
    "type": "content_based",
    "config": {
      "fields": [
        "class",
        "custom_details.result.series.0.tags.site"
      ],
      "aggregate": "all",
      "time_window": 600,
      "recommended_time_window": 1677
    }
  }
}'''
        })
    )

    class Meta:
        model = PagerDutyTemplate
        fields = ['name', 'description', 'template_type', 'pagerduty_config']

    def clean_pagerduty_config(self):
        """Custom validation for PagerDuty configuration"""
        data = self.cleaned_data.get('pagerduty_config')
        if data:
            # Validate the JSON structure using the model's validation method
            temp_template = PagerDutyTemplate(pagerduty_config=data)
            is_valid, errors = temp_template.validate_pagerduty_config()
            if not is_valid:
                raise forms.ValidationError(f"Invalid PagerDuty configuration: {'; '.join(errors)}")
        return data


class TechnicalServicePagerDutyForm(forms.ModelForm):
    """
    Form for selecting PagerDuty templates for TechnicalService objects.
    """
    class Meta:
        model = TechnicalService
        fields = ['pagerduty_service_definition', 'pagerduty_router_rule', 'pagerduty_routing_key']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Filter templates by type and active status
        self.fields['pagerduty_service_definition'].queryset = PagerDutyTemplate.objects.filter(
            template_type=PagerDutyTemplateTypeChoices.SERVICE_DEFINITION,
        )
        self.fields['pagerduty_router_rule'].queryset = PagerDutyTemplate.objects.filter(
            template_type=PagerDutyTemplateTypeChoices.ROUTER_RULE,
        )

        self.fields['pagerduty_routing_key'].widget = forms.PasswordInput(attrs={
            'placeholder': 'Enter PagerDuty routing key'
        })
        self.fields['pagerduty_routing_key'].help_text = 'PagerDuty routing key for this service'


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
            'commander',
            'pagerduty_dedup_key'
        ]
        widgets = {
            'detected_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'resolved_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'rows': 4}),
            'pagerduty_dedup_key': forms.TextInput(attrs={
                'readonly': True,
                'placeholder': 'Automatically populated when PagerDuty incident is created'
            }),
        }

