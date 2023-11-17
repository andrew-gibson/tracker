import json
from core.utils import (
    API,
    render,
    assert_or_404,
    get_model_or_404,
    link_m2m_or_404,
    unlink_m2m_or_404,
)
from core.autocomplete import AutoCompleteNexus
from django.apps import apps
from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    JsonResponse,
    QueryDict,
    Http404,
)
from django.shortcuts import get_object_or_404
from django.urls import reverse
from text.translate import gettext_lazy as _

from .models import Contact, Project, Tag, Team, Theme, ThemeWork, Model

api = API(namespace="project", session={})


@api.get("main/")
def main(request):
    project = Project.objects.first()
    project.tags.set(Tag.belongs_to_user(request).all())
    form = Project.form(request)(instance=project)
    tags_typeahead = {
        "m": "project.Project",
        "attr": "tags",
    }
    teams_typeahead = {
        "m": "project.Project",
        "attr": "teams",
    }
    if project.pk:
        tags_typeahead["pk"] = project.pk
        teams_typeahead["pk"] = project.pk
    return render(
        request,
        "project/main.html",
        {
            "form": form,
            "tags_typeahead": reverse("core:sel_setup", kwargs=tags_typeahead),
            "teams_typeahead": reverse("core:sel_setup", kwargs=teams_typeahead),
        },
    )


@api.post_delete(
    [
        "m2m/<str:m1>/<int:pk1>/<str:m2>/<int:pk2>/",
        "m2m/<str:m1>/<int:pk1>/<str:m2>/<int:pk2>/attr/",
    ]
)
def m2m(request, m1, pk1, m2, pk2, attr=""):
    model1 = get_model_or_404(m1)
    model2 = get_model_or_404(m2)
    obj1 = get_object_or_404(model1.belongs_to_user(request), pk=pk1)
    obj2 = get_object_or_404(model2.belongs_to_user(request), pk=pk2)
    if request.method == "POST":
        link_m2m_or_404(obj1, obj2, attr)
    if request.method == "DELETE":
        unlink_m2m_or_404(obj1, obj2, attr)
    return HttpResponse("success")


@api.post(["free_text_ac/<str:m>/<str:attr>/"])
def free_text_ac(request, m, attr):
    model = get_model_or_404(m, test=lambda m : issubclass(m,(AutoCompleteNexus,)))
    text_input = request.POST.get(attr)
    fields =  model.get_autocompletes()
    results = {
        f.name: {
            "model": f.related_model,
            "name": f.name,
            "many_to_many" :  f.many_to_many,
            "search_terms": model.find_words_from_trigger(
                text_input, f.related_model.text_search_trigger, many = f.many_to_many
            ),
        }
        for f in fields
    }
    for name in results:
        results[name]["results"] = [
            [term, results[name]["model"].ac(request, term)]
            for term in results[name]["search_terms"]
        ]

    return render(request, f"free_text_ac.html", {"results": results})
