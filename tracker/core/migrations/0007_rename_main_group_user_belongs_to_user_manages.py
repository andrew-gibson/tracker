# Generated by Django 5.0.6 on 2024-05-22 13:52

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_group_app"),
    ]

    operations = [
        migrations.RenameField(
            model_name="user",
            old_name="main_group",
            new_name="belongs_to",
        ),
        migrations.AddField(
            model_name="user",
            name="manages",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="core.group",
            ),
        ),
    ]
