# Generated by Django 5.0.6 on 2024-06-29 21:16

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("project", "0025_rename_teams_project_partners"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="project_manager",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="projects_i_manage",
                to="project.projectuser",
            ),
        ),
    ]
