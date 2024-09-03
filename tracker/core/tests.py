import sys

import faker
import pytest
from decouple import config
from django.test import TestCase


#@pytest.mark.django_db
#def test_user_login(client, load_fixture):
#    resp = client.post("/core/login/",{
#        "username" : "andrew",
#        "password" :  config("ANDREW_PASSWORD"),
#    },follow=True)
#    assert resp.content.decode() == 'success'


