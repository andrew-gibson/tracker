import re
import sys
import uuid
from datetime import date
from itertools import product

import dateparser
from core.rest import AutoCompleteNexus, AutoCompleteREST, RequestForm, RESTModel
from core.utils import add_to_admin, classproperty, render
from django.apps import apps
from django.contrib import admin
from django.db.models import (
    CASCADE,
    PROTECT,
    SET_NULL,
    BigAutoField,
    BooleanField,
    CharField,
    DateField,
    DateTimeField,
    EmailField,
    OneToOneField,
    ForeignKey,
    DecimalField,
    PositiveIntegerField,
    ManyToManyField,
    Model,
    Q,
    TextField,
)
from django.contrib.auth.models import Group
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

class Settings(RESTModel):

    class _Form(RequestForm):
        class Meta:
            fields = [ "hide_done", "id" ]

        def save(self, *args, **kwargs):
            self.instance.user = self.request.user
            super().save(*args, **kwargs)

    group = None
    spec = ["hide_done", "id", producers.__type__]
    form_fields = [ "user", "hide_done" ]
    user = OneToOneField("core.User", on_delete=CASCADE, related_name="project_settings", blank=True)
    hide_done = BooleanField(default=False,blank=True) 

    @classmethod
    def belongs_to_user(cls, request):
        return cls.objects.filter(user=request.user)

@add_to_admin
class EXCompetency(AutoCompleteREST, trigger="`", hex_color="2c6e49"):

    @classmethod
    def belongs_to_user(cls, request):
        return cls.objects.all()

    def can_i_delete(self,request):
        return False

    def __str__(self):
        return self.name

    spec = producers.basic_spec
    group = None
    name = CharField(max_length=300, unique=True)
    form_fields = [ "name" ]

@add_to_admin
class Tag(AutoCompleteREST, trigger="#", hex_color="ffbe0b"):

    class adminClass(admin.ModelAdmin):
        list_display = ("id","name","public","group")
        list_editable = ("name","public","group")
        list_filter = ("public","group")
        search_fields = ("name",)

    spec = producers.tag_spec
    form_fields = [ "name","public" ]

    @classmethod
    def belongs_to_user(cls, request):
        filters = cls.get_filters(request)
        q = Q(group__in = request.user.groups.all()) | Q(public=True)
        return cls.objects.filter(q).filter(filters).distinct()

    def can_i_delete(self,request):
        return self.group in request.user.groups.all()

    def __str__(self):
        return self.name

    name = CharField(max_length=100)
    public = BooleanField(db_default=False)

@add_to_admin
class Contact(AutoCompleteREST, trigger="@", hex_color="ff006e"):
    spec = producers.basic_spec
    form_fields = ["name", "email"]

    name = CharField(max_length=255)
    email = EmailField(null=True, blank=True)
    account = OneToOneField("core.User",null=True, blank=True,on_delete=SET_NULL, related_name="+")

@add_to_admin
class Team(AutoCompleteREST, trigger="*", hex_color="fb5607"):
    spec = producers.team_spec
    form_fields = ["name", "public"]

    @classmethod
    def belongs_to_user(cls, request):
        filters = cls.get_filters(request)
        q = Q(group__in = request.user.groups.all()) | Q(public=True)
        return cls.objects.filter(q).filter(filters).distinct()

    def can_i_delete(self,request):
        return self.group in request.user.groups.all()

    def __str__(self):
        return self.name

    group = ForeignKey(Group, blank=True,null=True, on_delete=PROTECT)
    name = CharField(max_length=255, unique=True)
    public = BooleanField(db_default=False)


class Project(AutoCompleteNexus, AutoCompleteREST, trigger="^", hex_color="8338ec"):
    spec = producers.project_spec

    class _Form(RequestForm):
        class Meta:
            fields = [
                "name",
                "parent_project",
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

    @hook(AFTER_CREATE)
    def add_default_stream(self):
        self.streams.create(name="New", project_default=True)
        ProjectLog(project=self).save()

    @property
    def default_stream(self):
        return self.streams.get(project_default=True)

    name = CharField(max_length=255)
    text = TextField(blank=True)
    parent_project = ForeignKey(
        "self",
        on_delete=SET_NULL,
        null=True,
        blank=True,
        related_name="sub_projects",
    )
    point_of_contact = ForeignKey("Contact", on_delete=SET_NULL, null=True)
    teams = ManyToManyField("Team")
    tags = ManyToManyField("Tag")


class ProjectLog(RESTModel):
    spec = producers.projectlog_spec
    form_fields = ["project"]

    @classmethod
    def belongs_to_user(cls, request):
        filters = cls.get_filters(request)
        return cls.objects.filter(project__group__in = request.user.groups.all()).filter(filters)   

    @property
    def id(self):
        return self.project.id

    group = None
    project = OneToOneField(Project, on_delete=CASCADE, related_name="log")


class ProjectLogEntry(RESTModel):
    spec = producers.projectlogentry_spec
    form_fields = ["log","text"]

    class Meta:
        ordering = ("-addstamp",)

    @classmethod
    def belongs_to_user(cls, request):
        filters = cls.get_filters(request)
        return cls.objects.filter(log__project__group__in = request.user.groups.all()).filter(filters)   

    group = None
    text = TextField(blank=True)
    addstamp = DateTimeField(auto_now_add=True)
    editstamp = DateTimeField(auto_now=True)
    log = ForeignKey(ProjectLog, on_delete=CASCADE, related_name="entries")


class Stream(AutoCompleteREST, trigger="~", hex_color="036666"):
    spec = producers.stream_spec

    class Meta:
        ordering = ("id",)
        unique_together = ("name", "project")

    form_fields = [
        "name",
        "project",
    ]

    @hook(BEFORE_DELETE)
    def cant_delete_only_stream(self):
        if self.project_default:
            raise Exception("Can't delete 'New' Stream from project")

    @hook(BEFORE_UPDATE)
    def cant_rename_new(self):
        if self.project_default:
            raise Exception("Can't rename 'New'")

    @classmethod
    def belongs_to_user(cls, request):
        filters = cls.get_filters(request)
        return cls.objects.filter(project__group__in = request.user.groups.all()).filter(filters)   

    @classmethod
    def ac_query(cls, request, query):
        if query == "":
            q = Q()
        elif query.endswith(" "):
            q = Q(**{"name__iexact": query.strip()})
        else:
            q = Q(name__icontains=query) | Q(project__name__icontains=query)

        return cls.belongs_to_user(request).filter(q).distinct()

    def __str__(self):
        return f"{self.pk}-{self.name}"

    group = None
    project = ForeignKey(Project, on_delete=CASCADE, related_name="streams")
    project_default = BooleanField(default=False)
    name = CharField(max_length=300)


class Task(RESTModel, AutoCompleteNexus):
    spec = producers.task_spec 

    class Meta:
        ordering = ["done", "order", "start_date"]

    form_fields = [
        "order",
        "stream",
        "start_date",
        "target_date",
        "name",
        "text",
        "done",
    ]

    @classmethod
    def belongs_to_user(cls, request):
        filters = cls.get_filters(request)
        return cls.objects.filter(project__group__in = request.user.groups.all()).filter(filters)

    @classmethod
    def cls_text_scan(cls, text_input, results, triggers):
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
            "model_info": {
                "hex": "90e0ef",
                "rbga": "rgb(144,224,239)",
            },
            "attr_only": True,
            "verbose": "Due Date",
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
    def assign_to_new(self):
        if not getattr(self,"stream",False):
            self.stream = self.project.default_stream
        last_in_order = self.stream.tasks.order_by("order").last()
        if last_in_order and last_in_order.order:
            self.order =  last_in_order.order + 1
        else:
            self.order = 1

    group = None
    order = PositiveIntegerField(null=True)
    project = ForeignKey(Project, on_delete=CASCADE, related_name="tasks")
    stream = ForeignKey(
        Stream, on_delete=PROTECT, blank=True,  related_name="tasks"
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

class TimeReport(RESTModel):

    user = ForeignKey("core.User",null=True,on_delete=SET_NULL)
    project = ForeignKey(Project, on_delete=CASCADE)
    time = DecimalField(max_digits=5,decimal_places=1)
    week = DateField()
