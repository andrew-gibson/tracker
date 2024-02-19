import datetime
import json
import random
import string
from urllib import parse

from crispy_forms.utils import render_crispy_form
from django.template.backends.jinja2 import Jinja2
from django.templatetags.static import static
from django.urls import reverse
from django.utils.safestring import SafeString
from django.utils.translation import activate
from jinja2 import Environment, pass_context
from text.translate import gettext_lazy as _
from text.translate import other_lang


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


def add_json_params(d):
    return "?" + parse.urlencode({key: json.dumps(d[key]) for key in d})

def make_signal_from_model(model,pk=""):
    pk = pk if pk else ""
    return f"refresh{model.replace('.','').title()}{pk}" 

def rest_pk_refresh(model,pk,params=None):
    return SafeString(f''' hx-get={reverse('core:rest',kwargs={'m' : model, "pk" : pk })}{ '' if not params else add_json_params(params)}
                hx-trigger="{make_signal_from_model(model,pk)} from:body"''')

def rest_refresh(model,params=None):
    return SafeString(f''' hx-get={reverse('core:rest',kwargs={'m' : model})}{ None if not params else add_json_params(params)}
                hx-trigger="{make_signal_from_model(model)} from:body"''')

def default(o):
    if isinstance(o, (datetime.date, datetime.datetime)):
        return o.isoformat()
    return str(o)

def dumps(obj):
    return SafeString(json.dumps(
            obj,
            default=default
            ))

def environment(**options):
    env = Environment(**options)
    env.globals.update(
        {
            "static": static,
            "url": reverse,
            "random_id": random_id,
            "crispy": crispy,
            "len": len,
            "url_translate": url_translate,
            "_": _,
            "getattr": getattr,
            "print": print,
            "dumps": dumps,
            "add_json_params": add_json_params,
            "rest_pk_refresh" : rest_pk_refresh,
            "rest_refresh" : rest_refresh
        }
    )
    return env
