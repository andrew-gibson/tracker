import markdown
from django.apps import apps
from django.db.models import CharField, Value, Q, Count, CharField, F
from django.db.models.functions import Concat, Replace
from django_readers import qs, pairs, projectors, producers, specs
from core.lang import lang,resolve_field_to_current_lang
from . import permissions


def lang_field(field):
    return {field: f"{field}_{lang()}"}


def render_markdown(attr):
    prepare = qs.include_fields(attr)

    def produce(inst):
        return markdown.markdown(getattr(inst, attr) or "")

    return prepare, produce


def count(attr):
    prepare = qs.include_fields(attr)

    def produce(inst):
        return getattr(inst, attr).count()

    return prepare, produce


def can_delete(user, *attrs):
    if attrs:
        prepare = qs.include_fields(*attrs)
    else:
        prepare = qs.noop

    def produce(inst):
        return permissions.good_request(user, "DELETE", inst)

    return prepare, produce


def programuser_projects():
    prepare = qs.include_fields(
        "projects",
    )


def name_task_count():
    return (
        qs.annotate(
            name_count=Concat(
                Replace(F(f"name_{lang()}"), Value("_"), Value(" ")),
                Value(" ("),
                Count("tasks", filter=Q(tasks__done=False)),
                Value(")"),
                output_field=CharField(),
            )
        ),
        producers.attr("name_count"),
    )

__type__ = {"__type__": (qs.noop, producers.attrgetter("_meta.label"))}

def force_type(model):
    m = apps.get_model(model)

    def produce(inst):
        return m._meta.label

    return {"__type__": (qs.noop, produce)}


def basic_spec(cls, request, pk=None):
    return [
        lang_field("name"),
        "id",
        __type__,
    ]


def projectuser_spec(cls, request, pk=None):
    spec = (
        "id",
        "username",
        {
            "belongs_to": [
                force_type("project.ProjectGroup"),
                lang_field("name"),
                "id",
            ]
        },
        {
            "manages": [
                force_type("project.ProjectGroup"),
                lang_field("name"),
                "id",
                {
                    "users": [
                        pairs.exclude(pk=request.user.pk),
                        force_type("project.ProjectUser"),
                        {"name": "username"},
                        "id",
                    ]
                },
            ]
        },
        {"groups": ["id", lang_field("name"), force_type("project.ProjectGroup")]},
    )
    return spec


def task_spec(cls, request, pk=None):
    return [
        __type__,
        "id",
        "order",
        lang_field("text"),
        lang_field("name"),
        {"project": [__type__, "id", lang_field("name")]},
        {"stream": [__type__, "id", lang_field("name")]},
        "start_date",
        "target_date",
        {"lead": [__type__, "id", "name"]},
        {"teams": [__type__, "id", lang_field("name")]},
        {"competency": [__type__, "id", lang_field("name")]},
        "done",
    ]


def tag_spec(cls, request, pk=None):
    ProjectGroup = apps.get_model("project.ProjectGroup")
    return [
        (qs.pipe(
            qs.select_related("group"),
            ),projectors.noop),
        __type__,
        "id",
        {"can_delete": can_delete(request.user, "group")},
        "name",
        "public",
    ]


def contact_spec(cls, request, pk=None):
    return [
        (qs.pipe(
            qs.select_related("group"),
            ),projectors.noop),
        __type__,
        "id",
        {"can_delete": can_delete(request.user, "group")},
        "name",
        "email",
        {"account": [__type__, "id", "username"]},
        {"group": [__type__, "id", lang_field("name")]},
    ]


def projectgroup_spec(cls, request, pk=None):
    spec = (
        (qs.pipe(
            qs.include_fields("parent","projects"),
            qs.select_related("parent__parent__parent__parent"),

            ),projectors.noop),
        __type__,
        "id",
        lang_field("name"),
        {"can_delete": can_delete(request.user)},
    )
    if pk:
        return spec + (
            {
                "projects": [
                    pairs.filter(private=False),
                    __type__,
                    "id",
                    lang_field("name"),
                    {
                        "viewers": (
                            qs.prefetch_related("viewers"),
                            producers.method("am_i_viewer", request),
                        )
                    },
                ]
            },
        )
    else:
        return spec + (
        {resolve_field_to_current_lang("name_count") : (
            qs.noop,
            producers.attr(resolve_field_to_current_lang("name_count")),
        )},
    )


def stream_spec(cls, request, pk=None):
    settings = cls.settings(request)
    Task = apps.get_model("project.Task")
    if settings["hide_done"]:
        tasks = [pairs.filter(done=False)]
    else:
        tasks = []
    tasks += [x for x in task_spec(Task, request) if "project" not in x]
    return [
        __type__,
        lang_field("name"),
        "id",
        {"name_count": name_task_count()},
        {"project": [__type__, "id", lang_field("name")]},
        {"tasks": tasks},
    ]


def project_spec(cls, request, pk=None):
    Stream = apps.get_model("project.Stream")
    ProjectLog = apps.get_model("project.ProjectLog")
    Task = apps.get_model("project.Task")
    ProjectUser = apps.get_model("project.ProjectUser")
    sub_qs = ProjectUser.objects.filter(pk=request.user.pk)
    return [
        (qs.pipe(
            qs.prefetch_many_to_many_relationship("viewers",related_queryset=sub_qs),
            qs.include_fields("group"),
            qs.select_related("group"),
            ),projectors.noop),
        "id",
        __type__,
        "private",
        lang_field("text"),
        {"text_m": render_markdown(f"text_{lang()}")},
        lang_field("name"),
        "short_term_outcomes",
        {"short_term_outcomes_m": render_markdown("short_term_outcomes")},
        "long_term_outcomes",
        {"long_term_outcomes_m": render_markdown("long_term_outcomes")},
        {
            "my_project": (
                qs.prefetch_related("viewers"),
                producers.method("am_i_viewer", request),
            )
        },
        specs.relationship(
            "streams",
            [
                pairs.filter(project_default=True),
                __type__,
                lang_field("name"),
                "id",
                {"tasks": task_spec(Task, request)},
            ],
            to_attr="unassigned_tasks",
        ),
        {
            "streams": [
                (qs.pipe(
                    qs.filter(project_default=False),
                    ),projectors.noop),
                __type__,
                lang_field("name"),
                "id",
                {"name_count": name_task_count()},
                {"tasks": task_spec(Task, request)},
            ],
        },
        {
            "group": [__type__, "id", lang_field("name")],
        },
        {
            "status": [__type__, "id", lang_field("name")],
        },
        {
            "log": [__type__, "id"],
        },
        {
            "leads": [__type__, "name", "id"],
        },
        {
            "teams": [__type__, lang_field("name"), "id"],
        },
        {
            "tags": [__type__, "name", "id"],
        },
    ]


def min_project_spec(cls, request, pk=None):
    ProjectUser = apps.get_model("project.ProjectUser")
    sub_qs = ProjectUser.objects.filter(pk=request.user.pk)
    return [
        (qs.pipe(
            qs.prefetch_many_to_many_relationship("viewers",related_queryset=sub_qs),
            qs.include_fields("group"),
            qs.select_related("group"),
            ),projectors.noop),
        "id",
        "private",
        __type__,
        lang_field("name"),
    ]


def projectlog_spec(cls, request, pk=None):
    ProjectLogEntry = apps.get_model("project.ProjectLogEntry")
    return [
        __type__,
        {"project": ["id", __type__]},
        "id",
        {"entries": projectlogentry_spec(ProjectLogEntry, request)},
    ]


def projectlogentry_spec(cls, request, pk=None):
    return [
        __type__,
        "id",
        "text",
        {"log": ["id", __type__]},
        {"rendered_text": render_markdown(f"text")},
        "addstamp",
    ]


def time_report(cls, request, pk=None):
    return [
        __type__,
        "id",
        {"user": [__type__, "id", "username"]},
        "time",
        "week",
    ]
