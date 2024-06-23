# Generated by Django 5.0.6 on 2024-06-22 20:37

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("project", "0022_timereport_text"),
    ]

    operations = [
        migrations.AlterField(
            model_name="timereport",
            name="time",
            field=models.DecimalField(
                decimal_places=1,
                max_digits=5,
                validators=[django.core.validators.MinValueValidator(0)],
            ),
        ),
    ]
