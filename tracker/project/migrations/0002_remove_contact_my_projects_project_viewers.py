# Generated by Django 5.0.6 on 2024-05-18 13:56

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("project", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveField(
            model_name="contact",
            name="my_projects",
        ),
        migrations.AddField(
            model_name="project",
            name="viewers",
            field=models.ManyToManyField(
                blank=True, related_name="projects", to=settings.AUTH_USER_MODEL
            ),
        ),
    ]
