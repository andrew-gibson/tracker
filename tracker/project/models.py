import re
import sys
import uuid
from datetime import date, datetime, timedelta
from itertools import product

import dateparser
from core.core import AutoCompleteNexus, AutoCompleteCoreModel, RequestForm, CoreModel
from core.models import Group, User,  GroupPrefetcherManager

from core.utils import add_to_admin, classproperty, render

from django.contrib.auth.models import UserManager, GroupManager
from django.apps import apps
from django.contrib import admin
from django.core.validators import MinValueValidator
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
    JSONField,
    OneToOneField,
    ForeignKey,
    DecimalField,
    PositiveIntegerField,
    ManyToManyField,
    Model,
    Manager,
    Q,
    Value,
    F,
    Count,
    TextField,
)
from django.db.models.functions import Concat, Replace
from django.http import QueryDict
from django.urls import reverse
from django_lifecycle import (
    AFTER_CREATE,
    BEFORE_CREATE,
    BEFORE_DELETE,
    BEFORE_UPDATE,
    BEFORE_SAVE,
    hook,
)
from . import queries
from core.lang import resolve_field_to_current_lang


class ProjectGroupManager(GroupManager):

    def get_queryset(self):
        return (
            super().get_queryset()
            .filter(app="project")
            .annotate( name_count_en=Concat(
                Replace(F("name_en"), Value("_"), Value(" ")),
                Value(" ("),
                Count("projects"),
                Value(")"),
                output_field=CharField()
            ))
            .annotate( name_count_fr=Concat(
                Replace(F("name_fr"), Value("_"), Value(" ")),
                Value(" ("),
                Count("projects"),
                Value(")"),
                output_field=CharField()
            ))
        )


    def user_filter(self, request):
        return self.filter()



class ProjectGroup(Group):
    objects = ProjectGroupManager()
    spec = queries.projectgroup_spec
    form_fields = [
        "name_en",
    ]

    class Meta:
        proxy = True

    @classmethod
    def user_filter(cls, request):
        return cls.objects.filter(app="project", system=False)


    def save(self, *args, **kwargs):
        self.app = self.__class__._meta.app_label
        super().save(*args, **kwargs)


    def add_user_and_save(self,request):
        self.save()
        request.project_user.groups.add(self)

class GroupPrefetcherManager(UserManager):
    use_for_related_fields = True

    def user_filter(self, request):
        return self.filter()

@add_to_admin
class ProjectUser(User, AutoCompleteCoreModel, trigger="@", hex_color="ff006e",search_field="username"):
    objects = GroupPrefetcherManager()
    spec = queries.projectuser_spec
    proxy_map = {
        "belongs_to" : ProjectGroup
    }

    class Meta:
        proxy = True

    @hook(BEFORE_SAVE)
    def force_no_password_no_active(self):
        if not self.password:
            self.is_active = False

    @property
    def blah(self):
        return reverse("core:main", kwargs={"m": self._meta.label, "pk": self.id})

class Settings(CoreModel):

    class _Form(RequestForm):
        class Meta:
            fields = ["hide_done", "id"]

        def save(self, *args, **kwargs):
            self.instance.user = self.request.user
            super().save(*args, **kwargs)

    spec = ["hide_done", "see_all_projects", "id", "work_hours", *queries.__core_info__]
    form_fields = ["user", "hide_done"]
    user = OneToOneField(ProjectUser, on_delete=CASCADE, blank=True, related_name="+")
    hide_done = BooleanField(default=False, blank=True)
    see_all_projects = BooleanField(default=True, blank=True)
    work_hours = DecimalField(max_digits=5, decimal_places=1,validators=[MinValueValidator(0)],db_default=37.5)
    projects_filter = JSONField(db_default="{}")

    @classmethod
    def user_filter(cls, request):
        return cls.objects.filter(user=request.user)


@add_to_admin
class EXCompetency(AutoCompleteCoreModel, trigger="`", hex_color="2c6e49"):

    form_fields = ["name_en", "name_fr"]

    @classmethod
    def user_filter(cls, request):
        return cls.objects.all()


    def __str__(self):
        return self.name_en

    spec = queries.basic_spec
    name_en = CharField(max_length=300, unique=True)
    name_fr = CharField(max_length=300, null=True, blank=True)


@add_to_admin
class ProjectStatus(AutoCompleteCoreModel, hex_color="8e6bc7"):

    form_fields = ["name_en", "name_fr"]

    class Meta:
        verbose_name_plural = "Statuses"
        verbose_name = "Status"

    class adminClass(admin.ModelAdmin):
        list_display = ("id", "name_en")
        list_editable = ("name_en",)

    @classmethod
    def user_filter(cls, request):
        return cls.objects.all()


    def __str__(self):
        return self.name_en

    spec = queries.basic_spec
    name_en = CharField(max_length=300, unique=True)
    name_fr = CharField(max_length=300, null=True, blank=True)


@add_to_admin
class Tag(AutoCompleteCoreModel, trigger="#", hex_color="ffbe0b"):

    class adminClass(admin.ModelAdmin):
        list_display = ("id", "name", "public", "group")
        list_editable = ("name", "public", "group")
        list_filter = ("public", "group")
        search_fields = ("name",)

    spec = queries.tag_spec
    form_fields = ["name", "public"]

    @classmethod
    def user_filter(cls, request):
        filters = cls.get_filters(request)
        q = Q(group__in=request.user.groups.all()) | Q(public=True)
        return cls.objects.filter(q).filter(filters).distinct()


    def __str__(self):
        return self.name

    group = ForeignKey(ProjectGroup, blank=True, on_delete=PROTECT, related_name="tags")
    name = CharField(max_length=100)
    public = BooleanField(db_default=False)


@add_to_admin
class Project(
    AutoCompleteNexus, AutoCompleteCoreModel, trigger="^", hex_color="8338ec"
):
    spec = queries.project_spec

    class Meta:
        ordering = ("name_en",)

    class adminClass(admin.ModelAdmin):
        list_display = ("id", "name_en", "group", "status")
        list_editable = ("name_en", "group", "status")
        list_filter = ("status", "group")
        search_fields = ("name_en",)

    class _Form(RequestForm):
        class Meta:
            fields = [
                "name_en",
                "name_fr",
                "parent_project",
                "text_en",
                "text_fr",
                "private",
            ]

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.fields["parent_project"].queryset = self.fields[
                "parent_project"
            ].queryset.exclude(pk=self.instance.pk)
            self.fields["parent_project"].widget.attrs["class"] = "form-control"

        def save(self, *args, **kwargs):
            ## ensure if project has been set to private, use the request.user to set the private owner
            if self.cleaned_data["private"]:
                self.instance.private_owner = self.request.user
            else:
                self.instance.private_owner = None
            super().save(*args, **kwargs)

    @classmethod
    def get_autocompletes(cls, excludes=None):
        return [
            x for x in super().get_autocompletes(excludes) if x.related_model != Stream
        ]

    @classmethod
    def user_filter(cls, request):
        filters = cls.get_filters(request)
        q1 = Q(group__in=request.user.groups.all())   # basic, you're in the group where the project is hosted
        q2 = Q(viewers=request.project_user) # you've opted to follow this project
        q3 = Q(leads=request.project_user) # you've been assinged as the lead of hte project'
        q4 = Q(timereports__user=request.project_user) # you've entered a time report'
        q5 =  Q(private=True) & ~Q(private_owner=request.user)
        return (
            cls.objects.filter(q1 | q2 | q3 | q4)
            .filter(filters)
            .exclude(q3)
        ).distinct()

    @hook(AFTER_CREATE)
    def add_default_stream(self):
        self.streams.create(name="New", project_default=True)
        ProjectLog(project=self).save()

    @property
    def default_stream(self):
        return self.streams.get(project_default=True)

    def __str__(self):
        return f"{self.pk}-{self.name_en}"

    def am_i_viewer(self, request):
        return {
            "selected": request.user in self.viewers.all()
            or self.group in request.user.groups.all(),
            "__url__": reverse(
                "core:toggle_link",
                kwargs={
                    "m1": self._meta.label,
                    "pk1": self.id,
                    "m2": ProjectUser._meta.label,
                    "pk2": request.user.id,
                    "attr": "viewers",
                },
            ),
        }

    group = ForeignKey(
        ProjectGroup, blank=True, on_delete=PROTECT, related_name="projects"
    )
    status = ForeignKey(ProjectStatus, blank=True, on_delete=SET_NULL, null=True)
    addstamp = DateTimeField(null=True)
    name_en = CharField(max_length=255)
    name_fr = CharField(max_length=255, null=True, blank=True)
    text_en = TextField(blank=True, null=True)
    text_fr = TextField(blank=True, null=True)
    parent_project = ForeignKey(
        "self",
        on_delete=SET_NULL,
        null=True,
        blank=True,
        related_name="sub_projects",
    )
    leads = ManyToManyField(ProjectUser, blank=True)
    teams = ManyToManyField(ProjectGroup, related_name="projects_supporting", blank=True)
    tags = ManyToManyField(Tag)
    private = BooleanField(db_default=False)
    private_owner = ForeignKey(
        ProjectUser,
        related_name="private_projects",
        null=True,
        blank=True,
        on_delete=SET_NULL,
    )
    viewers = ManyToManyField(ProjectUser, related_name="projects", blank=True)
    short_term_outcomes = TextField(blank=True, null=True)
    long_term_outcomes = TextField(blank=True, null=True)

class MinProject(Project):
    spec = queries.min_project_spec

    class Meta:
        proxy = True

    @classmethod
    def user_filter(cls, request):
        return  Project.user_filter(request)

class ProjectLog(CoreModel):
    spec = queries.projectlog_spec
    form_fields = ["project"]

    @classmethod
    def user_filter(cls, request):
        filters = cls.get_filters(request)
        return cls.objects.filter(project__group__in=request.user.groups.all()).filter(
            filters
        )

    @property
    def id(self):
        return self.project.id

    project = OneToOneField(Project, on_delete=CASCADE, related_name="log")


class ProjectLogEntry(CoreModel):
    spec = queries.projectlogentry_spec
    form_fields = ["log", "text"]

    class Meta:
        ordering = ("-addstamp",)

    @classmethod
    def user_filter(cls, request):
        filters = cls.get_filters(request)
        return cls.objects.filter(
            log__project__group__in=request.user.groups.all()
        ).filter(filters)

    def add_user_and_save(self, request):
        self.user = request.user
        self.save()

    text = TextField(blank=True)
    addstamp = DateTimeField(auto_now_add=True)
    editstamp = DateTimeField(auto_now=True)
    user = ForeignKey(ProjectUser, on_delete=CASCADE, related_name="log_entries")
    log = ForeignKey(ProjectLog, on_delete=CASCADE, related_name="entries")


@add_to_admin
class Stream(AutoCompleteCoreModel, trigger="~", hex_color="036666"):
    spec = queries.stream_spec

    class Meta:
        ordering = ("id",)
        unique_together = ("name_en", "project")

    form_fields = [
        "name_en",
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
    def user_filter(cls, request):
        filters = cls.get_filters(request)
        return cls.objects.filter(project__group__in=request.user.groups.all()).filter(
            filters
        )

    @classmethod
    def ac_query(cls, request, query,requestor):
        if query == "":
            q = Q()
        elif query.endswith(" "):
            name = resolve_field_to_current_lang("name")
            q = Q(**{f"{name}__iexact": query.strip()})
        else:
            q = Q(name__icontains=query) | Q(project__name__icontains=query)

        if isinstance(requestor, Task):
            q = q & Q(project=requestor.project) 

        return cls.user_filter(request).filter(q).distinct()

    def __str__(self):
        return f"{self.pk}-{self.name_en}"

    project = ForeignKey(Project, on_delete=CASCADE, related_name="streams")
    project_default = BooleanField(default=False)
    name_en = CharField(max_length=300)
    name_fr = CharField(max_length=300, null=True, blank=True)


class Task(AutoCompleteCoreModel, AutoCompleteNexus):
    spec = queries.task_spec

    class Meta:
        ordering = ["done", "order", "start_date"]

    form_fields = [
        "order",
        "stream",
        "start_date",
        "target_date",
        "name_en",
        "name_fr",
        "text_en",
        "text_fr",
        "done",
    ]

    @classmethod
    def user_filter(cls, request):
        filters = cls.get_filters(request)
        return cls.objects.filter(project__group__in=request.user.groups.all()).filter(
            filters
        )


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
        if not getattr(self, "stream", False):
            self.stream = self.project.default_stream
        last_in_order = self.stream.tasks.order_by("order").last()
        if last_in_order and last_in_order.order:
            self.order = last_in_order.order + 1
        else:
            self.order = 1

    def __str__(self):
        return f"{self.pk}-{self.name_en}"

    order = PositiveIntegerField(null=True, blank=True)
    project = ForeignKey(Project, on_delete=CASCADE, related_name="tasks")
    stream = ForeignKey(Stream, on_delete=PROTECT, blank=True, related_name="tasks")
    start_date = DateField(default=date.today, blank=True, null=True)
    target_date = DateField(blank=True, null=True)
    name_en = CharField(max_length=255)
    name_fr = CharField(max_length=255, null=True, blank=True)
    text_en = TextField(blank=True, null=True)
    text_fr = TextField(blank=True, null=True)
    lead = ForeignKey(ProjectUser, on_delete=SET_NULL, null=True, blank=True)
    teams = ManyToManyField(ProjectGroup, blank=True)
    addstamp = DateTimeField(auto_now_add=True)
    editstamp = DateTimeField(auto_now=True)
    competency = ForeignKey(EXCompetency, on_delete=PROTECT, null=True, blank=True)
    done = BooleanField(db_default=False, blank=True)



class TimeReport(CoreModel):

    spec = queries.time_report

    class _Form(RequestForm):
        class Meta:
            fields = [
        "project",
        "time",
        "week",
    ]

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

        def save(self, *args, **kwargs):
            super().save(*args, **kwargs)

    @classmethod
    def user_filter(cls, request):
        filters = cls.get_filters(request)
        return cls.objects.filter(user=request.user).filter(filters)

    @hook(BEFORE_SAVE)
    def force_start_of_week(self):
        self.week = self.week - timedelta(days=self.week.weekday())

    def add_user_and_save(self,request):
        self.user = request.user
        self.save()

    user = ForeignKey(ProjectUser, null=True, on_delete=SET_NULL)
    project = ForeignKey(Project, on_delete=CASCADE,related_name="timereports")
    time = DecimalField(max_digits=5, decimal_places=1,validators=[MinValueValidator(0)])
    text = TextField(blank=True)
    week = DateField()
