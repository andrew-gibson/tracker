# Generated by Django 5.0.6 on 2024-06-02 02:19

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("project", "0018_projectlogentry_user_alter_settings_user_and_more"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="project",
            options={"ordering": ("name_en",)},
        ),
        migrations.AlterField(
            model_name="contact",
            name="account",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="contact",
                to="project.projectuser",
            ),
        ),
        migrations.AlterField(
            model_name="task",
            name="order",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
