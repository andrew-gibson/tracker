import markdown
import datetime
from django.apps import apps
from django.db.models import (
    CharField,
    CharField,
    BooleanField,
    IntegerField,
    Value,
    Q,
    Count,
    F,
    Prefetch,
    OuterRef,
    Subquery,
    Sum,
    Max,
    When,
    Case,
)
from django.db.models.functions import Concat, Replace
from django.utils import timezone
from django_readers import qs, pairs, projectors, producers, specs
from django.urls import reverse
from core.lang import lang, resolve_field_to_current_lang
from . import permissions
from . import time_utils

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


def add_log_date_and_order(request):
    two_weeks_ago = timezone.now() - timezone.timedelta(weeks=2)
    four_weeks_ago = timezone.now() - timezone.timedelta(weeks=3)
    ProjectLogEntry = apps.get_model("project.ProjectLogEntry")
    return qs.pipe(
        qs.annotate(
            most_recent_log_date=Subquery(
                ProjectLogEntry.objects.filter(
                    log__project=OuterRef("pk"), user=request.project_user
                )
                .order_by("-addstamp")
                .values("addstamp")[:1]
            ),
            has_log_date = Case(
                When(most_recent_log_date__isnull=True, then=Value(False)),
                When(most_recent_log_date__isnull=False, then=Value(True)),
                output_field=BooleanField(),
            ),
            last_look_age = Case(
               When(most_recent_log_date__gte = two_weeks_ago, then=Value(0)),
               When(most_recent_log_date__gte = four_weeks_ago, then=Value(1)),
               When(most_recent_log_date__lt = four_weeks_ago, then=Value(2)),
               When(has_log_date = False, then=Value(2)),
               output_field=IntegerField()
            ),
        ),
        qs.order_by("has_log_date", "most_recent_log_date"),
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


def __core_info__(request, include_fields=None, select_related=None):

    def perms(user, *attrs):
        prepare = qs.pipe(
            qs.include_fields(*(include_fields or [])),
            qs.select_related(*(select_related or [])),
        )

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
        {"__perms__": perms(request.project_user, include_fields, select_related)},
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

        if pk == request.project_user.pk:
            user = request.project_user
        else:
            user = (
                ProjectUser.objects.only("id", "manages", "belongs_to")
                .select_related("manages", "belongs_to")
                .get(pk=pk)
            )

        def add_project_data_to_user():
            prepare_qs, projection = specs.process(miniproject_spec(Project, request))

            def producer(u):
                return {
                    "projects": [
                        projection(x) for x in prepare_qs(user.all_my_projects).all()
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
                            pairs.exclude(pk=request.project_user.pk),
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
                *__core_info__(request, select_related=["project"]),
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
    return [
        (
            qs.select_related("group"),
            projectors.noop,
        ),
        *__core_info__(request),
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
                qs.include_fields("app"),
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
                    pairs.exclude(status__name_en__in=["Completed", "Canceled"]),
                    {"is_new" : (qs.include_fields("addstamp"), 
                                 lambda inst : timezone.now() - inst.addstamp < datetime.timedelta(weeks=4)
                        )
                    },
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
        (
            qs.include_fields(
                "project_default",
            ),
            projectors.noop,
        ),
        lang_field("name"),
        {"name_count": name_task_count()},
        {"project": [*__core_info__(request), lang_field("name")]},
        {"tasks": tasks},
    ]


def project_spec(cls, request, pk=None):
    Stream = apps.get_model("project.Stream")
    TimeReport = apps.get_model("project.TimeReport")
    Task = apps.get_model("project.Task")
    ProjectUser = apps.get_model("project.ProjectUser")

    sub_qs = ProjectUser.objects.filter(pk=request.project_user.pk)

    most_recent_date_subquery = (
        ProjectLogEntry.objects.filter(
            log__project=OuterRef("pk"), user=request.project_user
        )
        .order_by("-addstamp")
        .values("addstamp")[:1]
    )

    return [
        (
            qs.pipe(
                qs.prefetch_many_to_many_relationship(
                    "viewers", related_queryset=sub_qs
                ),
                qs.include_fields("group", "private", "private_owner"),
                pairs.exclude(status__name_en__in=["Completed", "Canceled"]),
                qs.select_related("group"),
                qs.annotate(
                    most_recent_log_date=Subquery(most_recent_date_subquery),
                    has_log_date=Case(
                        When(most_recent_log_date__isnull=True, then=Value(False)),
                        When(most_recent_log_date__isnull=False, then=Value(True)),
                        output_field=BooleanField(),
                    ),
                ),
                qs.order_by("-has_log_date", "-most_recent_log_date"),
            ),
            projectors.noop,
        ),
        *__core_info__(request),
        {"most_recent_log_date" : (qs.noop,producers.attr("most_recent_log_date"))},
        {"team_size" : pairs.count("project_team")},
        {"reported_time_in_last_month" : pairs.sum(
                        "timereports__time",
                        filter=Q(
                            timereports__week__gte=time_utils.get_last_n_weeks(4)[-1][
                                "week_start"
                            ]
                        ),
        )},
        {"reported_time_in_last_quarter" : pairs.sum(
                        "timereports__time",
                        filter=Q(
                            timereports__week__gte=time_utils.get_last_n_weeks(12)[-1][
                                "week_start"
                            ]
                        ),
        )},
        {"reported_time_in_last_year" : pairs.sum(
                        "timereports__time",
                        filter=Q(
                            timereports__week__gte=time_utils.get_last_n_weeks(52)[-1][
                                "week_start"
                            ]
                        ),
        )},
        {"last_look_age": (qs.noop, producers.attr("last_look_age"))},
        "private",
        lang_field("text"),
        lang_field("name"),
        {"is_new" : (qs.include_fields("addstamp"), 
                     lambda inst : timezone.now() - inst.addstamp < datetime.timedelta(weeks=4)
            )
        },
        {"text_m": render_markdown(f"text_{lang()}")},
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
                (qs.include_fields("project_default"), projectors.noop),
                *__core_info__(request),
                {"name_count": name_task_count()},
                lang_field("name"),
                {"tasks": task_spec(Task, request)},
            ],
        },
        {
            "group": [
                *__core_info__(request),
                lang_field("name"),
            ],
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
            "tags": [
                (qs.include_fields("group"), projectors.noop),
                *__core_info__(request),
                "name",
            ],
        },
    ]


def miniproject_spec(cls, request, pk=None):
    return [ ( add_log_date_and_order(request),
               projectors.noop
              ),
        pairs.exclude(status__name_en__in=["Completed", "Canceled"]),
        {"is_new" : (qs.include_fields("addstamp"), 
                     lambda inst : timezone.now() - inst.addstamp < datetime.timedelta(weeks=4)
            )
        },
        {"most_recent_log_date": (qs.noop, producers.attr("most_recent_log_date"))},
        {"last_look_age": (qs.noop, producers.attr("last_look_age"))},
        {"private_owner": ["id"]},
        {"group": ["id"]},
        "private",
        *__core_info__(request),
        lang_field("name"),
    ]


def projectlog_spec(cls, request, pk=None):
    ProjectLogEntry = apps.get_model("project.ProjectLogEntry")
    return [
        *__core_info__(request),
        {"project": [*__core_info__(request)]},
        {
            "entries": [
                *__core_info__(request),
                "text",
                {"rendered_text": render_markdown(f"text")},
                "addstamp",
            ]
        },
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
        {"project": ["id"]},
        "text",
        "time",
        "week",
    ]
