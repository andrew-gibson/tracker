# Generated by Django 5.1 on 2024-08-13 20:17

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("project", "0036_projectlogentry_project_projectdoc"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="projectlogentry",
            name="log",
        ),
        migrations.DeleteModel(
            name="ProjectLog",
        ),
    ]
