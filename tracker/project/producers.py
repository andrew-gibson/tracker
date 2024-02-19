from django_readers import qs, pairs, projectors, producers, specs


basic_rest_spec = ["name", "id", ]

task_rest_spec = [
    "id",
    {"project": ["id", "name"]},
    {"stream": ["id", "name"]},
    "start_date",
    "target_date",
    "text",
    {"lead": ["id", "name"]},
    {"teams": ["id", "name"]},
    {"competency": ["id", "name"]},
    "done",
    "name",
]

stream_rest_spec = [
    "name",
    "name",
    "id",
    {"project": ["id", "name"]},
    {"tasks": task_rest_spec},
]


project_rest_spec = [
    "text",
    "id",
    "name",
    specs.relationship(
        "streams",
        [
            pairs.filter(project_default=True),
            "name",
            "id",
            {"tasks": task_rest_spec},
        ],
        to_attr="unassigned_tasks",
    ),
    {
        "streams": [
            pairs.filter(project_default=False),
            "name",
            "id",
            {"tasks": task_rest_spec},
        ],
    },
    {
        "point_of_contact": ["name", "id"],
    },
    {
        "teams": ["name", "id"],
    },
    {
        "tags": ["name", "id"],
    },
]
