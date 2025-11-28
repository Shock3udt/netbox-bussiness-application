# Generated migration for WorkflowExecution model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import utilities.json


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('contenttypes', '0002_remove_content_type_name'),
        ('business_application', '0008_add_external_workflow'),
    ]

    operations = [
        migrations.CreateModel(
            name='WorkflowExecution',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('last_updated', models.DateTimeField(auto_now=True, null=True)),
                ('custom_field_data', models.JSONField(blank=True, default=dict, encoder=utilities.json.CustomFieldJSONEncoder)),
                ('object_id', models.PositiveIntegerField(help_text='ID of the source object')),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Pending'),
                        ('running', 'Running'),
                        ('success', 'Success'),
                        ('failed', 'Failed'),
                        ('cancelled', 'Cancelled')
                    ],
                    default='pending',
                    help_text='Current status of the execution',
                    max_length=20
                )),
                ('started_at', models.DateTimeField(auto_now_add=True, help_text='When the execution was started')),
                ('completed_at', models.DateTimeField(blank=True, help_text='When the execution completed', null=True)),
                ('parameters_sent', models.JSONField(blank=True, default=dict, help_text='Parameters sent to the workflow')),
                ('execution_id', models.CharField(blank=True, help_text='External execution ID (AAP job ID, etc.)', max_length=255, null=True)),
                ('response_data', models.JSONField(blank=True, default=dict, help_text='Response received from the workflow platform')),
                ('error_message', models.TextField(blank=True, help_text='Error message if execution failed', null=True)),
                ('content_type', models.ForeignKey(
                    help_text='Type of the source object',
                    on_delete=django.db.models.deletion.CASCADE,
                    to='contenttypes.contenttype'
                )),
                ('user', models.ForeignKey(
                    blank=True,
                    help_text='User who triggered the execution',
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='workflow_executions',
                    to=settings.AUTH_USER_MODEL
                )),
                ('workflow', models.ForeignKey(
                    help_text='The workflow that was executed',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='executions',
                    to='business_application.externalworkflow'
                )),
            ],
            options={
                'verbose_name': 'Workflow Execution',
                'verbose_name_plural': 'Workflow Executions',
                'ordering': ['-started_at'],
            },
        ),
    ]

