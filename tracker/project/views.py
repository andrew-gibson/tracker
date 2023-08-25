from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from core.utils import API
from text.translate import gettext_lazy as _

api = API(namespace="project", session={})


@api.get("main/")
def main(request):
    return HttpResponse("success")


@api.get_post_delete_put(["project/", "project/<int:pk>/"])
async def project(request, pk=None):
    session, set_session = api.get_url_session(request)
    if request.method == "GET" and not pk:
        return render()
    if request.method == "GET" and pk:
        pass
    if request.method == "POST" and not pk:
        pass
    if request.method == "PUT" and pk:
        pass
    if request.method == "DELETE" and pk:
        pass

