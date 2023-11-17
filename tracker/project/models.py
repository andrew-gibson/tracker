import sys
from django.apps import apps
from core.utils import render,  add_to_admin, classproperty, to_dict
from core.autocomplete import AutoComplete, belongs_to, AutoCompleteNexus
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
        for attr,field in self.fields.items():
            setattr(field, "request", self.request)
            setattr(field.widget, "request", self.request)
            if hasattr(field.widget, "a_c"):
                setattr(field.a_c, "request", self.request)
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
            fields=getattr(cls,"form_fields",cls._Form._meta.fields),
            field_classes=getattr(cls, "field_classes", {}),
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


class Tag(RESTModel,AutoComplete("#", "ffbe0b")):
    form_fields = [
        "name",
    ]

    name = CharField(max_length=100)

    def __str__(self):
        return self.name


class Team(RESTModel, AutoComplete("*","fb5607")):
    form_fields = ["name", "internal"]

    @classmethod
    def belongs_to_user(cls, request):
        q = Q(project__users=request.user, private=True) | Q(private=False)
        return cls.objects.filter(q)

    users = None
    name = CharField(max_length=255,unique=True)
    projects = ManyToManyField("Project", through="ProjectTeam")
    private =  BooleanField(default=False)
    internal = BooleanField(default=False)

    def __str__(self):
        return self.name


class Contact(RESTModel, AutoComplete("@","ff006e")):
    form_fields = ["name", "email"]

    name = CharField(max_length=255)
    email = EmailField()

    def __str__(self):
        return self.name


class Project(RESTModel, AutoComplete("^", "8338ec"), AutoCompleteNexus):

    class _Form(RequestForm):

        class Meta:
            fields = ["name", "parent_project", "teams", "tags", "text"]

        def __init__(self,*args,**kwargs):
            super().__init__(*args, **kwargs)
            self.fields["parent_project"].queryset = self.fields["parent_project"].queryset.exclude(pk=self.instance.pk)
            self.fields["parent_project"].widget.attrs["class"] = "form-control"

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
