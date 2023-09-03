import sys

import faker
import pytest
from decouple import config
from django.test import TestCase

from .models import EXCompetency, Project, User

pytestmark = pytest.mark.django_db
fake = faker.Faker()

def test_user_login(client):
    resp = client.post("/core/login/",{
        "username" : "andrew",
        "password" :  config("ANDREW_PASSWORD"),
    },follow=True)
    assert resp.content.decode() == 'success'


