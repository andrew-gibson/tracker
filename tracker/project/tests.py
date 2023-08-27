import random

import faker
import pytest
from decouple import config
from django.core.cache import cache
from django.test import TestCase
from django.apps import apps

from .models import Contact, Event, EventLog, Project, Tag, Team

fake = faker.Faker()


def test_project_create(transactional_db, client):
    cache.clear()
    User = apps.get_model("core.User")
    Team.objects.bulk_create([Team(name=fake.name()) for x in range(10)])
    Tag.objects.bulk_create([Tag(name=fake.name()) for x in range(10)])
    Contact.objects.bulk_create(
        [Contact(name=fake.name(), email=fake.email()) for x in range(10)]
    )
    projects = [
        Project(
            user=User.objects.get(username="andrew" if x != 0 else "root"),
            name=fake.name(),
            point_of_contact=Contact.objects.order_by("?").first(),
        )
        for x in range(10)
    ]
    Project.objects.bulk_create(projects)
    for project in projects:
        extra_teams = random.choice([1, 2])
        project.teams.add(*list(Team.objects.order_by("?")[0:extra_teams]))
        extra_tags = random.choice([1, 2])
        project.tags.add(*list(Tag.objects.order_by("?")[0:extra_tags]))
        if random.choice([True, False]):
            project.parent_project = Project.objects.filter(
                parent_project__isnull=True
            ).order_by("?")[0]
        project.save()

    # login
    client.post(
        "/core/login/",
        {
            "username": "andrew",
            "password": config("ANDREW_PASSWORD"),
        },
        follow=True,
    )

    # test getting all projects for the user
    resp = client.get("/project/project/")

    for project in projects[1:]:
        assert project in resp.__context__["projects"]

    for project in projects[1:]:
        resp = client.get(f"/project/project/{project.pk}/")
        assert project == resp.__context__["project"]

    client.delete( f"/project/project/{projects[0].pk}/")
    import pdb
    pdb.set_trace()
    assert Project.objects.count() == 10

    client.delete( f"/project/project/{projects[1].pk}/")
    assert Project.objects.count() == 9


