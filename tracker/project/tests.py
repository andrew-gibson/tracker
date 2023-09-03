import random

import faker
import pytest
from decouple import config
from django.apps import apps
from django.core.cache import cache
from django.test import TestCase

from .models import (
    Contact,
    EXCompetency,
    Project,
    SubTheme,
    SubThemeWork,
    Tag,
    Team,
    Theme,
    ThemeWork,
)

fake = faker.Faker()


def test_project_create(transactional_db, client):
    cache.clear()
    User = apps.get_model("core.User")

    assert 6 == EXCompetency.objects.count()

    # login
    client.post(
        "/core/login/",
        {
            "username": "andrew",
            "password": config("ANDREW_PASSWORD"),
        },
        follow=True,
    )

    teams = []
    for x in range(10):
        resp = client.post("/project/m/team/",
                           { "name":fake.name(), 
                            })
        team = resp.__context__["team"]
        teams.append(team)
        assert team.pk
    assert Team.objects.count() == 10


    for x in range(10):
        resp = client.post("/project/m/tag/",
                           { "name":fake.name(), 
                            })
        tag = resp.__context__["tag"]
        assert tag.pk
    assert Tag.objects.count() == 10


    contacts = []
    for x in range(10):
        resp = client.post("/project/m/contact/",
                           { "name":fake.name(), 
                            "email": fake.email()
                            })
        contact = resp.__context__["contact"]
        contacts.append(contact)
        assert contact.pk
    assert Contact.objects.count() == 10

    projects = []
    for x in range(10):

        project = Project(
            name=fake.name(),
            point_of_contact=Contact.objects.order_by("?").first(),
        )
        projects.append(project)
        project.save()

        assert project.theme_set.count() == EXCompetency.objects.count()

        if x == 0:
            project.users.add(User.objects.get(username="root"))
        else:
            project.users.add(User.objects.get(username="andrew"))

        extra_teams = random.choice([1, 2])
        project.teams.add(*list(Team.objects.order_by("?")[0:extra_teams]))
        extra_tags = random.choice([1, 2])
        project.tags.add(*list(Tag.objects.order_by("?")[0:extra_tags]))

        if random.choice([True, False]):
            project.parent_project = Project.objects.filter(
                parent_project__isnull=True
            ).order_by("?")[0]
        project.save()


    # test getting all projects for the user
    resp = client.get("/project/m/project/")

    # test all but the root owned project is in the group template
    # context
    for project in projects[1:]:
        assert project in resp.__context__["projects"]

    # check each project is in the resp context
    for project in projects[1:]:
        resp = client.get(f"/project/m/project/{project.pk}/")
        assert project == resp.__context__["project"]

    # this delete shouldn't work, project is owned by root
    client.delete(f"/project/m/project/{projects[0].pk}/")
    assert Project.objects.count() == 10

    # this delete shouldn work
    client.delete(f"/project/m/project/{projects[1].pk}/")
    assert Project.objects.count() == 9
    
    # add themework
    for project in projects[2:]:
        for theme in project.theme_set.all():
            resp = client.post("/project/m/themework/",
                        {"title" : fake.name(),
                         "target_date" : fake.date(),
                         "parent" : theme.pk,
                         "text" : fake.text(),
                         "lead" : random.choice(contacts).pk,
                         "teams" : [x.pk for x in random.choices(teams,k=2)]
                         })
            themework = resp.__context__["themework"]
            assert theme.work_details.count() == 1
            assert theme.work_details.first() == themework



                     

