# Generated by Django 5.0.9 on 2024-12-09 22:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('business_application', '0001_initial'),
        ('dcim', '0191_module_bay_rebuild'),
    ]

    operations = [
        migrations.AddField(
            model_name='businessapplication',
            name='devices',
            field=models.ManyToManyField(blank=True, related_name='business_applications', to='dcim.device'),
        ),
    ]

