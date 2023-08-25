import random

import faker
import pytest
from decouple import config
from django.test import TestCase

from .models import Contact, Event, EventLog, Project, Tag, Team

fake = faker.Faker()


def test_project_create(transactional_db, client):
    Team.objects.bulk_create([Team(name=fake.name()) for x in range(10)])
    Tag.objects.bulk_create([Tag(name=fake.name()) for x in range(10)])
    Contact.objects.bulk_create(
        [Contact(name=fake.name(), email=fake.email()) for x in range(10)]
    )
    projects = [
        Project(
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


    
