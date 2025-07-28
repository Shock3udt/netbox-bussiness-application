from netbox.search import SearchIndex
from .models import (
    BusinessApplication, TechnicalService, EventSource, Event,
    Maintenance, ChangeType, Change, Incident
)

class BusinessApplicationIndex(SearchIndex):
    model = BusinessApplication
    fields = (
        ('name', 100),
        ('appcode', 60),
        ('owner', 1000),
        ('delegate', 2000)
    )

class TechnicalServiceIndex(SearchIndex):
    model = TechnicalService
    fields = (
        ('name', 100),
    )

class EventSourceIndex(SearchIndex):
    model = EventSource
    fields = (
        ('name', 100),
        ('description', 500),
    )

class EventIndex(SearchIndex):
    model = Event
    fields = (
        ('message', 100),
        ('dedup_id', 200),
        ('status', 500),
        ('criticallity', 500),
    )

class MaintenanceIndex(SearchIndex):
    model = Maintenance
    fields = (
        ('description', 100),
        ('status', 200),
        ('contact', 300),
    )

class ChangeTypeIndex(SearchIndex):
    model = ChangeType
    fields = (
        ('name', 100),
        ('description', 500),
    )

class ChangeIndex(SearchIndex):
    model = Change
    fields = (
        ('description', 100),
    )

class IncidentIndex(SearchIndex):
    model = Incident
    fields = (
        ('title', 100),
        ('description', 200),
        ('status', 300),
        ('severity', 300),
        ('reporter', 400),
        ('commander', 400),
    )

indexes = [
    BusinessApplicationIndex,
    TechnicalServiceIndex,
    EventSourceIndex,
    EventIndex,
    MaintenanceIndex,
    ChangeTypeIndex,
    ChangeIndex,
    IncidentIndex,
]