# Generated by Django 5.0.8 on 2024-08-11 02:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("project", "0033_alter_tag_unique_together"),
    ]

    operations = [
        migrations.AddField(
            model_name="task",
            name="old_target_dates",
            field=models.JSONField(default=list),
        ),
    ]
