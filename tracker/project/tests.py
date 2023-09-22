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
    Tag,
    Team,
    Theme,
    ThemeWork,
)

fake = faker.Faker()


def test_project_create(transactional_db, client):
    cache.clear()
    User = apps.get_model("core.User")

    user2 = User.objects.create_user("user2")
    user2.set_password("user2")
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
        team = resp.__context__["inst"]
        teams.append(team)
        assert team.pk
    assert Team.objects.count() == 10


    for x in range(10):
        resp = client.post("/project/m/tag/",
                           { "name":fake.name(), 
                            })
        tag = resp.__context__["inst"]
        assert tag.pk
    assert Tag.objects.count() == 10


    contacts = []
    for x in range(10):
        resp = client.post("/project/m/contact/",
                           { "name":fake.name(), 
                            "email": fake.email()
                            })
        contact = resp.__context__["inst"]
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
        assert project in resp.__context__["insts"]

    assert projects[0] not in resp.__context__["insts"]

    # check each project is in the resp context
    for project in projects[1:]:
        resp = client.get(f"/project/m/project/{project.pk}/")
        assert project == resp.__context__["inst"]

    # this delete shouldn't work, project is owned by root
    client.delete(f"/project/m/project/{projects[0].pk}/")
    assert Project.objects.count() == 10

    # this delete shouldn work
    client.delete(f"/project/m/project/{projects[1].pk}/")
    assert Project.objects.count() == 9
    
    # add themework
    for project in projects[2:]:
        resp = client.post("/project/m/theme/",
                    {"name" : fake.name(),
                     "project" : project.pk,
                    })
        assert project.themes.count() == 1
        theme =  resp.__context__["inst"]

        for x in range(10):
            resp = client.post("/project/m/themework/",
                        {"name" : fake.name(),
                         "target_date" : fake.date(),
                         "theme" : theme.pk,
                         "text" : fake.text(),
                         "lead" : random.choice(contacts).pk,
                         "competency" : "",
                         "teams" : [x.pk for x in random.choices(teams,k=2)]
                        })
            themework = resp.__context__["inst"]

            assert theme.work_details.last() == themework


        assert theme.work_details.count() == 10
        client.post(f"/project/m2m/project.project/{project.pk}/core.user/{user2.pk}/")
        assert project.users.count() == 2

        tagsk

    # login as second user
    client.post(
        "/core/login/",
        {
            "username": "user2",
            "password": "user2",
        },
        follow=True,
    )
    # check that the other user can add a new theme
    for project in projects[2:]:
        resp = client.post("/project/m/theme/",
                    {"name" : fake.name(),
                     "project" : project.pk,
                    })
        #check we now have two themes
        assert project.themes.count() == 2
        # remove user from project
        client.delete(f"/project/mp2m/project.project/{project.pk}/core.user/{user2.pk}/")
        assert project.users.count() == 1




        
        ##assert project.users.count() == 2
