# Generated migration for ServiceDependency and TechnicalService refactor

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('business_application', '0002_changetype_change_eventsource_event_maintenance_and_more'),
    ]

    operations = [
        # Add service_type field to TechnicalService
        migrations.AddField(
            model_name='technicalservice',
            name='service_type',
            field=models.CharField(choices=[('technical', 'Technical'), ('logical', 'Logical')], default='technical', help_text='Type of service', max_length=16),
        ),

        # Remove parent field from TechnicalService
        migrations.RemoveField(
            model_name='technicalservice',
            name='parent',
        ),

        # Remove depends_on field from TechnicalService
        migrations.RemoveField(
            model_name='technicalservice',
            name='depends_on',
        ),

        # Create ServiceDependency model
        migrations.CreateModel(
            name='ServiceDependency',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('last_updated', models.DateTimeField(auto_now=True, null=True)),
                ('name', models.CharField(help_text='Name of the dependency relationship', max_length=240)),
                ('description', models.TextField(blank=True, help_text='Optional description of the dependency')),
                ('dependency_type', models.CharField(choices=[('normal', 'Normal'), ('redundancy', 'Redundancy')], default='normal', help_text='Normal: dependent on all upstream services, Redundancy: dependent on any upstream service', max_length=16)),
                ('downstream_service', models.ForeignKey(help_text='Service that depends on the upstream service', on_delete=django.db.models.deletion.CASCADE, related_name='upstream_dependencies', to='business_application.technicalservice')),
                ('upstream_service', models.ForeignKey(help_text='Service that is depended upon', on_delete=django.db.models.deletion.CASCADE, related_name='downstream_dependencies', to='business_application.technicalservice')),
            ],
            options={
                'verbose_name': 'Service Dependency',
                'verbose_name_plural': 'Service Dependencies',
                'ordering': ['name'],
            },
        ),

        # Add unique constraint for ServiceDependency
        migrations.AddConstraint(
            model_name='servicedependency',
            constraint=models.UniqueConstraint(fields=('upstream_service', 'downstream_service'), name='unique_service_dependency'),
        ),
    ]