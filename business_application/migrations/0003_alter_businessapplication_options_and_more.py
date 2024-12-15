# Generated by Django 5.0.9 on 2024-12-15 13:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('business_application', '0002_businessapplication_devices'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='businessapplication',
            options={'ordering': ['appcode']},
        ),
        migrations.RemoveField(
            model_name='businessapplication',
            name='id',
        ),
        migrations.AlterField(
            model_name='businessapplication',
            name='appcode',
            field=models.CharField(max_length=20, primary_key=True, serialize=False, unique=True),
        ),
        migrations.AlterField(
            model_name='businessapplication',
            name='name',
            field=models.CharField(max_length=100),
        ),
    ]
