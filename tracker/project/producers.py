from django.db.models import CharField, Value
from django_readers import qs, pairs, projectors, producers, specs

__type__ = {"__type__" : (qs.noop, producers.attrgetter("_meta.label"))}

basic_rest_spec = ["name", "id", ]

task_rest_spec = [
    __type__,
    "id",
    {"project": [__type__,"id", "name"]},
    {"stream": [__type__,"id", "name"]},
    "start_date",
    "target_date",
    "text",
    {"lead": [__type__,"id", "name"]},
    {"teams": [__type__,"id", "name"]},
    {"competency": [__type__,"id", "name"]},
    "done",
    "name",
]

stream_rest_spec = [
    __type__,
    "name",
    "name",
    "id",
    {"project": [__type__,"id", "name"]},
    {"tasks": task_rest_spec},
]


project_rest_spec = [
    __type__,
    "text",
    "id",
    "name",
    specs.relationship(
        "streams",
        [
            pairs.filter(project_default=True),
            __type__,
            "name",
            "id",
            {"tasks": task_rest_spec},
        ],
        to_attr="unassigned_tasks",
    ),
    {
        "streams": [
            pairs.filter(project_default=False),
            __type__,
            "name",
            "id",
            {"tasks": task_rest_spec},
        ],
    },
    {
        "point_of_contact": [__type__,"name", "id"],
    },
    {
        "teams": [__type__,"name", "id"],
    },
    {
        "tags": [__type__,"name", "id"],
    },
]
