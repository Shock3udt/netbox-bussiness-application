from django.db.models import Q
from netbox.filtersets import NetBoxModelFilterSet
from .models import BusinessApplication

class BusinessApplicationFilter(NetBoxModelFilterSet):
    """
    Filters for the BusinessApplication model.
    """

    def search(self, queryset, name, value):
        if not value:
            return queryset
        qs_filter = (
            Q(name__icontains=value)
            | Q(appcode_icontains=value)
        )
        return queryset.filter(qs_filter)

    class Meta:
        model = BusinessApplication
        fields = ['name', 'appcode', 'owner', 'delegate']
