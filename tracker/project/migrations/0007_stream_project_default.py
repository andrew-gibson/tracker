# Generated by Django 5.0.1 on 2024-01-15 02:24

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("project", "0006_rename_streamwork_task"),
    ]

    operations = [
        migrations.AddField(
            model_name="stream",
            name="project_default",
            field=models.BooleanField(default=False),
        ),
    ]
