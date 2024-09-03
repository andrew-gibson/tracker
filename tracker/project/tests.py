import random
from urllib.parse import quote
import faker
import pytest
from decouple import config
from django.apps import apps
from django.core.cache import cache
from django.urls import reverse
from django.core.management import call_command
from .models import (
    EXCompetency,
    ProjectUser,
    ProjectGroup,
    Project,
    Tag,

    # Team,
    # Theme,
    # ThemeWork,
)

fake = faker.Faker()


@pytest.fixture(scope="session")
def load_fixtures(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        company = ProjectGroup.objects.create(name_en="Company")
        teamA = ProjectGroup.objects.create(name_en="TeamA")
        call_command("loaddata", "project/fixtures/fixtures.json")
        return [
            company,
             ProjectUser.objects.create_user(
                username="boss", password="boss", belongs_to=company, manages=teamA
            ),
            teamA,
            ProjectUser.objects.create_user(
                username="teama_1", password="teama_1", belongs_to=teamA
            ),
        ]

@pytest.mark.django_db
def test_project_main(client, load_fixtures):
    company, boss, *_ =   load_fixtures
    assert client.login(username="boss", password="boss")
    assert client.get("/project/main/").__context__["standalone"]

@pytest.mark.django_db
def test_project_options_with_boss(client, load_fixtures):
    company, boss, *_ =   load_fixtures
    client.login(username="boss", password="boss")
    q = f"New Project @{boss.username[:-2]}"
    resp = client.get(
        reverse("core:parse_for_links", kwargs={"m": "project.Project", "attr": "name"})
        + "?"
        + f"q={quote(q)}"
    )
    assert list(map(lambda x: [x[0],x[1]["trigger"]], resp.__context__["results"].items())) == [['parent_project', '^'], ['lead', '@'], ['tags', '#']]
    assert len(resp.__context__["results"]["lead"]["results"][0][1]) == 2
    assert len(resp.__context__["results"]["tags"]["results"]) == 0
    assert len(resp.__context__["results"]["parent_project"]["results"]) == 0
    q = f"New Project @{boss.username[:-2]} #Urge"
    resp = client.get(
        reverse("core:parse_for_links", kwargs={"m": "project.Project", "attr": "name"})
        + "?"
        + f"q={quote(q)}"
    )
    assert len(resp.__context__["results"]["lead"]["results"][0][1]) == 1
    assert len(resp.__context__["results"]["tags"]["results"][0][1]) == 2
    assert len(resp.__context__["results"]["parent_project"]["results"]) == 0
    q = f"New Project @{boss.username} #Urgent"
    resp = client.get(
        reverse("core:parse_for_links", kwargs={"m": "project.Project", "attr": "name"})
        + "?"
        + f"q={quote(q)}"
    )
    assert len(resp.__context__["results"]["lead"]["results"][0][1]) == 1
    assert len(resp.__context__["results"]["tags"]["results"][0][1]) == 1
    assert len(resp.__context__["results"]["parent_project"]["results"]) == 0
    q = f"New Project @new_user #Urgent #newTag"
    resp = client.post(
        reverse("core:create_from_parsed", kwargs={"m": "project.Project", "attr": "name"}),
        data = {"q": q}
    )
    new_project = Project.objects.get(name_en="New Project")
    assert new_project.lead == ProjectUser.objects.get(username="new_user")
    assert Tag.objects.get(name="newTag") in new_project.tags.all() 
    assert Tag.objects.get(name="Urgent") in   new_project.tags.all()  


@pytest.mark.django_db
def test_project_options_with_team_member(client, load_fixtures):
    company, boss, teamA, team_1 =   load_fixtures
    assert client.login(username="teama_1", password="teama_1")
    q = f"New Project @new_user #Urgent #newTag"
    resp = client.post(
        reverse("core:create_from_parsed", kwargs={"m": "project.Project", "attr": "name"}),
        data = {"q": q}
    )
    new_project = Project.objects.get(name_en="New Project")
    assert new_project.lead == None
    assert Tag.objects.get(name="newTag") in new_project.tags.all() 
    assert Tag.objects.get(name="Urgent") in   new_project.tags.all()  


# def test_project_create(transactional_db, client):
#    cache.clear()
#    User = apps.get_model("core.User")
#
#    user2 = User.objects.create_user("user2")
#    user2.set_password("user2")
#    assert 6 == EXCompetency.objects.count()
#
#    # login
#
#    teams = []
#    for x in range(10):
#        resp = client.post("/project/m/team/",
#                           { "name":fake.name(),
#                            })
#        team = resp.__context__["inst"]
#        teams.append(team)
#        assert team.pk
#    assert Team.objects.count() == 10
#
#
#    for x in range(10):
#        resp = client.post("/project/m/tag/",
#                           { "name":fake.name(),
#                            })
#        tag = resp.__context__["inst"]
#        assert tag.pk
#    assert Tag.objects.count() == 10
#
#
#    contacts = []
#    for x in range(10):
#        resp = client.post("/project/m/contact/",
#                           { "name":fake.name(),
#                            "email": fake.email()
#                            })
#        contact = resp.__context__["inst"]
#        contacts.append(contact)
#        assert contact.pk
#    assert Contact.objects.count() == 10
#
#    projects = []
#    for x in range(10):
#
#        project = Project(
#            name=fake.name(),
#            point_of_contact=Contact.objects.order_by("?").first(),
#        )
#        projects.append(project)
#        project.save()
#
#        if x == 0:
#            project.users.add(User.objects.get(username="root"))
#        else:
#            project.users.add(User.objects.get(username="andrew"))
#
#        extra_teams = random.choice([1, 2])
#        project.teams.add(*list(Team.objects.order_by("?")[0:extra_teams]))
#        extra_tags = random.choice([1, 2])
#        project.tags.add(*list(Tag.objects.order_by("?")[0:extra_tags]))
#
#        if random.choice([True, False]):
#            project.parent_project = Project.objects.filter(
#                parent_project__isnull=True
#            ).order_by("?")[0]
#        project.save()
#
#
#    # test getting all projects for the user
#    resp = client.get("/project/m/project/")
#
#    # test all but the root owned project is in the group template
#    # context
#    for project in projects[1:]:
#        assert project in resp.__context__["insts"]
#
#    assert projects[0] not in resp.__context__["insts"]
#
#    # check each project is in the resp context
#    for project in projects[1:]:
#        resp = client.get(f"/project/m/project/{project.pk}/")
#        assert project == resp.__context__["inst"]
#
#    # this delete shouldn't work, project is owned by root
#    client.delete(f"/project/m/project/{projects[0].pk}/")
#    assert Project.objects.count() == 10
#
#    # this delete shouldn work
#    client.delete(f"/project/m/project/{projects[1].pk}/")
#    assert Project.objects.count() == 9
#
#    # add themework
#    for project in projects[2:]:
#        resp = client.post("/project/m/theme/",
#                    {"name" : fake.name(),
#                     "project" : project.pk,
#                    })
#        assert project.themes.count() == 1
#        theme =  resp.__context__["inst"]
#
#        for x in range(10):
#            resp = client.post("/project/m/themework/",
#                        {"name" : fake.name(),
#                         "target_date" : fake.date(),
#                         "theme" : theme.pk,
#                         "text" : fake.text(),
#                         "lead" : random.choice(contacts).pk,
#                         "competency" : "",
#                         "teams" : [x.pk for x in random.choices(teams,k=2)]
#                        })
#            themework = resp.__context__["inst"]
#
#            assert theme.work_details.last() == themework
#
#
#        assert theme.work_details.count() == 10
#        client.post(f"/project/m2m/project.project/{project.pk}/core.user/{user2.pk}/")
#        assert project.users.count() == 2
#
#        tagsk
#
#    # login as second user
#    client.post(
#        "/core/login/",
#        {
#            "username": "user2",
#            "password": "user2",
#        },
#        follow=True,
#    )
#    # check that the other user can add a new theme
#    for project in projects[2:]:
#        resp = client.post("/project/m/theme/",
#                    {"name" : fake.name(),
#                     "project" : project.pk,
#                    })
#        #check we now have two themes
#        assert project.themes.count() == 2
#        # remove user from project
#        client.delete(f"/project/mp2m/project.project/{project.pk}/core.user/{user2.pk}/")
#        assert project.users.count() == 1
#
#
#
#
#
#        ##assert project.users.count() == 2
