from django_readers import qs


def produce_repr(obj):
    return obj.name


name_repr = {"repr" : (qs.include_fields("name"), produce_repr)}
