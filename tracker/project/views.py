from django.apps import apps
from core.utils import API, render
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest
from django.urls import reverse
from text.translate import gettext_lazy as _

from .models import Project, Tag, Team, Contact

lookups = {
        "tag" : Tag,
        "team" : Team,
        "contact" : Contact
}

api = API(namespace="project", session={})


@api.get("main/")
def main(request):
    return HttpResponse("success")


@api.get_post_delete_put(["project/", "project/<int:pk>/"])
async def project(request, pk=None):
    session, set_session = api.get_url_session(request)
    if request.method == "GET" and not pk:
        return render(
            request,
            "projects/projects.html",
            {"projects": [p async for p in Project.objects.filter(user=request.user)]},
        )
    if request.method == "GET" and pk:
        return render(
            request,
            "projects/project.html",
            {"project": await Project.objects.filter(user=request.user).aget(pk=pk)},
        )
    if request.method == "POST" and not pk:
        pass
    if request.method == "PUT" and pk:
        pass
    if request.method == "DELETE" and pk:
        qs = Project.objects.filter(user=request.user, pk=pk)
        if await qs.acount() == 1:
            await qs.adelete()
        return render(
            request,
            "projects/projects.html",
            {"projects": [p async for p in Project.objects.filter(user=request.user)]},
        )

@api.get_post_delete_put(["lookup/<str:modelname>/", "lookup/<str:modelname>/<int:pk>/"])
async def project(request, modelname='',pk=None):
    model = lookups.get(modelname)
    if not model:
        return HttpResponseBadRequest()
    if request.method == "GET" and not pk:
        pass
    if request.method == "GET" and pk:
        pass
    if request.method == "POST" and not pk:
        pass
    if request.method == "PUT" and pk:
        pass
    if request.method == "DELETE" and pk:
        pass
    return HttpResponseBadRequest()
    


