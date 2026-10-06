import django_filters

from .models import Note


class NoteFilter(django_filters.FilterSet):
    """
    ?tag=work,ideas          notes having ANY of these tags
    ?updated_after=2026-01-01T00:00:00Z
    ?updated_before=...
    (?archived and ?search are handled by the view / SearchFilter.)
    """

    tag = django_filters.CharFilter(method="filter_tag")
    updated_after = django_filters.IsoDateTimeFilter(field_name="updated_at", lookup_expr="gte")
    updated_before = django_filters.IsoDateTimeFilter(field_name="updated_at", lookup_expr="lte")

    class Meta:
        model = Note
        fields = []

    def filter_tag(self, queryset, name, value):
        names = [v.strip().lower() for v in value.split(",") if v.strip()]
        if not names:
            return queryset
        return queryset.filter(tags__name__in=names).distinct()
