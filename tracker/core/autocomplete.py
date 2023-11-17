import re
from .utils import to_dict
from django.db.models import Q, Field


class belongs_to:
    @classmethod
    def belongs_to_user(cls, request):
        return cls.objects


class AutoCompleteNexus:
    @classmethod
    def find_words_from_trigger(cls, text, trigger, many=True):
        split_text = text.split(" ")
        regex = re.compile(f"\\{trigger}\\w+")
        length =  len(split_text)
        words = [
            x.replace(trigger,"") + " "
            for i, x in enumerate(split_text[0:-1])
            if re.match(regex, x) 
        ]
        if len(split_text) and split_text[-1].startswith(trigger):
            words.append(split_text[-1].replace(trigger, ""))
        if not many and len(words):
            return [words[-1]]
        return words

    @classmethod
    def get_autocompletes(cls):
        return [
            x
            for x in cls._meta.get_fields()
            if isinstance(x, (Field,))
            and x.related_model
            and hasattr(x.related_model, "text_search_trigger")
        ]

    @classmethod
    def describe_links(cls):
        autocompletes = ", ".join(
            [
                f"'{x.related_model.text_search_trigger}' for {x.related_model._meta.verbose_name}"
                for x in cls.get_autocompletes()
            ]
        )
        return f"Type: {autocompletes}"


class _AutoComplete:
    def get_autocomplete_triggers(cls):
        """return the instrcutions for self.search_field"""

    @classmethod
    def ac(cls, request, query="", variant=None, filter_qs=None):
        f = f"{cls.search_field}"

        if query == "":
            q = Q()
        elif query.endswith(" "):
            q = Q(**{f"{f}__iexact": query.strip()})
        else:
            q = Q(**{f"{f}__icontains": query})

        qs = cls.belongs_to_user(request).filter(q).distinct()

        if filter_qs:
            qs = qs.filter(filter_qs)

        if query == "":
            qs = qs[:10]

        results = [to_dict(x, field_list=[f, "id"]) for x in qs]

        if (
            (len(results) == 0 and query.endswith(" ") or not query.endswith(" "))
            and query.strip() != ""
            and not any(query.lower() == x[f].lower() for x in results)
        ):
            # not ending in space -- always create fake new one unless it
            # duplicates i.e. cursor was right at the end of the word
            results = [{f: query, "id": -1, "new": True}] + results

        return results


def AutoComplete(trigger, hex_color, search_field="name"):
    # convert hex to rgb
    rgba = f"rgba{tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4)) + (0.3,)}"
    return type(
        f"AutoComplete{hex_color}",
        (_AutoComplete,),
        {
            "text_search_trigger": trigger,
            "trigger_color": rgba,
            "search_field": search_field,
        },
    )
