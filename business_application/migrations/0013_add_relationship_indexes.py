# Generated migration for adding indexes to M2M relationship tables
# This improves query performance for the relationship API endpoints

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('business_application', '0012_externalworkflow_auto_trigger_and_more'),
    ]

    operations = [
        # Indexes for BusinessApplication <-> Device M2M relationship
        migrations.RunSQL(
            sql="CREATE INDEX IF NOT EXISTS idx_ba_devices_device_id ON business_application_businessapplication_devices(device_id);",
            reverse_sql="DROP INDEX IF EXISTS idx_ba_devices_device_id;"
        ),
        migrations.RunSQL(
            sql="CREATE INDEX IF NOT EXISTS idx_ba_devices_app_id ON business_application_businessapplication_devices(businessapplication_id);",
            reverse_sql="DROP INDEX IF EXISTS idx_ba_devices_app_id;"
        ),

        # Indexes for BusinessApplication <-> VirtualMachine M2M relationship
        migrations.RunSQL(
            sql="CREATE INDEX IF NOT EXISTS idx_ba_vms_vm_id ON business_application_businessapplication_virtual_machines(virtualmachine_id);",
            reverse_sql="DROP INDEX IF EXISTS idx_ba_vms_vm_id;"
        ),
        migrations.RunSQL(
            sql="CREATE INDEX IF NOT EXISTS idx_ba_vms_app_id ON business_application_businessapplication_virtual_machines(businessapplication_id);",
            reverse_sql="DROP INDEX IF EXISTS idx_ba_vms_app_id;"
        ),

        # Indexes for TechnicalService <-> Device M2M relationship
        migrations.RunSQL(
            sql="CREATE INDEX IF NOT EXISTS idx_ts_devices_device_id ON business_application_technicalservice_devices(device_id);",
            reverse_sql="DROP INDEX IF EXISTS idx_ts_devices_device_id;"
        ),
        migrations.RunSQL(
            sql="CREATE INDEX IF NOT EXISTS idx_ts_devices_service_id ON business_application_technicalservice_devices(technicalservice_id);",
            reverse_sql="DROP INDEX IF EXISTS idx_ts_devices_service_id;"
        ),

        # Indexes for TechnicalService <-> VirtualMachine M2M relationship
        migrations.RunSQL(
            sql="CREATE INDEX IF NOT EXISTS idx_ts_vms_vm_id ON business_application_technicalservice_vms(virtualmachine_id);",
            reverse_sql="DROP INDEX IF EXISTS idx_ts_vms_vm_id;"
        ),
        migrations.RunSQL(
            sql="CREATE INDEX IF NOT EXISTS idx_ts_vms_service_id ON business_application_technicalservice_vms(technicalservice_id);",
            reverse_sql="DROP INDEX IF EXISTS idx_ts_vms_service_id;"
        ),
    ]
