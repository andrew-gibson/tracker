from itertools import chain, groupby

from core.utils import (API, get_model_or_404, link_m2m_or_404, render,
                        unlink_m2m_or_404)
from django.apps import apps
from django.http import (HttpResponse, HttpResponseBadRequest, JsonResponse,
                         QueryDict)
from django.shortcuts import get_object_or_404
from django.urls import reverse
from text.translate import gettext_lazy as _

from .models import Contact, Project, Tag, Team, Theme, ThemeWork

api = API(namespace="project", session={})


@api.get("main/")
def main(request):
    project = Project.objects.first()
    project.tags.set(Tag.belongs_to_user(request).all())
    return render(
        request,
        "project/main.html",
        {
            "form": Project.form(request)(
                instance=project
            )
        },
    )


@api.get_post_delete_put(["m/<str:modelname>/", "m/<str:modelname>/<int:pk>/"])
def project(request, modelname="", pk=None):
    session, set_session = api.get_url_session(request)
    model = get_model_or_404(f"project.{modelname}")
    if not model:
        return HttpResponseBadRequest()
    if request.method == "GET":
        return model.GET(request, pk)
    if request.method == "POST" and not pk:
        return model.POST(request)
    if request.method == "PUT" and pk:
        return model.PUT(request, pk)
    if request.method == "DELETE" and pk:
        return model.DELETE(request, pk)
    return HttpResponseBadRequest()


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
def ac(request,component_id,m):
    model = get_model_or_404(m, test=lambda m: hasattr(m, "text_search_trigger"))
    trigger = model.text_search_trigger
    text_input = request.POST[component_id]
    query = [x.replace(trigger,"") for x in text_input.split(" ") if x.startswith(trigger) and len(x) != 1]
    results = model.ac(request, query) if len(query) else []
    print(results)
    return render(request,f"{model._name}/ac_results.html",{"results" : results})


@api.get(
    ["lookup/<str:m>/", "lookup/<str:m>/<str:query>/", "lookup/<str:m>/<str:variant>/<str:query>/"]
)
def lookup(request, m, variant="", query=""):
    model = get_model_or_404(m, test=lambda m: hasattr(m, "ac"))
    return JsonResponse(model.ac(request, query, variant), safe=False)
