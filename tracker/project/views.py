from core.utils import API
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from text.translate import gettext_lazy as _
from django.urls import reverse

api = API(namespace="core")

@api.get("project/")
def main(request):
    return HttpResponse("success")
