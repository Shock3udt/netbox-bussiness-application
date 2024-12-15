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
            | Q(appcode__icontains=value)
        )
        return queryset.filter(qs_filter)

    class Meta:
        model = BusinessApplication
        fields = ['appcode', 'name', 'owner', 'delegate']
