from django.db import migrations, connection

def fix_relationship_tables(apps, schema_editor):
    # Raw SQL to fix relationship tables

    with connection.cursor() as cursor:
        # List of relationship tables and the necessary transformations
        relationship_tables = [
            {
                "table_name": "business_application_businessapplication_virtual_machines",
                "old_column": "businessapplication_id",
                "new_column": "businessapplication_appcode",
                "referenced_table": "business_application_businessapplication",
            },
            {
                "table_name": "business_application_businessapplication_devices",
                "old_column": "businessapplication_id",
                "new_column": "businessapplication_appcode",
                "referenced_table": "business_application_businessapplication",
            },
        ]

        for table in relationship_tables:
            table_name = table["table_name"]
            old_column = table["old_column"]
            new_column = table["new_column"]
            referenced_table = table["referenced_table"]


            # Step 1: Drop the old foreign key constraint
            cursor.execute(f"""
                DO $$
                DECLARE
                    constraint_name TEXT;
                BEGIN
                    SELECT conname INTO constraint_name
                    FROM pg_constraint
                    WHERE conrelid = '{table_name}'::regclass
                    AND confrelid = '{referenced_table}'::regclass;

                    IF constraint_name IS NOT NULL THEN
                        EXECUTE format('ALTER TABLE {table_name} DROP CONSTRAINT %I;', constraint_name);
                    END IF;
                END $$;
            """)

            # Step 2: Alter the column type to match `businessapplication_appcode`
            cursor.execute(f"""
                ALTER TABLE {table_name}
                ALTER COLUMN {old_column} TYPE character varying
                USING {old_column}::character varying;
            """)

            # Step 3: Rename the column to `businessapplication_appcode`
            cursor.execute(f"""
                ALTER TABLE {table_name}
                RENAME COLUMN {old_column} TO {new_column};
            """)

            # Step 4: Add a new foreign key constraint
            cursor.execute(f"""
                ALTER TABLE {table_name}
                ADD CONSTRAINT {table_name}_{new_column}_fkey
                FOREIGN KEY ({new_column})
                REFERENCES {referenced_table}(appcode);
            """)

def no_op(*args, **kwargs):
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('business_application', '0003_alter_businessapplication_options_and_more'),  # Update with the correct dependency
    ]

    operations = [
        migrations.RunPython(fix_relationship_tables, no_op),
    ]
