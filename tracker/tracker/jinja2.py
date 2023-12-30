import random
import string
import json
from urllib import parse

from crispy_forms.utils import render_crispy_form
from django.templatetags.static import static
from django.urls import reverse
from django.utils.translation import activate
from jinja2 import Environment, pass_context
from text.translate import gettext_lazy as _
from text.translate import other_lang
from django.template.backends.jinja2 import Jinja2


@pass_context
def url_translate(context):
    request = context["request"]
    r = request.resolver_match
    url_name, args, kwargs = r.url_name, r.args, r.kwargs
    activate(other_lang())
    translated_url = reverse(url_name, args=args, kwargs=kwargs)
    activate(other_lang())
    return translated_url


@pass_context
def crispy(context, form):
    return render_crispy_form(form, context=context)


def random_id():
    letters = string.ascii_lowercase
    return "".join(random.choice(letters) for i in range(10))


def url_session(view_name, session=None, kwargs=None):
    url = reverse(view_name, kwargs=kwargs)
    return "?".join(url, parse.urlencode(session))


def environment(**options):
    env = Environment(**options)
    env.globals.update(
        {
            "static": static,
            "url": reverse,
            "random_id": random_id,
            "crispy": crispy,
            "len" : len,
            "url_translate": url_translate,
            "_": _,
            "getattr": getattr,
            "print": print,
            "json" : json,
        }
    )
    return env


