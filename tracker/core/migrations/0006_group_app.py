# Generated by Django 5.0.6 on 2024-05-20 02:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_group_system"),
    ]

    operations = [
        migrations.AddField(
            model_name="group",
            name="app",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
