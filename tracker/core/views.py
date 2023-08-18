import json
from . import models
from .utils import API
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from text.translate import gettext_lazy as _
from django.urls import reverse

api = API(namespace="core")


@api.post_get("login/", require_login=False)
@ensure_csrf_cookie
def _login(request):
    if request.headers.get("Content-Type", "text/plain") == "application/json":
        if request.method == "POST":
            username = request.data.get("username")
            password = request.data.get("password")
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return HttpResponse(
                    json.dumps({"status": "success"}), content_type="application/json"
                )
        else:
            return HttpResponse(
                json.dumps({"status": "failure"}), content_type="application/json"
            )
    else:
        if request.method == "POST":
            username = request.POST.get("username")
            password = request.POST.get("password")
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect(reverse(user.login_redirect))
        return render(request, "login.html", {})


@api.post_get("logout/")
def _logout(request):
    logout(request)
    return render(request, "login.html", {})
