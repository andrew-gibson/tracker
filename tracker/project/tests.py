import dateparser
import random
import string
from urllib.parse import quote, urlencode
import faker
import pytest
from decouple import config
from django.apps import apps
from django.core.cache import cache
from django.urls import reverse
from django.core.management import call_command
from tracker.jinja2 import add_encode_parameter
from .models import (
    EXCompetency,
    ProjectUser,
    ProjectGroup,
    Project,
    Stream,
    Task,
    Tag,
    User,
)
from . import permissions

fake = faker.Faker()


def fake_request(username,_method="GET"):
    class R:
        user = User.objects.get(username=username)
        project_user = ProjectUser.objects.get(username=username)
        method = _method

    return R

def model_info(model,username):
    return  model.model_info(fake_request(username)) 

@pytest.fixture
def boss_client(client, load_fixtures):
    client.login(username="boss", password="boss")
    return client

@pytest.fixture
def teama_1_client(client):
    client.login(username="teama_1", password="teama_1")
    return client

@pytest.fixture
def teamb_1_client(client):
    client.login(username="teamb_1", password="teamb_1")
    return client

@pytest.fixture()
def data_loader(client,load_fixtures):

    class DataLoader:

        def __init__(self, username, password):
            self.switch_user(username,password)

        def model_info(self,model):
            return  model.model_info(fake_request(self.username)) 

        def switch_user(self,username, password):
            self.username = username
            return client.login(username=username,password=password)

        def get(self,model, url=None):
            if url is None:
                url = self.model_info(model)["main"]
            print(f"Getting {url}")
            resp =   client.get( url)
            if "insts" in resp.__context__:
                return resp, resp.__context__["insts"]
            else:
                return resp, resp.__context__["inst"]

        def getjson(self,url):
            print(f"Getting {url}")
            resp =   client.get( url, headers={"" : ""})
            if "insts" in resp.__context__:
                return resp, resp.__context__["insts"]
            else:
                return resp, resp.__context__["inst"]


        def post(self,url,data):
            print(f"Posting {data} to {url}")
            resp =   client.post( url, data = urlencode(data), content_type = "application/x-www-form-urlencoded")
            if hasattr(resp, "__context__"):
                return resp, resp.__context__["inst"]
            else:
                return resp, None


        def put(self,url,data):
            print(f"Putting {data} to {url}")
            resp = client.put( url, data = urlencode(data), content_type = "application/x-www-form-urlencoded")
            if hasattr(resp, "__context__"):
                return resp, resp.__context__["inst"]
            else:
                return resp, None

        def delete(self,url):
            print(f"Deleteing {url}")
            return client.delete( url )

        def new_projectgroup(self,data=None):
            if not data:
                data = {}
            data = {
                "name_en"  : fake.name(),
                "name_fr"  : fake.name(),
                "acronym_fr" : "".join(random.sample(string.ascii_uppercase, random.choice([2,3,4]))),
                "acronym_en" : "".join(random.sample(string.ascii_uppercase, random.choice([2,3,4]))),
                "app" : "project",
                **data
            }
            info = self.model_info(ProjectGroup)
            return self.post( info["main"], data)

        def new_projectuser(self,data=None):
            if not data:
                data = {}
            data = {
                "username"  : fake.user_name(),
                **data
            }
            info = self.model_info(ProjectUser)
            return self.post( info["main"], data)

        def new_project(self, data=None ):
            info = self.model_info(Project)
            if not data:
                data = {}
            data = {
                "text"  : fake.text(),
                **data
            }
            return self.post( info["main"], data)

        def new_stream(self, data=None, ):
            info = self.model_info(Stream)
            return self.post( info["main"], data)

        def new_task(self, data=None):
            info = self.model_info(Task)
            return self.post( info["main"], data)

        def new_tag(self, data=None):
            if not data:
                data = {}
            data = {
                "name"  : fake.slug(),
                **data
            }
            info = self.model_info(Tag)
            return self.post( info["main"], data)

        def new_log(self, data=None):
            info = self.model_info(Log)

        def new_link(self, data):
            info = self.model_info(Link)

        def new_timereport(self, data):
            info = self.model_info(TimeReport)

    return DataLoader 

@pytest.fixture(scope="session")
def load_fixtures(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        company = ProjectGroup.objects.create(name_en="Company")
        teamA = ProjectGroup.objects.create(name_en="TeamA", parent=company)
        teamB = ProjectGroup.objects.create(name_en="TeamB", parent=company)
        call_command("loaddata", "project/fixtures/fixtures.json")
        return [
            company,
            ProjectUser.objects.create_user(
                username="boss", password="boss", belongs_to=company, manages=company
            ),
            teamA,
            teamB,
            ProjectUser.objects.create_user(
                username="teama_1", password="teama_1", belongs_to=teamA
            ),
            ProjectUser.objects.create_user(
                username="teamb_1", password="teamb_1", belongs_to=teamB
            ),
        ]

###################################       ################################### 
################################### TESTS ###################################  
###################################       ################################### 

@pytest.mark.django_db
def test_project_text_parse_with_boss(boss_client, load_fixtures):
    company, boss, *_ = load_fixtures
    q = f"New Project @{boss.username[:-2]}"
    url =  reverse("core:parse_for_links", kwargs={"m": "project.Project", "attr": "name"}) 
    resp = boss_client.get( url + "?" + f"q={quote(q)}")
    assert list(
        map(lambda x: [x[0], x[1]["trigger"]], resp.__context__["results"].items())
    ) == [["parent_project", "^"], ["lead", "@"], ["tags", "#"]]
    assert len(resp.__context__["results"]["lead"]["results"][0][1]) == 2
    assert len(resp.__context__["results"]["tags"]["results"]) == 0
    assert len(resp.__context__["results"]["parent_project"]["results"]) == 0
    q = f"New Project @{boss.username[:-2]} #Urge"
    resp = boss_client.get( url + "?" + f"q={quote(q)}")
    assert len(resp.__context__["results"]["lead"]["results"][0][1]) == 1
    assert len(resp.__context__["results"]["tags"]["results"][0][1]) == 2
    assert len(resp.__context__["results"]["parent_project"]["results"]) == 0
    q = f"New Project @{boss.username} #Urgent"
    resp = boss_client.get( url + "?" + f"q={quote(q)}")
    assert len(resp.__context__["results"]["lead"]["results"][0][1]) == 1
    assert len(resp.__context__["results"]["tags"]["results"][0][1]) == 1
    assert len(resp.__context__["results"]["parent_project"]["results"]) == 0
    q = f"New Project @new_user #Urgent #newTag"
    resp = boss_client.post(
        reverse(
            "core:create_from_parsed", kwargs={"m": "project.Project", "attr": "name"}
        ),
        data={"q": q},
    )
    new_project = Project.objects.get(name_en="New Project")
    assert new_project.lead == ProjectUser.objects.get(username="new_user")
    assert Tag.objects.get(name="newTag") in new_project.tags.all()
    assert Tag.objects.get(name="Urgent") in new_project.tags.all()

    url =   reverse("core:parse_for_links", kwargs={"m": "project.Task", "attr": "name"}) 



@pytest.mark.django_db
def test_project_text_parse_with_team_member(teama_1_client, load_fixtures):
    q = f"New Project @new_user #Urgent #newTag"
    resp = teama_1_client.post(
        reverse(
            "core:create_from_parsed", kwargs={"m": "project.Project", "attr": "name"}
        ),
        data={"q": q},
    )
    new_project = Project.objects.get(name_en="New Project")
    assert new_project.lead == None
    assert Tag.objects.get(name="newTag") in new_project.tags.all()
    assert Tag.objects.get(name="Urgent") in new_project.tags.all()

@pytest.mark.django_db
def test_project_main(boss_client, load_fixtures):
    client = boss_client
    assert client.get("/project/main/").__context__["standalone"]

@pytest.mark.django_db
def test_permissions(data_loader, load_fixtures):
    company, boss, teamA, teamB, teamA_user, teamB_user = load_fixtures
    dl = data_loader("boss","boss")
    # download existing groups
    resp, existing_groups = dl.get(ProjectGroup)
    assert resp.status_code == 200
    # make a new group
    resp, projectgroup = dl.new_projectgroup()
    assert resp.status_code == 200
    # delete the group
    resp = dl.delete(projectgroup["__url__"])
    assert resp.status_code == 200
    # create a new user for TeamA
    resp, projectuser1 = dl.new_projectuser({"belongs_to" : teamA.id})
    assert resp.status_code == 200
    projectuser1_obj = ProjectUser.objects.get(id=projectuser1["id"])
    projectuser1_obj.set_password("password")
    projectuser1_obj.is_active = True
    projectuser1_obj.save()
    # create a new user for TeamB
    resp, projectuser2 = dl.new_projectuser({"belongs_to" : teamB.id})
    assert resp.status_code == 200

    # log in as projectuser1
    assert dl.switch_user(projectuser1["username"], "password")
    # other user can't delete 
    resp = dl.delete(projectuser2["__url__"])
    assert resp.status_code == 403
    
    # log back in as boss
    assert dl.switch_user("boss", "boss")
    # only a manager can delete a user 
    resp = dl.delete(projectuser2["__url__"])
    assert resp.status_code == 200
    # recreate a new user for TeamB
    resp, projectuser2 = dl.new_projectuser({"belongs_to" : teamB.id})
    assert resp.status_code == 200
    projectuser2_obj = ProjectUser.objects.get(id=projectuser2["id"])
    projectuser2_obj.set_password("password")
    projectuser2_obj.is_active = True
    projectuser2_obj.save()

    # log in as projectuser1
    assert dl.switch_user(projectuser1["username"], "password")
    # create a new project for teamA
    resp, project1 = dl.new_project({
        "name" : fake.company(),
    })
    assert resp.status_code == 200
    assert Project.objects.get(name_en=project1["name"]).group == teamA
    # log in as projectuser2
    assert dl.switch_user(projectuser2["username"], "password")
    # create a new project for teamB
    resp, project2 = dl.new_project({
        "name" : fake.company(),
    })
    assert resp.status_code == 200
    assert Project.objects.get(name_en=project2["name"]).group == teamB
    assert Project.objects.count()  == 2
    # log in as projectuser1
    assert dl.switch_user(projectuser1["username"], "password")
    # prjectuser1 shouldn't be able to delete project 2
    resp = dl.delete(project2["__url__"])
    assert resp.status_code == 403
    # log back in as boss
    assert dl.switch_user("boss", "boss")
    assert teamA.team_members.count() == 2
    # move projectuser2 to teamA
    resp, projectuser2 = dl.put(
            projectuser2["__url__"],
            {
                **projectuser2,
                "belongs_to" : teamA.id
                })
    assert resp.status_code == 200
    assert teamA.team_members.count() == 3
    # move projectuser2 back to teamB
    resp, projectuser2 = dl.put(
            projectuser2["__url__"],
            {
                **projectuser2,
                "belongs_to" : teamB.id
                })
    assert resp.status_code == 200
    assert teamA.team_members.count() == 2
    # log in as projectuser1
    assert dl.switch_user(projectuser1["username"], "password")
    # create a new stream
    resp, project1_stream1 = dl.new_stream({
        "name" : fake.name().replace(" ", "_"),
        "project" : project1["id"]
    })
    assert resp.status_code == 200
    # make sure projectuser1 can't create a new stream on someone else's project
    resp, project1_stream1 = dl.new_stream({
        "name" : fake.name().replace(" ", "_"),
        "project" : project2["id"]
    })
    assert resp.status_code == 403
    # create a new Task




    #assert new_project.due_date.day == dateparser.parse("tomorrow").day 



@pytest.mark.skip
@pytest.mark.django_db
def test_employee_create_task(client, load_fixtures):
    test_employees_create_stream(client,load_fixtures)
    assert Project.objects.count() == 1


#@pytest.mark.skip
#@pytest.mark.django_db
#def test_project_text_parse_with_boss(boss_client, load_fixtures):
#    company, boss, teamA, team_1, *_ = load_fixtures
#    q = f"New Project @new_user #Urgent #newTag"
#    resp = boss_client.post(
#        reverse(
#            "core:create_from_parsed", kwargs={"m": "project.Project", "attr": "name"}
#        ),
#        data={"q": q},
#    )
#    new_project = Project.objects.get(name_en="New Project")
#    params = (
#        add_encode_parameter(
#            "f",
#            {
#                "ac_filters": {"stream": {"project_id": new_project.id}},
#                "attach_to": {"attr": "project", "pk": new_project.id},
#                "excludes": ["project", "competency"],
#            },
#        ),
#    )


