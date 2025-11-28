# Generated migration for ExternalWorkflow model

from django.db import migrations, models
import django.db.models.deletion
import utilities.json


class Migration(migrations.Migration):

    dependencies = [
        ('business_application', '0007_add_event_validity'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExternalWorkflow',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('last_updated', models.DateTimeField(auto_now=True, null=True)),
                ('custom_field_data', models.JSONField(blank=True, default=dict, encoder=utilities.json.CustomFieldJSONEncoder)),
                ('name', models.CharField(help_text='Unique name for this workflow configuration', max_length=100, unique=True)),
                ('description', models.TextField(blank=True, help_text='Description of what this workflow does')),
                ('workflow_type', models.CharField(
                    choices=[('aap', 'Ansible Automation Platform'), ('n8n', 'N8N')],
                    help_text='External workflow platform type',
                    max_length=20
                )),
                ('enabled', models.BooleanField(default=True, help_text='Whether this workflow is enabled for execution')),
                ('aap_url', models.URLField(blank=True, help_text='AAP Controller URL (e.g., https://aap.example.com)', null=True)),
                ('aap_resource_type', models.CharField(
                    blank=True,
                    choices=[('workflow', 'Workflow Template'), ('job_template', 'Job Template')],
                    help_text='AAP resource type (Workflow Template or Job Template)',
                    max_length=20,
                    null=True
                )),
                ('aap_resource_id', models.PositiveIntegerField(blank=True, help_text='AAP Workflow or Job Template ID', null=True)),
                ('n8n_webhook_url', models.URLField(blank=True, help_text='N8N Webhook URL for triggering the workflow', null=True)),
                ('object_type', models.CharField(
                    choices=[('device', 'Device'), ('incident', 'Incident'), ('event', 'Event')],
                    help_text='Type of object that triggers this workflow',
                    max_length=20
                )),
                ('attribute_mapping', models.JSONField(
                    blank=True,
                    default=dict,
                    help_text='JSON mapping of object attributes to workflow parameters.\n        For AAP: {"extra_vars": {"var_name": "object.field"}, "limit": "object.name"}\n        For N8N: {"field_name": "object.field", "another_field": "object.other_field"}'
                )),
            ],
            options={
                'verbose_name': 'External Workflow',
                'verbose_name_plural': 'External Workflows',
                'ordering': ['name'],
            },
        ),
    ]

