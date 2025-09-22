# Generated migration for complete PagerDuty Templates system (clean version)

from django.db import migrations, models
import django.db.models.deletion
import taggit.managers
import utilities.json


def remove_existing_pagerduty_data(apps, schema_editor):
    """Remove any existing PagerDuty data to start clean"""
    # Get the model classes
    TechnicalService = apps.get_model('business_application', 'TechnicalService')
    
    # Try to get PagerDutyTemplate if it exists
    try:
        PagerDutyTemplate = apps.get_model('business_application', 'PagerDutyTemplate')
        # Clear all existing templates
        PagerDutyTemplate.objects.all().delete()
    except:
        # Table doesn't exist yet, which is fine
        pass
    
    # Clear any existing pagerduty_template references if they exist
    try:
        # This will fail if the field doesn't exist, which is fine
        TechnicalService.objects.filter(pagerduty_template__isnull=False).update(pagerduty_template=None)
    except:
        pass


class Migration(migrations.Migration):

    dependencies = [
        ('business_application', '0004_add_custom_field_data_to_servicedependency'),
        ('extras', '0122_charfield_null_choices'),
    ]

    operations = [
        # First, clean up any existing data
        migrations.RunPython(remove_existing_pagerduty_data, migrations.RunPython.noop),
        
        # Remove existing PagerDutyTemplate table if it exists
        migrations.RunSQL(
            "DROP TABLE IF EXISTS business_application_pagerdutytemplate CASCADE;",
            reverse_sql="-- No reverse operation needed"
        ),
        
        # Remove any existing pagerduty fields from TechnicalService
        migrations.RunSQL(
            """
            ALTER TABLE business_application_technicalservice 
            DROP COLUMN IF EXISTS pagerduty_config,
            DROP COLUMN IF EXISTS pagerduty_template_id;
            """,
            reverse_sql="-- No reverse operation needed"
        ),
        
        # Create PagerDutyTemplate model with all fields
        migrations.CreateModel(
            name='PagerDutyTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('last_updated', models.DateTimeField(auto_now=True, null=True)),
                ('custom_field_data', models.JSONField(blank=True, default=dict, encoder=utilities.json.CustomFieldJSONEncoder)),
                ('name', models.CharField(max_length=100, unique=True, help_text='Template name for easy identification')),
                ('description', models.TextField(blank=True, help_text='Description of this PagerDuty template')),
                ('template_type', models.CharField(
                    choices=[
                        ('service_definition', 'Service Definition'),
                        ('router_rule', 'Router Rule')
                    ],
                    help_text='Type of PagerDuty template (Service Definition or Router Rule)',
                    max_length=20
                )),
                ('pagerduty_config', models.JSONField(help_text='PagerDuty service configuration in API format')),
            ],
            options={
                'verbose_name': 'PagerDuty Template',
                'verbose_name_plural': 'PagerDuty Templates',
                'ordering': ['name'],
            },
        ),
        
        # Add PagerDuty template foreign keys to TechnicalService
        migrations.AddField(
            model_name='technicalservice',
            name='pagerduty_service_definition',
            field=models.ForeignKey(
                blank=True,
                help_text='PagerDuty service definition template',
                limit_choices_to={'template_type': 'service_definition'},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='services_using_definition',
                to='business_application.pagerdutytemplate'
            ),
        ),
        migrations.AddField(
            model_name='technicalservice',
            name='pagerduty_router_rule',
            field=models.ForeignKey(
                blank=True,
                help_text='PagerDuty router rule template',
                limit_choices_to={'template_type': 'router_rule'},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='services_using_router_rule',
                to='business_application.pagerdutytemplate'
            ),
        ),
    ]
