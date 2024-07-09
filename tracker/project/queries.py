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


def __core_info__(request, *include_fields):

    def perms(user, *attrs):
        if attrs:
            prepare = qs.include_fields(*attrs)
        else:
            prepare = qs.noop

        def producer(inst):
            return {
                "PUT": permissions.good_request(user, "PUT", inst),
                "DELETE": permissions.good_request(user, "DELETE", inst),
            }

        return prepare, producer

    return [
        "id",
        {"__type__": (qs.noop, producers.attrgetter("_meta.label"))},
        {"__url__": (qs.noop, producers.attrgetter("url"))},
        {"__perms__": perms(request.user, *include_fields)},
    ]


def settings_spec(cls, request, pk=None):
    return [
        "hide_done",
        "see_all_projects",
        "id",
        "work_hours",
        *__core_info__(request),
    ]


def basic_spec(cls, request, pk=None):
    return [
        lang_field("name"),
        *__core_info__(request),
    ]


def projectuser_spec(cls, request, pk=None):
    Project = apps.get_model("project.Project")
    ProjectUser = apps.get_model("project.ProjectUser")
    ProjectGroup = apps.get_model("project.ProjectGroup")

    spec = (
        *__core_info__(request),
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

        user = (
            ProjectUser.objects.only("id", "manages")
            .select_related("manages")
            .get(pk=pk)
        )

        def add_project_data_to_user():
            prepare_qs, projection = Project.readers(request)

            def producer(u):
                return {
                    "projects": [
                        projection(x) for x in prepare_qs(user.all_my_projects)
                    ]
                }

            return qs.noop, producer

        def add_manages_descendants():
            prepare_qs, projection = ProjectGroup.readers(request)

            def producer(u):
                group = u.manages or u.belongs_to
                ids = [x.id for x in group.descendants]
                groups = prepare_qs(ProjectGroup.objects.filter(id__in=ids))
                return {"teams": [projection(x) for x in groups]}

            return qs.noop, producer

        return spec + (
            add_project_data_to_user(),
            add_manages_descendants(),
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
        *__core_info__(request),
        "order",
        lang_field("text"),
        lang_field("name"),
        {"project": [*__core_info__(request), lang_field("name")]},
        {
            "stream": [
                *__core_info__(request),
                lang_field("name"),
            ]
        },
        "start_date",
        "target_date",
        {"lead": [*__core_info__(request), "username"]},
        {"teams": [*__core_info__(request), lang_field("name")]},
        {"competency": [*__core_info__(request), lang_field("name")]},
        "done",
    ]


def tag_spec(cls, request, pk=None):
    ProjectGroup = apps.get_model("project.ProjectGroup")
    return [
        (
            qs.select_related("group"),
            projectors.noop,
        ),
        *__core_info__(request, "group"),
        "name",
        "public",
    ]


def contact_spec(cls, request, pk=None):
    return [
        (
            qs.select_related("group"),
            projectors.noop,
        ),
        *__core_info__(request, "group"),
        "name",
        "email",
        {"account": [*__core_info__(request), "username"]},
        {"group": [*__core_info__(request), lang_field("name")]},
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
        *__core_info__(request),
        lang_field("name"),
    )
    if pk:
        return spec + (
            {
                "projects": [
                    pairs.filter(private=False),
                    *__core_info__(request),
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
        *__core_info__(request),
        lang_field("name"),
        {"name_count": name_task_count()},
        {"project": [*__core_info__(request), lang_field("name")]},
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
        *__core_info__(request),
        "private",
        lang_field("text"),
        {"text_m": render_markdown(f"text_{lang()}")},
        lang_field("name"),
        "short_term_outcomes",
        {"short_term_outcomes_m": render_markdown("short_term_outcomes")},
        "long_term_outcomes",
        {"long_term_outcomes_m": render_markdown("long_term_outcomes")},
        {
            "viewers": (
                qs.prefetch_related("viewers"),
                producers.method("am_i_viewer", request),
            )
        },
        {
            "streams": [
                {"name_count": name_task_count()},
                *__core_info__(request),
                lang_field("name"),
                {"tasks": task_spec(Task, request)},
            ],
        },
        {
            "group": [*__core_info__(request), lang_field("name")],
        },
        {
            "status": [*__core_info__(request), lang_field("name")],
        },
        {
            "project_manager": [*__core_info__(request), "username"],
        },
        {
            "log": [*__core_info__(request)],
        },
        {
            "partners": [*__core_info__(request), lang_field("name")],
        },
        {
            "lead": [
                *__core_info__(request),
                "username",
            ],
        },
        {
            "project_team": [
                *__core_info__(request),
                "username",
            ],
        },
        {
            "tags": [*__core_info__(request), "name"],
        },
    ]


def projectlog_spec(cls, request, pk=None):
    ProjectLogEntry = apps.get_model("project.ProjectLogEntry")
    return [
        *__core_info__(request),
        {"project": [*__core_info__(request)]},
        {"entries": projectlogentry_spec(ProjectLogEntry, request)},
    ]


def projectlogentry_spec(cls, request, pk=None):
    return [
        *__core_info__(request),
        "text",
        {"log": [*__core_info__(request)]},
        {"rendered_text": render_markdown(f"text")},
        "addstamp",
    ]


def time_report(cls, request, pk=None):
    return [
        *__core_info__(request),
        {"user": [*__core_info__(request), "username"]},
        "time",
        "week",
    ]
