import re
import sys
import uuid
from datetime import date
from itertools import product

import dateparser
from core.core import AutoCompleteNexus, AutoCompleteCoreModel, RequestForm, CoreModel
from core.models import Group, User

from core.utils import add_to_admin, classproperty, render

from django.contrib.auth.models import UserManager, GroupManager
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
    JSONField,
    OneToOneField,
    ForeignKey,
    DecimalField,
    PositiveIntegerField,
    ManyToManyField,
    Model,
    Manager,
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
from core.lang import  resolve_field_to_current_lang

''' 
1- tool for managers
2- employees can ttack hours worked against all the projects that they are assigned to
    a- can they search up extra projects?
3-contacts belong to a team
4-teams (groups) are universal
5-staff can
    - more contacts between teams
    - create new teams
6 tags 
    - can be public
    - mostly belong to a team
7- Andrew - director    manages: PHDSS part_of: DMIA
    Hanah - manager      manages: science part_of: PHDSS
        Robyn            manages:  part_of: science
    Darren - manager   manages: services part_of: PHDSS
        Caroline       manages:  part_of: services
    Jsoh                manages:  part_of: PHDSS


'''

class ProjectGroupManager(GroupManager):

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(app="project")
        )

    def user_get(self,request,*args,**kwargs):
        try:
            return self.get(*args,**kwargs)
        except self.model.DoesNotExist:
            raise Http404("cannot find requested object")

    def user_filter(self, request):
        return self.filter()

    def user_delete(self,request,*args,**kwargs):
        try:
            obj =  self.get(*args,**kwargs)
            if request.user.is_staff:
                obj.delete()
            else:
                raise Http404("Cannot delete this object")
        except self.model.DoesNotExist:
            raise Http404("cannot find requested object")

class ProjectGroup(Group):
    objects = ProjectGroupManager()
    spec = producers.projectgroup_spec
    form_fields = ["name_en",]

    class Meta:
        proxy = True

    @classmethod
    def user_filter(cls, request):
        return cls.objects.filter(app="project",system=False)

    def can_i_delete(self, request):
        return request.user.is_staff

    def add_user(self,request):
        self.save()

    def save(self,*args,**kwargs):
        self.app = self.__class__._meta.app_label
        super().save(*args,**kwargs)


class GroupPrefetcherManager(UserManager):
    use_for_related_fields = True

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .prefetch_related("groups")
            .prefetch_related("projects")
        )

class ProjectUser(User):

    class Meta:
        proxy = True

    objects = GroupPrefetcherManager()


@add_to_admin
class Contact(AutoCompleteCoreModel, trigger="@", hex_color="ff006e"):
    spec = producers.contact_spec
    form_fields = ["name", "email"]

    class adminClass(admin.ModelAdmin):
        list_display = ("name", "email","account")
        list_editable = ("email","account")

    def can_i_delete(self, request):
        return request.user.is_staff

    group = ForeignKey(ProjectGroup, blank=True,on_delete=PROTECT, related_name="contacts")
    name = CharField(max_length=255)
    email = EmailField(null=True, blank=True)
    account = OneToOneField(
        User,
        null=True,
        blank=True,
        on_delete=SET_NULL,
        related_name="contact",
    )

class Settings(CoreModel):

    class _Form(RequestForm):
        class Meta:
            fields = ["hide_done", "id"]

        def save(self, *args, **kwargs):
            self.instance.user = self.request.user
            super().save(*args, **kwargs)

    spec = ["hide_done","see_all_projects", "id", producers.__type__]
    form_fields = ["user", "hide_done"]
    user = OneToOneField(
        ProjectUser, on_delete=CASCADE,  blank=True
    )
    hide_done = BooleanField(default=False, blank=True)
    see_all_projects = BooleanField(default=True, blank=True)
    projects_filter = JSONField(db_default="{}")

    @classmethod
    def user_filter(cls, request):
        return cls.objects.filter(user=request.user)


@add_to_admin
class EXCompetency(AutoCompleteCoreModel, trigger="`", hex_color="2c6e49"):

    form_fields = ["name_en","name_fr"]

    @classmethod
    def user_filter(cls, request):
        return cls.objects.all()

    def can_i_delete(self, request):
        return False

    def __str__(self):
        return self.name_en

    spec = producers.basic_spec
    name_en = CharField(max_length=300, unique=True)
    name_fr = CharField(max_length=300, null=True,blank=True)


@add_to_admin
class ProjectStatus(AutoCompleteCoreModel, hex_color="8e6bc7"):

    form_fields = ["name_en","name_fr"]

    class Meta:
        verbose_name_plural = "Statuses"
        verbose_name = "Status"

    class adminClass(admin.ModelAdmin):
        list_display = ("id", "name_en")
        list_editable = ("name_en",)

    @classmethod
    def user_filter(cls, request):
        return cls.objects.all()

    def can_i_delete(self, request):
        return False

    def __str__(self):
        return self.name_en

    spec = producers.basic_spec
    name_en = CharField(max_length=300, unique=True)
    name_fr = CharField(max_length=300, null=True,blank=True)

@add_to_admin
class Tag(AutoCompleteCoreModel, trigger="#", hex_color="ffbe0b"):

    class adminClass(admin.ModelAdmin):
        list_display = ("id", "name", "public", "group")
        list_editable = ("name", "public", "group")
        list_filter = ("public", "group")
        search_fields = ("name",)

    spec = producers.tag_spec
    form_fields = ["name", "public"]

    @classmethod
    def user_filter(cls, request):
        filters = cls.get_filters(request)
        q = Q(group__in=request.user.groups.all()) | Q(public=True)
        return cls.objects.filter(q).filter(filters).distinct()

    def can_i_delete(self, request):
        return self.group in request.user.groups.all()

    def __str__(self):
        return self.name

    group = ForeignKey(ProjectGroup, blank=True,on_delete=PROTECT, related_name="tags")
    name = CharField(max_length=100)
    public = BooleanField(db_default=False)



@add_to_admin
class Project(AutoCompleteNexus, AutoCompleteCoreModel, trigger="^", hex_color="8338ec"):
    spec = producers.project_spec

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

        def save(self,*args,**kwargs):
            ## ensure if project has been set to private, use the request.user to set the private owner
            if self.cleaned_data["private"]:
                self.instance.private_owner = self.request.user
            else:
                self.instance.private_owner = None
            super().save(*args,**kwargs)

    @classmethod
    def get_autocompletes(cls, excludes=None):
        return [
            x for x in super().get_autocompletes(excludes) if x.related_model != Stream
        ]

    @classmethod
    def user_filter(cls, request):
        filters = cls.get_filters(request)
        return (
            cls.objects
              .filter(group__in=request.user.groups.all())
              .filter(filters)
              .exclude(Q(private=True) & ~Q(private_owner=request.user))  
        )

    @hook(AFTER_CREATE)
    def add_default_stream(self):
        self.streams.create(name="New", project_default=True)
        ProjectLog(project=self).save()

    @property
    def default_stream(self):
        return self.streams.get(project_default=True)

    def __str__(self):
        return f'{self.pk}-{self.name_en}'


    def am_i_viewer(self, request):
        return {
            "selected": request.user in self.viewers.all() or self.group in request.user.groups.all(),
            "url": reverse(
                "core:toggle_link",
                kwargs={
                    "m1": self._meta.label,
                    "pk1": self.id,
                    "m2": Contact._meta.label,
                    "pk2": request.user.id,
                    "attr": "viewers",
                },
            ),
        }

    group = ForeignKey(ProjectGroup, blank=True,on_delete=PROTECT, related_name="projects")
    status = ForeignKey(ProjectStatus,blank=True,on_delete=SET_NULL,null=True)
    addstamp = DateTimeField(null=True)
    name_en = CharField(max_length=255)
    name_fr = CharField(max_length=255,null=True,blank=True)
    text_en = TextField(blank=True, null=True)
    text_fr = TextField(blank=True, null=True)
    parent_project = ForeignKey(
        "self",
        on_delete=SET_NULL,
        null=True,
        blank=True,
        related_name="sub_projects",
    )
    leads = ManyToManyField(Contact, blank=True)
    teams = ManyToManyField(ProjectGroup, related_name="projects_supporting")
    tags = ManyToManyField(Tag)
    private = BooleanField(db_default=False)
    private_owner = ForeignKey(ProjectUser, related_name="private_projects",null=True, blank=True,on_delete=SET_NULL)
    viewers = ManyToManyField(ProjectUser, related_name="projects", blank=True)
    short_term_outcomes = TextField(blank=True, null=True) 
    long_term_outcomes = TextField(blank=True, null=True) 


class ProjectLog(CoreModel):
    spec = producers.projectlog_spec
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
    spec = producers.projectlogentry_spec
    form_fields = ["log", "text"]

    class Meta:
        ordering = ("-addstamp",)

    @classmethod
    def user_filter(cls, request):
        filters = cls.get_filters(request)
        return cls.objects.filter(
            log__project__group__in=request.user.groups.all()
        ).filter(filters)

    text = TextField(blank=True)
    addstamp = DateTimeField(auto_now_add=True)
    editstamp = DateTimeField(auto_now=True)
    log = ForeignKey(ProjectLog, on_delete=CASCADE, related_name="entries")


@add_to_admin
class Stream(AutoCompleteCoreModel, trigger="~", hex_color="036666"):
    spec = producers.stream_spec

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
    def ac_query(cls, request, query):
        if query == "":
            q = Q()
        elif query.endswith(" "):
            name = resolve_field_to_current_lang("name")
            q = Q(**{f"{name}__iexact": query.strip()})
        else:
            q = Q(name__icontains=query) | Q(project__name__icontains=query)

        return cls.user_filter(request).filter(q).distinct()

    def __str__(self):
        return f"{self.pk}-{self.name_en}"

    project = ForeignKey(Project, on_delete=CASCADE, related_name="streams")
    project_default = BooleanField(default=False)
    name_en = CharField(max_length=300)
    name_fr = CharField(max_length=300,null=True, blank=True)


class Task(CoreModel, AutoCompleteNexus):
    spec = producers.task_spec

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

    order = PositiveIntegerField(null=True)
    project = ForeignKey(Project, on_delete=CASCADE, related_name="tasks")
    stream = ForeignKey(Stream, on_delete=PROTECT, blank=True, related_name="tasks")
    start_date = DateField(default=date.today, blank=True, null=True)
    target_date = DateField(blank=True, null=True)
    name_en = CharField(max_length=255)
    name_fr = CharField(max_length=255, null=True,blank=True)
    text_en = TextField(blank=True, null=True)
    text_fr = TextField(blank=True, null=True)
    lead = ForeignKey(Contact, on_delete=SET_NULL, null=True, blank=True)
    teams = ManyToManyField(ProjectGroup, blank=True)
    addstamp = DateTimeField(auto_now_add=True)
    editstamp = DateTimeField(auto_now=True)
    competency = ForeignKey(EXCompetency, on_delete=PROTECT, null=True, blank=True)
    done = BooleanField(db_default=False, blank=True)

    def __str__(self):
        return self.name


class TimeReport(CoreModel):

    user = ForeignKey("core.User", null=True, on_delete=SET_NULL)
    project = ForeignKey(Project, on_delete=CASCADE)
    time = DecimalField(max_digits=5, decimal_places=1)
    week = DateField()
