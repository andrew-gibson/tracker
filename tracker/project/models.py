import sys
from django.apps import apps
from core.utils import render, belongs_to, add_to_admin, classproperty, to_dict
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
    TextField,
    Q,
)
from django.forms import ModelForm, modelform_factory
from django.http import QueryDict
from django.urls import reverse


class RequestForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            setattr(field.widget, "request", self.request)
            if hasattr(field.widget, "a_c"):
                setattr(field.widget.a_c, "request", self.request)


class RESTModel(Model, belongs_to):
    class Meta:
        abstract = True

    users = ManyToManyField("core.User")

    @classproperty
    def _name(cls):
        return f"{cls.__name__.lower()}"

    _Form = RequestForm

    @classmethod
    def form(cls, request):
        Form = modelform_factory(
            cls,
            form=cls._Form,
            fields=cls.form_fields,
            widgets=getattr(cls, "form_widgets", {}),
        )
        Form.request = request
        return Form

    @classmethod
    def POST(cls, request):
        form = cls.form(request)(request.POST)
        context = {"form": form}
        if form.is_valid():
            inst = form.save()
            context["inst"] = inst
            # by default associate objects with their creator
            if getattr(inst, "users", False):
                inst.users.add(request.user)
        else:
            context["inst"] = form.instance
        return render(
            request,
            f"{cls._name}/{cls._name}.html",
            context,
        )

    @classmethod
    def PUT(cls, request, pk):
        inst = cls.belongs_to_user(request).get(pk=pk)
        put = QueryDict(request.PUT)
        form = cls.form(request)(put, instance=inst)
        context = {"form": form}
        if form.is_valid():
            inst = form.save()
            context["inst"] = inst
        return render(
            request,
            f"{cls._name}/{cls._name}.html",
            context,
        )

    @classmethod
    def GET(cls, request, pk=None):
        if pk:
            inst = cls.belongs_to_user(request).get(pk=pk)
            form = cls.form(request)(instance=inst)
            return render(
                request,
                f"{cls._name}/{cls._name}.html",
                {"inst": inst, "form": form},
            )
        else:
            return render(
                request,
                f"{cls._name}/{cls._name}s.html",
                {"insts": [p for p in cls.belongs_to_user(request)]},
            )

    @classmethod
    def DELETE(cls, request, pk):
        qs = cls.belongs_to_user(request).filter(pk=pk)
        if qs.count() == 1:
            qs.delete()
        return render(
            request,
            f"{cls._name}/{cls._name}s.html",
            {f"{cls._name}": [p for p in cls.belongs_to_user(request)]},
        )

    @classmethod
    def belongs_to_user(cls, request):
        return cls.objects.filter(users=request.user)

    def get_absolute_url(self):
        return reverse(
            "project:project", kwarg={"modelname": self._name(), "pk": self.pk}
        )


class EXCompetency(Model):
    name = CharField(max_length=300, unique=True)


class Tag(RESTModel):
    form_fields = [
        "name",
    ]

    text_search_trigger = "#"

    @classmethod
    def ac(cls, request, query="", variant=None):
        if not isinstance(query,(tuple,list)):
            query = [query]
        q = Q()
        for _ in query:
            q.add(Q(name__icontains=_), Q.OR)
        print(q)
        return [
                to_dict(x, field_list=["name","id"])
                for x in cls.belongs_to_user(request).filter(q).distinct()
                ]

    name = CharField(max_length=100)

    def __str__(self):
        return self.name


def make_get_items(cls):
    def get_items(self, search=None, values=None):
        nonlocal cls
        if isinstance(cls, str):
            cls = apps.get_model(cls)
        if search is not None:
            items = [
                {"label": str(x), "value": str(x.id)}
                for x in cls.belongs_to_user(self.request)
                if search == "" or str(search).upper() in f"{x}".upper()
            ]
            return items
        if values is not None and len(values) != 0:
            items = [
                {"label": str(x), "value": str(x.id)}
                for x in cls.belongs_to_user(self.request)
                if str(x.id) in values
            ]
            return items

        return []

    return get_items


class Team(RESTModel):
    form_fields = ["name", "internal"]

    name = CharField(max_length=255)
    projects = ManyToManyField("Project", through="ProjectTeam")
    internal = BooleanField(default=False)

    def __str__(self):
        return self.name


class Contact(RESTModel):
    form_fields = ["name", "email"]

    name = CharField(max_length=255)
    email = EmailField()

    def __str__(self):
        return self.name


class Project(RESTModel):
    form_fields = ["name", "parent_project", "teams", "tags", "text"]

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

    def __str__(self):
        return self.name


class Theme(RESTModel):
    form_fields = [
        "name",
        "project",
    ]

    @classmethod
    def belongs_to_user(cls, request):
        return cls.objects.filter(project__users=request.user)

    users = None
    project = ForeignKey(Project, on_delete=CASCADE, related_name="themes")
    name = CharField(max_length=300)


class ThemeWork(RESTModel):
    form_fields = [
        "theme",
        "target_date",
        "name",
        "text",
        "lead",
        "teams",
        "competency",
    ]

    @classmethod
    def belongs_to_user(cls, request):
        return cls.objects.filter(theme__project__users=request.user)

    users = None
    theme = ForeignKey(Theme, on_delete=CASCADE, related_name="work_details")
    target_date = DateTimeField()
    name = CharField(max_length=255)
    text = TextField()
    lead = ForeignKey(Contact, on_delete=SET_NULL, null=True)
    teams = ManyToManyField(Team, blank=True)
    addstamp = DateTimeField(auto_now_add=True)
    editstamp = DateTimeField(auto_now=True)
    competency = ForeignKey(EXCompetency, on_delete=PROTECT, null=True, blank=True)

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
