# business_application/forms.py
"""
Forms for Business Application plugin.
Updated with PagerDuty routing key support (sensitive field).
"""

from django import forms
from .models import (
    BusinessApplication, TechnicalService, ServiceDependency, EventSource, Event,
    Maintenance, ChangeType, Change, Incident, PagerDutyTemplate, PagerDutyTemplateTypeChoices,
    ExternalWorkflow, ExternalWorkflowType
)


class SensitiveCharField(forms.CharField):
    """
    A CharField that renders as a password input for sensitive values.
    Shows placeholder text if a value already exists.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', forms.PasswordInput(attrs={
            'class': 'form-control',
            'autocomplete': 'off',
            'placeholder': '••••••••••••••••'
        }))
        kwargs.setdefault('required', False)
        super().__init__(*args, **kwargs)


class BusinessApplicationForm(forms.ModelForm):
    """
    Form for creating and editing BusinessApplication objects.
    """
    pagerduty_routing_key = SensitiveCharField(
        label='PagerDuty Routing Key',
        help_text='PagerDuty Events API v2 routing key (integration key). '
                  'Leave empty to clear, or enter new value to update. '
                  'Used as fallback if no TechnicalService has a routing key.',
        required=False,
    )

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
            'devices',
            'pagerduty_routing_key',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If editing existing object with routing key, show placeholder
        if self.instance and self.instance.pk and self.instance.pagerduty_routing_key:
            self.fields['pagerduty_routing_key'].widget.attrs[
                'placeholder'] = '••••••• (value set - enter new value to change)'
            self.fields['pagerduty_routing_key'].help_text += ' Current value is hidden for security.'

    def clean_pagerduty_routing_key(self):
        """Handle the sensitive routing key field."""
        new_value = self.cleaned_data.get('pagerduty_routing_key')

        # If empty and we're editing, keep the old value
        if not new_value and self.instance and self.instance.pk:
            return self.instance.pagerduty_routing_key

        return new_value if new_value else None


class TechnicalServiceForm(forms.ModelForm):
    """
    Form for creating and editing TechnicalService objects.
    """
    pagerduty_routing_key = SensitiveCharField(
        label='PagerDuty Routing Key',
        help_text='PagerDuty Events API v2 routing key (integration key). '
                  'Leave empty to clear, or enter new value to update. '
                  'If not set, will search upstream (parent) services for a routing key.',
        required=False,
    )

    class Meta:
        model = TechnicalService
        fields = [
            'name',
            'service_type',
            'business_apps',
            'pagerduty_service_definition',
            'pagerduty_router_rule',
            'pagerduty_routing_key',
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

        # If editing existing object with routing key, show placeholder
        if self.instance and self.instance.pk and self.instance.pagerduty_routing_key:
            self.fields['pagerduty_routing_key'].widget.attrs[
                'placeholder'] = '••••••• (value set - enter new value to change)'
            self.fields['pagerduty_routing_key'].help_text += ' Current value is hidden for security.'

    def clean_pagerduty_routing_key(self):
        """Handle the sensitive routing key field."""
        new_value = self.cleaned_data.get('pagerduty_routing_key')

        # If empty and we're editing, keep the old value
        if not new_value and self.instance and self.instance.pk:
            return self.instance.pagerduty_routing_key

        return new_value if new_value else None


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
    Form for selecting PagerDuty templates and routing key for TechnicalService objects.
    """
    pagerduty_routing_key = SensitiveCharField(
        label='PagerDuty Routing Key',
        help_text='PagerDuty Events API v2 routing key (integration key). '
                  'Leave empty to inherit from upstream services or BusinessApplication.',
        required=False,
    )

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

        # If editing existing object with routing key, show placeholder
        if self.instance and self.instance.pk and self.instance.pagerduty_routing_key:
            self.fields['pagerduty_routing_key'].widget.attrs[
                'placeholder'] = '••••••• (value set - enter new value to change)'

    def clean_pagerduty_routing_key(self):
        """Handle the sensitive routing key field."""
        new_value = self.cleaned_data.get('pagerduty_routing_key')

        # If empty and we're editing, keep the old value
        if not new_value and self.instance and self.instance.pk:
            return self.instance.pagerduty_routing_key

        return new_value if new_value else None


class TechnicalServiceAssignDevicesForm(forms.ModelForm):
    """
    Form for assigning existing devices to a TechnicalService.
    """
    class Meta:
        model = TechnicalService
        fields = ['devices']


class TechnicalServiceAssignVMsForm(forms.ModelForm):
    """
    Form for assigning existing virtual machines to a TechnicalService.
    """
    class Meta:
        model = TechnicalService
        fields = ['vms']


class TechnicalServiceAssignClustersForm(forms.ModelForm):
    """
    Form for assigning existing clusters to a TechnicalService.
    """
    class Meta:
        model = TechnicalService
        fields = ['clusters']


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
    # Optional: Add checkbox for testing PagerDuty integration
    create_pagerduty_incident = forms.BooleanField(
        required=False,
        initial=False,
        label='Create PagerDuty Incident',
        help_text='For testing: Create a corresponding incident in PagerDuty'
    )

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

    def save(self, commit=True):
        """Override save to add PagerDuty integration for testing."""
        # Check if this is a new incident (before saving)
        is_new_incident = self.instance.pk is None

        # Save the incident first
        incident = super().save(commit=commit)

        # If this is a new incident and user checked the PagerDuty checkbox
        if commit and is_new_incident and self.cleaned_data.get('create_pagerduty_incident'):
            # Import here to avoid circular imports
            from .utils.pagerduty_integration import create_pagerduty_incident
            import logging

            logger = logging.getLogger('business_application.forms')
            try:
                logger.info(f"Form-based PagerDuty creation requested for incident {incident.id}")
                create_pagerduty_incident(incident)
            except Exception as e:
                logger.exception(f"Error creating PagerDuty incident from form: {str(e)}")
                # Don't fail the form submission if PagerDuty fails
                pass

        return incident

class ExternalWorkflowForm(forms.ModelForm):
    """
    Form for creating and editing ExternalWorkflow objects.
    """
    attribute_mapping = forms.JSONField(
        required=False,
        help_text='JSON mapping of object attributes to workflow parameters',
        widget=forms.Textarea(attrs={
            'rows': 10,
            'placeholder': '''{
  "extra_vars": {
    "device_name": "object.name",
    "device_ip": "object.primary_ip4.address",
    "severity": "object.severity"
  },
  "limit": "object.name"
}'''
        })
    )

    class Meta:
        model = ExternalWorkflow
        fields = [
            'name',
            'description',
            'workflow_type',
            'enabled',
            'object_type',
            'aap_url',
            'aap_resource_type',
            'aap_resource_id',
            'n8n_webhook_url',
            'attribute_mapping',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add help text for conditional fields
        self.fields['aap_url'].widget.attrs['placeholder'] = 'https://aap.example.com'
        self.fields['n8n_webhook_url'].widget.attrs['placeholder'] = 'https://n8n.example.com/webhook/abc123'

    def clean(self):
        cleaned_data = super().clean()
        workflow_type = cleaned_data.get('workflow_type')

        # Validate AAP-specific fields
        if workflow_type == ExternalWorkflowType.AAP:
            if not cleaned_data.get('aap_url'):
                self.add_error('aap_url', 'AAP URL is required for AAP workflow type')
            if not cleaned_data.get('aap_resource_type'):
                self.add_error('aap_resource_type', 'AAP resource type is required for AAP workflow type')
            if not cleaned_data.get('aap_resource_id'):
                self.add_error('aap_resource_id', 'AAP resource ID is required for AAP workflow type')

        # Validate N8N-specific fields
        elif workflow_type == ExternalWorkflowType.N8N:
            if not cleaned_data.get('n8n_webhook_url'):
                self.add_error('n8n_webhook_url', 'N8N webhook URL is required for N8N workflow type')

        return cleaned_data
