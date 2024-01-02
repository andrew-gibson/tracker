# Generated by Django 5.0 on 2023-12-30 16:10

import core.rest
import django.db.models.deletion
import django_lifecycle.mixins
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="EXCompetency",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=300, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name="Contact",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("email", models.EmailField(max_length=254)),
                ("users", models.ManyToManyField(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "abstract": False,
            },
            bases=(django_lifecycle.mixins.LifecycleModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name="Project",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("text", models.TextField()),
                (
                    "parent_project",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="sub_projects",
                        to="project.project",
                    ),
                ),
                (
                    "point_of_contact",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="project.contact",
                    ),
                ),
                ("users", models.ManyToManyField(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "abstract": False,
            },
            bases=(
                core.rest.AutoCompleteNexus,
                django_lifecycle.mixins.LifecycleModelMixin,
                models.Model,
            ),
        ),
        migrations.CreateModel(
            name="ProjectTeam",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="project.project",
                    ),
                ),
            ],
            bases=(django_lifecycle.mixins.LifecycleModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name="Stream",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=300)),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="streams",
                        to="project.project",
                    ),
                ),
            ],
            options={
                "unique_together": {("name", "project")},
            },
            bases=(django_lifecycle.mixins.LifecycleModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name="Tag",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100)),
                ("users", models.ManyToManyField(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "abstract": False,
            },
            bases=(django_lifecycle.mixins.LifecycleModelMixin, models.Model),
        ),
        migrations.AddField(
            model_name="project",
            name="tags",
            field=models.ManyToManyField(to="project.tag"),
        ),
        migrations.CreateModel(
            name="Team",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255, unique=True)),
                ("private", models.BooleanField(default=True)),
                ("internal", models.BooleanField(default=False)),
                (
                    "projects",
                    models.ManyToManyField(
                        through="project.ProjectTeam", to="project.project"
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
            bases=(django_lifecycle.mixins.LifecycleModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name="StreamWork",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("target_date", models.DateTimeField()),
                ("name", models.CharField(max_length=255)),
                ("text", models.TextField()),
                ("addstamp", models.DateTimeField(auto_now_add=True)),
                ("editstamp", models.DateTimeField(auto_now=True)),
                ("done", models.BooleanField(db_default=models.Value(False))),
                (
                    "competency",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to="project.excompetency",
                    ),
                ),
                (
                    "lead",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="project.contact",
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="work_items",
                        to="project.project",
                    ),
                ),
                (
                    "stream",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="work_items",
                        to="project.stream",
                    ),
                ),
                ("teams", models.ManyToManyField(blank=True, to="project.team")),
            ],
            options={
                "abstract": False,
            },
            bases=(
                django_lifecycle.mixins.LifecycleModelMixin,
                models.Model,
                core.rest.AutoCompleteNexus,
            ),
        ),
        migrations.AddField(
            model_name="projectteam",
            name="team",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="project.team"
            ),
        ),
        migrations.AddField(
            model_name="project",
            name="teams",
            field=models.ManyToManyField(
                through="project.ProjectTeam", to="project.team"
            ),
        ),
        migrations.AlterUniqueTogether(
            name="projectteam",
            unique_together={("project", "team")},
        ),
    ]
