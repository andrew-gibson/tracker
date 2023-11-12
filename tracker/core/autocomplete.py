from .utils import to_dict
from django.db.models import Q, Field


class belongs_to:
    @classmethod
    def belongs_to_user(cls, request):
        return cls.objects

def get_autocompletes(model):
    return [
        x
        for x in model._meta.get_fields()
        if isinstance(x, (Field,))
        and x.related_model
        and hasattr(x.related_model, "text_search_trigger")
    ]

class _AutoComplete:

    # refactor back to just one query
    # ending in space -- no match, create fake new one
    # not ending in space -- always create fake new one unless it duplicates i.e. cursor was right at the end of the word
    # add warning for one to many which has multiple matches

    @classmethod
    def ac(cls, request, query="", variant=None, filter_qs=None):
        if not isinstance(query, (tuple, list)):
            query = [query]
        q = Q()
        for _ in query:
            if _.endswith(" "):
                q.add(Q(**{f"{cls.search_field}__iexact":_.strip()}), Q.OR)
            else:
                q.add(Q(**{f"{cls.search_field}__icontains":_}), Q.OR)
        qs = cls.belongs_to_user(request).filter(q).distinct()
        if filter_qs:
            qs = qs.filter(filter_qs)

        return [to_dict(x, field_list=[f"{cls.search_field}", "id"]) for x in qs]


def AutoComplete(trigger,hex_color,search_field="name"):
    rgba = f"rgba{tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4)) + (0.3,)}"
    return type(f"AutoComplete{hex_color}",
                (_AutoComplete,),
                {
                    "text_search_trigger": trigger,
                    "trigger_color": rgba,
                    "search_field" : search_field
                })
