# Generated migration to add custom_field_data to ServiceDependency

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('business_application', '0003_servicedependency_technicalservice_refactor'),
    ]

    operations = [
        # Add custom_field_data field to ServiceDependency
        migrations.AddField(
            model_name='servicedependency',
            name='custom_field_data',
            field=models.JSONField(blank=True, default=dict, editable=False),
        ),
    ]