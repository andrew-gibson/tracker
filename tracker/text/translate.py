from django.utils.functional import lazy
from django.utils.translation import get_language

lang_map = {
    "en-us" : "en",
    "en" : "en",
    "fr" : "fr",
}

def other_lang():
  if get_language() == "en":
    return "fr"
  return "en"

def gettext_lazy(key : str) -> str:
  text = keys.get(key,False)
  return text[ lang_map[get_language()] ] if text else key

gettext_lazy = lazy(gettext_lazy, str)
keys =  {}
