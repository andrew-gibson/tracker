from django.utils.translation import get_language

def lang():
    return "en" if get_language() == "en-us" else "fr"

def resolve_field_to_current_lang(field):
    return f"{field}_{lang()}"
