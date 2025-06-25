# Generated migration for Incident model

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('contenttypes', '0002_remove_content_type_name'),
        ('business_application', '0003_technicalservice_depends_on'),
    ]

    operations = [
        migrations.CreateModel(
            name='Incident',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('last_updated', models.DateTimeField(auto_now=True, null=True)),
                ('custom_field_data', models.JSONField(blank=True, default=dict, encoder=None)),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField()),
                ('status', models.CharField(choices=[('new', 'New'), ('investigating', 'Investigating'), ('identified', 'Identified'), ('monitoring', 'Monitoring'), ('resolved', 'Resolved'), ('closed', 'Closed')], max_length=16)),
                ('severity', models.CharField(choices=[('critical', 'Critical'), ('high', 'High'), ('medium', 'Medium'), ('low', 'Low')], max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('detected_at', models.DateTimeField(blank=True, null=True)),
                ('resolved_at', models.DateTimeField(blank=True, null=True)),
                ('reporter', models.CharField(blank=True, max_length=120)),
                ('commander', models.CharField(blank=True, help_text='Incident commander', max_length=120)),
                ('affected_services', models.ManyToManyField(blank=True, help_text='Technical services affected by this incident', related_name='incidents', to='business_application.technicalservice')),
                ('events', models.ManyToManyField(blank=True, help_text='Events related to this incident', related_name='incidents', to='business_application.event')),
                ('responders', models.ManyToManyField(blank=True, help_text='Users responding to this incident', related_name='incidents_responding', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]