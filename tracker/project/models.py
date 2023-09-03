from asgiref.sync import sync_to_async
from core.utils import render
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
    signals,
)
from django.forms import ModelForm, modelform_factory
from django.http import QueryDict
from django.urls import reverse

from tracker.shared import classproperty


class RequestForm(ModelForm):
    def __init__(self, *args, request=None, **kwargs):
        self.request = request
        super().__init__(*args, **kwargs)


class RESTModel(Model):
    class Meta:
        abstract = True

    users = ManyToManyField("core.User")

    @classproperty
    def _name(cls):
        return f"{cls.__name__.lower()}"

    @classmethod
    def form(cls, request):
        return modelform_factory(cls, fields=cls.form_fields)

    @classmethod
    def post(cls, request):
        form = cls.form(request)(request.POST)
        if form.is_valid():
            inst = form.save()
        # by default associate objects with their creator
        inst.users.add(request.user)
        return cls.get(request, pk=inst.pk, form=form)

    @classmethod
    def put(cls, request, pk):
        inst = cls.belongs_to_user(request).get(pk=pk)
        put = QueryDict(request.PUT)
        form = cls.form(request)(put, instance=inst)
        if form.is_valid():
            inst = form.save()

        return cls.get(request, pk=pk, form=form)

    @classmethod
    def get(cls, request, pk=None, form=None):
        if pk:
            inst = cls.belongs_to_user(request).get(pk=pk)
            if not form:
                form = cls.form(request)(instance=inst)
            return render(
                request,
                f"{cls._name}/{cls._name}.html",
                {f"{cls._name}": inst},
            )
        else:
            return render(
                request,
                f"{cls._name}/{cls._name}s.html",
                {f"{cls._name}s": [p for p in cls.belongs_to_user(request)]},
            )

    @classmethod
    def delete(cls, request, pk):
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


class Team(RESTModel):
    form_fields = ["name","internal"]

    name = CharField(max_length=255, unique=True)
    projects = ManyToManyField("Project", through="ProjectTeam")
    internal = BooleanField(default=False)

    def __str__(self):
        return self.name


class Tag(RESTModel):
    form_fields = ["name",]

    name = CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Contact(RESTModel):

    form_fields = ["name", "email"]

    name = CharField(max_length=255)
    email = EmailField(unique=True)

    def __str__(self):
        return self.name


class Project(RESTModel):
    form_fields = ["name", "parent_project", "teams", "tags"]

    name = CharField(max_length=255)
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

    def save(self, *args, **kwargs):
        new = not bool(self.pk)
        super().save(*args, **kwargs)
        if new:
            for competency in EXCompetency.objects.all():
                inst = self.theme_set.create(
                    competency=competency, name=competency.name
                )

    def __str__(self):
        return self.name


class Theme(RESTModel):
    @classmethod
    def belongs_to_user(cls, request):
        return cls.objects.filter(project__user=request.user)

    users = None
    project = ForeignKey(Project, on_delete=CASCADE)
    competency = ForeignKey(EXCompetency, on_delete=PROTECT, null=True)
    name = CharField(max_length=300)


class SubTheme(RESTModel):
    @classmethod
    def belongs_to_user(cls, request):
        return cls.objects.filter(theme__project__user=request.user)

    users = None
    theme = ForeignKey(Theme, on_delete=CASCADE)
    name = CharField(max_length=300)


class _WorkLine(RESTModel):
    form_fields = ["parent", "target_date", "title", "text", "lead", "teams"]

    class Meta:
        abstract = True

    target_date = DateTimeField()
    title = CharField(max_length=255)
    text = TextField()
    lead = ForeignKey(Contact, on_delete=SET_NULL, null=True)
    teams = ManyToManyField(Team)
    addstamp = DateTimeField(auto_now_add=True)
    editstamp = DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class ThemeWork(_WorkLine):

    @classmethod
    def belongs_to_user(cls, request):
        return cls.objects.filter(parent__project__users=request.user)

    parent = ForeignKey(Theme, on_delete=CASCADE, related_name="work_details")


class SubThemeWork(_WorkLine):

    @classmethod
    def belongs_to_user(cls, request):
        return cls.objects.filter(parent__theme__project__users=request.user)

    parent = ForeignKey(SubTheme, on_delete=CASCADE, related_name="work_details")


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
