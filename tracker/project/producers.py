from django_readers import qs


def produce_repr(obj):
    return obj.name


name_repr = {"repr" : (qs.include_fields("name"), produce_repr)}

stream_repr = { "repr": (
                qs.include_fields("name", "work_items"),
                lambda obj: f"{obj.name} ({obj.work_items.count()})",
                ),
              }
