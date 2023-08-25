import sys

import faker
import pytest
from decouple import config
from django.test import TestCase

from .models import EXCompetency, Project, User

pytestmark = pytest.mark.django_db
fake = faker.Faker()

def test_competency_load():
    assert 6 == EXCompetency.objects.count() 

def test_create_project():
    p = Project(
            name = fake.bs(),
            description = fake.text(),
            user = User.objects.get(username="andrew")
        )
    p.save()
    assert p.theme_set.count() == EXCompetency.objects.count()  

def test_user_login(client):
    resp = client.post("/core/login/",{
        "username" : "andrew",
        "password" :  config("ANDREW_PASSWORD"),
    },follow=True)
    assert resp.content.decode() == 'success'


