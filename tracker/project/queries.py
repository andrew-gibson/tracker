import markdown
from django.apps import apps
from django.db.models import CharField, Value, Q, Count, CharField, F
from django.db.models.functions import Concat, Replace
from django_readers import qs, pairs, projectors, producers, specs
from django.urls import reverse
from core.lang import lang, resolve_field_to_current_lang
from . import permissions

"""
  1. top level is specs
  2. specs are made up of pairs
  3. pairs are composed of producers, projectors and qs (prepare)


"""


def lang_field(field):
    return {field: f"{field}_{lang()}"}


def render_markdown(attr):
    prepare = qs.include_fields(attr)

    def produce(inst):
        return markdown.markdown(getattr(inst, attr) or "")

    return prepare, produce


def count(attr):
    prepare = qs.include_fields(attr)

    def producer(inst):
        return getattr(inst, attr).count()

    return prepare, producer


def can_delete(user, *attrs):
    if attrs:
        prepare = qs.include_fields(*attrs)
    else:
        prepare = qs.noop

    def producer(inst):
        return permissions.good_request(user, "DELETE", inst)

    return prepare, producer


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


__core_info__ = [
    "id",
    {"__type__": (qs.noop, producers.attrgetter("_meta.label"))},
    {"__url__": (qs.noop, producers.attrgetter("url"))},
]


def force_type(model):
    m = apps.get_model(model)

    def produce1(inst):
        return m._meta.label

    def produce2(inst):
        return reverse("core:main", kwargs={"m": model, "pk": inst.id})

    return [
        {"__type__": (qs.noop, produce1)},
        {"__url__": (qs.noop, produce2)},
    ]


def basic_spec(cls, request, pk=None):
    return [
        lang_field("name"),
        *__core_info__,
    ]


def projectuser_spec(cls, request, pk=None):
    Project = apps.get_model("project.Project")
    spec = (
        *__core_info__,
        "username",
        {"name": "username"},
        {
            "belongs_to": [
                *force_type("project.ProjectGroup"),
                lang_field("name"),
                "id",
            ]
        },
    )

    if pk:

        def add_project_data_to_user(request):
            cls = apps.get_model("project.MinProject")
            prepare_qs, projection = cls.readers(request)

            def producer(u):
                return {
                    "projects": [
                        projection(x)
                        for x in cls.objects.filter(cls.users_projects(u))
                        .exclude(cls.private_projects(u))
                        .distinct()
                    ]
                }

            return qs.noop, producer

        return spec + (
            add_project_data_to_user(request),
            {
                "manages": [
                    *force_type("project.ProjectGroup"),
                    lang_field("name"),
                    "id",
                    {
                        "team_members": [
                            pairs.exclude(pk=request.user.pk),
                            *force_type("project.ProjectUser"),
                            {"name": "username"},
                            "id",
                        ]
                    },
                ]
            },
        )

    return spec


def task_spec(cls, request, pk=None):
    return [
        *__core_info__,
        "order",
        lang_field("text"),
        lang_field("name"),
        {"project": [*__core_info__, lang_field("name")]},
        {
            "stream": [
                *__core_info__,
                lang_field("name"),
            ]
        },
        "start_date",
        "target_date",
        {"lead": [*__core_info__, "username"]},
        {"teams": [*__core_info__, lang_field("name")]},
        {"competency": [*__core_info__, lang_field("name")]},
        "done",
    ]


def tag_spec(cls, request, pk=None):
    ProjectGroup = apps.get_model("project.ProjectGroup")
    return [
        (
            qs.select_related("group"),
            projectors.noop,
        ),
        *__core_info__,
        {"can_delete": can_delete(request.user, "group")},
        "name",
        "public",
    ]


def contact_spec(cls, request, pk=None):
    return [
        (
            qs.select_related("group"),
            projectors.noop,
        ),
        *__core_info__,
        {"can_delete": can_delete(request.user, "group")},
        "name",
        "email",
        {"account": [*__core_info__, "username"]},
        {"group": [*__core_info__, lang_field("name")]},
    ]


def projectgroup_spec(cls, request, pk=None):
    spec = (
        (
            qs.pipe(
                qs.include_fields("parent", "projects"),
                qs.select_related("parent__parent__parent__parent"),
                qs.prefetch_related("children__children__children__children"),
            ),
            projectors.noop,
        ),
        *__core_info__,
        lang_field("name"),
        {"can_delete": can_delete(request.user)},
    )
    if pk:
        return spec + (
            {
                "projects": [
                    pairs.filter(private=False),
                    *__core_info__,
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
            {
                resolve_field_to_current_lang("name_count"): (
                    qs.noop,
                    producers.attr(resolve_field_to_current_lang("name_count")),
                )
            },
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
        *__core_info__,
        lang_field("name"),
        {"name_count": name_task_count()},
        {"project": [*__core_info__, lang_field("name")]},
        {"tasks": tasks},
    ]


def project_spec(cls, request, pk=None):
    Stream = apps.get_model("project.Stream")
    ProjectLog = apps.get_model("project.ProjectLog")
    Task = apps.get_model("project.Task")
    ProjectUser = apps.get_model("project.ProjectUser")
    sub_qs = ProjectUser.objects.filter(pk=request.user.pk)
    return [
        (
            qs.pipe(
                qs.prefetch_many_to_many_relationship(
                    "viewers", related_queryset=sub_qs
                ),
                qs.include_fields("group"),
                qs.select_related("group"),
            ),
            projectors.noop,
        ),
        *__core_info__,
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
                *__core_info__,
                lang_field("name"),
                {"tasks": task_spec(Task, request)},
            ],
            to_attr="unassigned_tasks",
        ),
        {
            "streams": [
                (
                    qs.pipe(
                        qs.filter(project_default=False),
                    ),
                    projectors.noop,
                ),
                *__core_info__,
                lang_field("name"),
                {"name_count": name_task_count()},
                {"tasks": task_spec(Task, request)},
            ],
        },
        {
            "group": [*__core_info__, lang_field("name")],
        },
        {
            "status": [*__core_info__, lang_field("name")],
        },
        {
            "project_manager": [*__core_info__, "username"],
        },
        {
            "log": [*__core_info__],
        },
        {
            "partners": [*__core_info__, lang_field("name")],
        },
        {
            "lead": [
                *__core_info__,
                "username",
            ],
        },
        {
            "project_team": [
                *__core_info__,
                "username",
            ],
        },
        {
            "tags": [*__core_info__, "name"],
        },
    ]


def min_project_spec(cls, request, pk=None):
    ProjectUser = apps.get_model("project.ProjectUser")
    sub_qs = ProjectUser.objects.filter(pk=request.user.pk)
    return [
        (
            qs.pipe(
                qs.prefetch_many_to_many_relationship(
                    "viewers", related_queryset=sub_qs
                ),
                qs.include_fields("group"),
                qs.select_related("group"),
            ),
            projectors.noop,
        ),
        "private",
        *__core_info__,
        lang_field("name"),
    ]


def projectlog_spec(cls, request, pk=None):
    ProjectLogEntry = apps.get_model("project.ProjectLogEntry")
    return [
        *__core_info__,
        {"project": [*__core_info__]},
        {"entries": projectlogentry_spec(ProjectLogEntry, request)},
    ]


def projectlogentry_spec(cls, request, pk=None):
    return [
        *__core_info__,
        "text",
        {"log": [*__core_info__]},
        {"rendered_text": render_markdown(f"text")},
        "addstamp",
    ]


def time_report(cls, request, pk=None):
    return [
        *__core_info__,
        {"user": [*__core_info__, "username"]},
        {"project": [*__core_info__]},
        "time",
        "week",
    ]
