# Generated by Django 5.1 on 2024-08-13 20:19

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("project", "0037_remove_projectlogentry_log_delete_projectlog"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="ProjectLogEntry",
            new_name="ProjectLog",
        ),
    ]
