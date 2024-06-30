# Generated by Django 5.0.6 on 2024-06-29 19:27

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0011_alter_user_groups"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="belongs_to",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="team_members",
                to="core.group",
            ),
        ),
    ]
