from django.contrib import admin
from .models import BusinessApplication

@admin.register(BusinessApplication)
class BusinessApplicationAdmin(admin.ModelAdmin):
    list_display = ('appcode', 'name', 'owner', 'delegate')
    search_fields = ('appcode', 'name', 'owner')
