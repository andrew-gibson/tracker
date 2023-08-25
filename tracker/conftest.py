import pytest
from django.core.management import call_command


@pytest.fixture(scope='session')
def load_fixture(name):
    with django_db_blocker.unblock():
        call_command('loaddata', name)
