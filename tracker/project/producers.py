import markdown
from django.apps import apps
from django.db.models import CharField, Value, Q, Count, CharField, F
from django.db.models.functions import Concat, Replace
from django_readers import qs, pairs, projectors, producers, specs
from core.lang import lang

def lang_field(field):
    return {field : f"{field}_{lang()}"}

def render_markdown(attr):
    prepare = qs.include_fields(attr)

    def produce(inst):
        return markdown.markdown(getattr(inst, attr) or "")

    return prepare, produce


__type__ = {"__type__": (qs.noop, producers.attrgetter("_meta.label"))}


def basic_spec(cls,request): 
    return [
        lang_field("name"),
        "id",
        __type__,
    ]

def task_spec(cls,request):
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


def name_count():
    return  (
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

def contact_spec(cls, request):
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
        "email",
        {"account" : [__type__, "id","username"]},
        {"group" : [__type__, "id","name_en"]},
    ]



def projectgroup_spec(cls, request):
    return [
        __type__,
        "id",
        {
            "can_delete": (
                qs.noop,
                producers.method("can_i_delete", request),
            )
        },
        {"projects": [
            pairs.filter(private=False),
            "id",
            lang_field("name"),
        ]},
        "name",
    ]


def stream_spec(cls, request):
    settings = cls.settings(request)
    Task = apps.get_model("project.Task")
    if settings["hide_done"]:
        tasks = [pairs.filter(done=False)]
    else:
        tasks = []
    tasks += [x for x in task_spec(Task,request) if "project" not in x]
    return [
        __type__,
        lang_field("name"),
        "id",
        {"name_count": name_count()},
        {"project": [__type__, "id", lang_field("name")]},
        {"tasks": tasks},
    ]


def project_spec(cls, request):
    Stream = apps.get_model("project.Stream")
    ProjectLog = apps.get_model("project.ProjectLog")
    Task = apps.get_model("project.Task")
    return [
        "id",
        __type__,
        lang_field("text"),
        {"text_m": render_markdown(f"text_{lang()}")},
        lang_field("name"),
        "short_term_outcomes",
        {"short_term_outcomes_m": render_markdown("short_term_outcomes")},
        "long_term_outcomes",
        {"long_term_outcomes_m": render_markdown("long_term_outcomes")},
        {
            "my_project": (
                qs.include_fields("viewers"),
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
                {"tasks": task_spec(Task,request)},
            ],
            to_attr="unassigned_tasks",
        ),
        {
            "streams": [
                pairs.filter(project_default=False),
                __type__,
                lang_field("name"),
                "id",
                {"name_count": name_count()},
                {"tasks": task_spec(Task,request)},
            ],
        },
        {
            "status": [__type__, "id",lang_field("name")],
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


def projectlog_spec(cls, request):
    ProjectLogEntry = apps.get_model("project.ProjectLogEntry")
    return [
        __type__,
        {"project" : ["id",__type__]},
        "id",
        {"entries": projectlogentry_spec(ProjectLogEntry, request)},
    ]


def projectlogentry_spec(cls, request):
    return [
        __type__,
        "id",
        "text",
        {"log": ["id",__type__]},
        {"rendered_text": render_markdown(f"text")},
        "addstamp",
    ]
