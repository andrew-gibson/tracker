# Generated by Django 5.0.8 on 2024-08-10 04:11

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("project", "0032_projectstatus_active"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="tag",
            unique_together={("group", "name")},
        ),
    ]
