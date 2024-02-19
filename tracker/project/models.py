import re
import sys
import uuid
from datetime import date
from itertools import product

import dateparser
from core.rest import AutoCompleteNexus, AutoCompleteREST, RequestForm, RESTModel
from core.utils import add_to_admin, classproperty, render
from django.apps import apps
from django.db.models import (
    CASCADE,
    PROTECT,
    SET_NULL,
    BooleanField,
    CharField,
    DateField,
    DateTimeField,
    EmailField,
    ForeignKey,
    ManyToManyField,
    Model,
    Q,
    TextField,
)
from django.http import QueryDict
from django.urls import reverse
from django_lifecycle import (
    AFTER_CREATE,
    BEFORE_CREATE,
    BEFORE_DELETE,
    BEFORE_UPDATE,
    hook,
)

from . import producers


class EXCompetency(AutoCompleteREST, trigger="`", hex_color="2c6e49"):
    rest_spec = producers.basic_rest_spec
    users = None
    name = CharField(max_length=300, unique=True)
    form_fields = [ "name" ]

    @classmethod
    def belongs_to_user(cls, request):
        return cls.objects.all()


class Tag(AutoCompleteREST, trigger="#", hex_color="ffbe0b"):
    rest_spec = producers.basic_rest_spec
    form_fields = [ "name" ]
    name = CharField(max_length=100)


class Contact(AutoCompleteREST, trigger="@", hex_color="ff006e"):
    rest_spec = producers.basic_rest_spec
    form_fields = ["name", "email"]

    name = CharField(max_length=255)
    email = EmailField(null=True, blank=True)


class Team(AutoCompleteREST, trigger="*", hex_color="fb5607"):
    rest_spec = producers.basic_rest_spec
    form_fields = ["name", "internal"]

    @classmethod
    def belongs_to_user(cls, request):
        q = Q(project__users=request.user, private=True) | Q(private=False)
        return cls.objects.filter(q).distinct()

    users = None
    name = CharField(max_length=255, unique=True)
    projects = ManyToManyField("Project", through="ProjectTeam")
    private = BooleanField(db_default=True)
    internal = BooleanField(default=False)


class Project(AutoCompleteNexus, AutoCompleteREST, trigger="^", hex_color="8338ec"):
    rest_spec = producers.project_rest_spec

    class _Form(RequestForm):
        class Meta:
            fields = [
                "name",
                "parent_project",
                "teams",
                "tags",
                "text",
            ]

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.fields["parent_project"].queryset = self.fields[
                "parent_project"
            ].queryset.exclude(pk=self.instance.pk)
            self.fields["parent_project"].widget.attrs["class"] = "form-control"

    @classmethod
    def get_autocompletes(cls, excludes=None):
        return [
            x for x in super().get_autocompletes(excludes) if x.related_model != Stream
        ]

    name = CharField(max_length=255)
    text = TextField()
    parent_project = ForeignKey(
        "self",
        on_delete=SET_NULL,
        null=True,
        blank=True,
        related_name="sub_projects",
    )
    point_of_contact = ForeignKey("Contact", on_delete=SET_NULL, null=True)
    teams = ManyToManyField("Team", through="ProjectTeam")
    tags = ManyToManyField("Tag")

    @hook(AFTER_CREATE)
    def add_default_stream(self):
        self.streams.create(name="Unassigned", project_default=True)


class Stream(AutoCompleteREST, trigger="~", hex_color="036666"):
    rest_spec = producers.stream_rest_spec

    class Meta:
        unique_together = ("name", "project")

    form_fields = [
        "name",
        "project",
    ]

    @hook(BEFORE_DELETE)
    def cant_delete_only_stream(self):
        if self.project_default:
            raise Exception("Can't delete 'unassigned' Stream from project")

    @hook(BEFORE_UPDATE)
    def cant_rename_unassigned(self):
        if self.project_default:
            raise Exception("Can't rename 'unassigned'")

    @classmethod
    def belongs_to_user(cls, request):
        return cls.objects.filter(project__users=request.user)

    @classmethod
    def ac_query(cls, request, query):
        if query == "":
            q = Q()
        elif query.endswith(" "):
            q = Q(**{"name__iexact": query.strip()})
        else:
            q = Q(name__icontains=query) | Q(project__name__icontains=query)

        return cls.belongs_to_user(request).filter(q).distinct()

    users = None
    project = ForeignKey(Project, on_delete=CASCADE, related_name="streams")
    project_default = BooleanField(default=False)
    name = CharField(max_length=300)


class Task(RESTModel, AutoCompleteNexus):
    rest_spec = producers.task_rest_spec

    form_fields = [
        "stream",
        "start_date",
        "target_date",
        "name",
        "text",
        "lead",
        "teams",
        "competency",
        "done",
    ]

    @classmethod
    def belongs_to_user(cls, request):
        return cls.objects.filter(stream__project__users=request.user)

    @classmethod
    def cls_text_scan(cls, text_input, results):
        # chops up text_input and looks for combinations which get recognized as dates

        # get rid of any extra spaces and then split  by spaces into tokens
        split_text_input = re.subn(" +", " ", text_input)[0].strip().split(" ")
        l = len(split_text_input)

        # chop up the text into buncles of dates
        parsed_dates = [
            x
            for x in [
                [
                    x,  # the range number e.g. [2, 5]
                    split_text_input[x[0] : x[1] + 1],  # the fragments of text
                    dateparser.parse(
                        " ".join(split_text_input[x[0] : x[1] + 1]), languages=["en"]
                    ),  # parse the test
                ]
                for x in filter(
                    lambda x: x[0] <= x[1], product(range(l), range(l))
                )  # use product/filter to create a list of all possible ranges of text
            ]
            if x[2]
        ]

        # bail if nothing was found
        if len(parsed_dates) == 0:
            return

        # grab the last instance of the date
        date = max(parsed_dates, key=lambda x: x[0][1] + len(x[1]))

        # add the extra dictionary to results
        results["targt_date"] = {
            "trigger": uuid.uuid4().hex,
            "model": {
                "hex_trigger_color": "90e0ef",
                "trigger_color": "rgb(144,224,239)",
            },
            "attr_only": True,
            "name": "Due Date",
            "many_to_many": False,
            "search_terms": date[1],
            "results": [
                [
                    date[1],
                    [
                        {
                            "id": date[2].timestamp(),
                            "name": date[2].strftime("%a, %d %b %G"),
                            "val": date[2],
                        }
                    ],
                ]
            ],
        }

    @hook(BEFORE_CREATE)
    def assign_to_unassigned(self):
        if not self.stream:
            self.stream = self.project.streams.get(project_default=True)

    users = None
    project = ForeignKey(Project, on_delete=CASCADE, related_name="tasks")
    stream = ForeignKey(
        Stream, on_delete=PROTECT, blank=True, null=True, related_name="tasks"
    )
    start_date = DateField(default=date.today, blank=True, null=True)
    target_date = DateField(blank=True, null=True)
    name = CharField(max_length=255)
    text = TextField(blank=True)
    lead = ForeignKey(Contact, on_delete=SET_NULL, null=True, blank=True)
    teams = ManyToManyField(Team, blank=True)
    addstamp = DateTimeField(auto_now_add=True)
    editstamp = DateTimeField(auto_now=True)
    competency = ForeignKey(EXCompetency, on_delete=PROTECT, null=True, blank=True)
    done = BooleanField(db_default=False, blank=True)

    def __str__(self):
        return self.name


class ProjectTeam(RESTModel):
    @classmethod
    def belongs_to_user(cls, request):
        return cls.objects.filter(project__users=request.user)

    users = None
    project = ForeignKey("Project", on_delete=CASCADE)
    team = ForeignKey("Team", on_delete=CASCADE)
    # If needed, you can add additional fields here to capture details about the relationship, for example:
    # start_date = DateField(null=True, blank=True)
    # role = CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ["project", "team"]
