import json
from core.utils import (
    API,
    render,
    assert_or_404,
    get_model_or_404,
    link_m2m_or_404,
    unlink_m2m_or_404,
    get_related_model_or_404,
)
from django.apps import apps
from django.db.models import Q
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
    typeahead_url_kwargs = {
        "m": "project.Project",
        "attr": "tags",
    }
    if project.pk:
        typeahead_url_kwargs["pk"] = project.pk
    return render(
        request,
        "project/main.html",
        {
            "form": form,
            "typeahead_url_kwargs": reverse(
                "core:sel_setup", kwargs=typeahead_url_kwargs
            ),
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


@api.post(["ac/<str:component_id>/<str:m>/"])
def ac(request, component_id, m):
    model = get_model_or_404(m, test=lambda m: hasattr(m, "text_search_trigger"))
    trigger = model.text_search_trigger
    text_input = request.POST[component_id]
    query = [
        x.replace(trigger, "")
        for x in text_input.split(" ")
        if x.startswith(trigger) and len(x) != 1
    ]
    results = model.ac(request, query) if len(query) else []
    return render(request, f"{model._name}/ac_results.html", {"results": results})


