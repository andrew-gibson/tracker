# Generated by Django 5.0.6 on 2024-06-19 00:53

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("project", "0020_alter_task_lead_minproject_alter_project_leads_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="project",
            name="teams",
            field=models.ManyToManyField(
                blank=True,
                related_name="projects_supporting",
                to="project.projectgroup",
            ),
        ),
        migrations.AlterField(
            model_name="settings",
            name="user",
            field=models.OneToOneField(
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="project.projectuser",
            ),
        ),
        migrations.AlterField(
            model_name="timereport",
            name="project",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="timereports",
                to="project.project",
            ),
        ),
    ]
