from asgiref.sync import sync_to_async
from django.apps import apps
from core.utils import API, render
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest
from django.urls import reverse
from text.translate import gettext_lazy as _

from .models import Project, Tag, Team, Contact, ThemeWork

generic_models = {
        "tag" : Tag,
        "team" : Team,
        "contact" : Contact,
        "project" : Project,
        "themework" : ThemeWork,
}

api = API(namespace="project", session={})


@api.get("main/")
def main(request):
    return HttpResponse("success")

@api.get_post_delete_put(["m/<str:modelname>/", "m/<str:modelname>/<int:pk>/"])
def project(request, modelname='',pk=None):
    session, set_session = api.get_url_session(request)
    model = generic_models.get(modelname)
    if not model:
        return HttpResponseBadRequest()
    if request.method == "GET":                  
        return  model.get(request,pk)
    if request.method == "POST" and not pk:
        return  model.post(request)
    if request.method == "PUT" and pk:
        return  model.put(request,pk)
    if request.method == "DELETE" and pk:
        return  model.delete(request,pk)
    return HttpResponseBadRequest()

