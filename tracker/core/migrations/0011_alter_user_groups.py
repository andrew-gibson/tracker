# Generated by Django 5.0.6 on 2024-06-16 19:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0010_alter_user_manages"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="groups",
            field=models.ManyToManyField(
                blank=True, related_name="users", to="core.group"
            ),
        ),
    ]
