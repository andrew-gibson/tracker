from django.templatetags.static import static
from django.urls import reverse
from jinja2 import Environment,  pass_context
import random
import string
from urllib import parse
from crispy_forms.utils import render_crispy_form
from core.models import to_dict
from text.translate import gettext_lazy as _, other_lang
from django.utils.translation import activate

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
  return   ''.join(random.choice(letters) for i in range(10)) 

def url_session(view_name,session=None, kwargs=None ):
    url = reverse(view_name, kwargs=kwargs)
    return "?".join(url, parse.urlencode(session) )


def environment(**options):
    env = Environment(**options)
    env.globals.update({
        'static': static,
        'url': reverse,
        'random_id' : random_id,
        "crispy" : crispy,
        "to_dict" : to_dict,
        "url_translate" : url_translate,
        "_" : _,
        "getattr" : getattr,
        "print" : print,
    })
    return env
