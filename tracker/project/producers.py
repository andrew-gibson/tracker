from django.apps import apps
from django.db.models import CharField, Value, Q, Count, CharField, F
from django.db.models.functions import Concat, Replace
from django_readers import qs, pairs, projectors, producers, specs

__type__ = {"__type__": (qs.noop, producers.attrgetter("_meta.label"))}

basic_spec = [
    "name",
    "id",
    __type__,
]

task_spec = [
    __type__,
    "id",
    "order",
    {"project": [__type__, "id", "name"]},
    {"stream": [__type__, "id", "name"]},
    "start_date",
    "target_date",
    "text",
    {"lead": [__type__, "id", "name"]},
    {"teams": [__type__, "id", "name"]},
    {"competency": [__type__, "id", "name"]},
    "done",
    "name",
]

mini_task_spec = [x for x in task_spec if "project" not in x]

name_count = (
    qs.annotate(
        name_count=Concat(
            Replace(F("name"), Value("_"), Value(" ")),
            Value(" ("),
            Count("tasks", filter=Q(tasks__done=False)),
            Value(")"),
            output_field=CharField(),
        )
    ),
    producers.attr("name_count"),
)

def tag_spec(cls, request):
    return [
        __type__,
        "id",
        {
            "can_delete": (
                qs.include_fields("group"),
                producers.method("can_i_delete", request),
            )
        },
        "name",
        "public",
    ]

def team_spec(cls, request):
    return [
        __type__,
        "id",
        {
            "can_delete": (
                qs.include_fields("group"),
                producers.method("can_i_delete", request),
            )
        },
        "name",
        "public",
    ]


def stream_spec(cls, request):
    settings = cls.settings(request)
    if settings["hide_done"]:
        tasks = [pairs.filter(done=False)]
    else:
        tasks = []
    tasks += mini_task_spec
    return [
        __type__,
        "name",
        "name",
        "id",
        {"name_count": name_count},
        {"project": [__type__, "id", "name"]},
        {"tasks": tasks},
    ]


project_spec = [
    __type__,
    "text",
    {
        "rendered_text": (
            qs.include_fields("text"),
            producers.method("render_text"),
        )
    },
    "id",
    "name",
    specs.relationship(
        "streams",
        [
            pairs.filter(project_default=True),
            __type__,
            "name",
            "id",
            {"tasks": task_spec},
        ],
        to_attr="unassigned_tasks",
    ),
    {
        "streams": [
            pairs.filter(project_default=False),
            __type__,
            "name",
            "id",
            {"name_count": name_count},
            {"tasks": task_spec},
        ],
    },
    {
        "point_of_contact": [__type__, "name", "id"],
    },
    {
        "teams": [__type__, "name", "id"],
    },
    {
        "tags": [__type__, "name", "id"],
    },
]
