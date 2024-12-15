# Generated by Django 5.0.9 on 2024-12-15 18:36

import taggit.managers
import utilities.json
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('dcim', '0191_module_bay_rebuild'),
        ('extras', '0121_customfield_related_object_filter'),
        ('virtualization', '0040_convert_disk_size'),
    ]

    operations = [
        migrations.CreateModel(
            name='BusinessApplication',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('last_updated', models.DateTimeField(auto_now=True, null=True)),
                ('custom_field_data', models.JSONField(blank=True, default=dict, encoder=utilities.json.CustomFieldJSONEncoder)),
                ('appcode', models.CharField(max_length=20, unique=True)),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True)),
                ('owner', models.CharField(max_length=100)),
                ('delegate', models.CharField(blank=True, max_length=100, null=True)),
                ('servicenow', models.URLField(blank=True, null=True)),
                ('devices', models.ManyToManyField(blank=True, related_name='business_applications', to='dcim.device')),
                ('tags', taggit.managers.TaggableManager(through='extras.TaggedItem', to='extras.Tag')),
                ('virtual_machines', models.ManyToManyField(blank=True, related_name='business_applications', to='virtualization.virtualmachine')),
            ],
            options={
                'ordering': ['appcode'],
            },
        ),
    ]
