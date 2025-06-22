from django.urls import path, include
from utilities.urls import get_model_urls

from . import views

urlpatterns = [
    # Business Application URLs
    path('business-application/', views.BusinessApplicationListView.as_view(), name='businessapplication_list'),
    path('business-application/<int:pk>/', views.BusinessApplicationDetailView.as_view(), name='businessapplication_detail'),
    path('business-application/add/', views.BusinessApplicationCreateView.as_view(), name='businessapplication_add'),
    path('business-application/<int:pk>/edit/', views.BusinessApplicationEditView.as_view(), name='businessapplication_edit'),
    path('business-application/<int:pk>/delete/', views.BusinessApplicationDeleteView.as_view(), name='businessapplication_delete'),
    path('business-application/<int:pk>/', include(get_model_urls('business_application', 'businessapplication'))),

    # Technical Service URLs
    path('technical-service/', views.TechnicalServiceListView.as_view(), name='technicalservice_list'),
    path('technical-service/<int:pk>/', views.TechnicalServiceDetailView.as_view(), name='technicalservice_detail'),
    path('technical-service/add/', views.TechnicalServiceCreateView.as_view(), name='technicalservice_add'),
    path('technical-service/<int:pk>/edit/', views.TechnicalServiceEditView.as_view(), name='technicalservice_edit'),
    path('technical-service/<int:pk>/delete/', views.TechnicalServiceDeleteView.as_view(), name='technicalservice_delete'),
    path('technical-service/<int:pk>/', include(get_model_urls('business_application', 'technicalservice'))),

    # Event Source URLs
    path('event-source/', views.EventSourceListView.as_view(), name='eventsource_list'),
    path('event-source/<int:pk>/', views.EventSourceDetailView.as_view(), name='eventsource_detail'),
    path('event-source/add/', views.EventSourceCreateView.as_view(), name='eventsource_add'),
    path('event-source/<int:pk>/edit/', views.EventSourceEditView.as_view(), name='eventsource_edit'),
    path('event-source/<int:pk>/delete/', views.EventSourceDeleteView.as_view(), name='eventsource_delete'),
    path('event-source/<int:pk>/', include(get_model_urls('business_application', 'eventsource'))),

    # Event URLs
    path('event/', views.EventListView.as_view(), name='event_list'),
    path('event/<int:pk>/', views.EventDetailView.as_view(), name='event_detail'),
    path('event/add/', views.EventCreateView.as_view(), name='event_add'),
    path('event/<int:pk>/edit/', views.EventEditView.as_view(), name='event_edit'),
    path('event/<int:pk>/delete/', views.EventDeleteView.as_view(), name='event_delete'),
    path('event/<int:pk>/', include(get_model_urls('business_application', 'event'))),

    # Maintenance URLs
    path('maintenance/', views.MaintenanceListView.as_view(), name='maintenance_list'),
    path('maintenance/<int:pk>/', views.MaintenanceDetailView.as_view(), name='maintenance_detail'),
    path('maintenance/add/', views.MaintenanceCreateView.as_view(), name='maintenance_add'),
    path('maintenance/<int:pk>/edit/', views.MaintenanceEditView.as_view(), name='maintenance_edit'),
    path('maintenance/<int:pk>/delete/', views.MaintenanceDeleteView.as_view(), name='maintenance_delete'),
    path('maintenance/<int:pk>/', include(get_model_urls('business_application', 'maintenance'))),

    # Change Type URLs
    path('change-type/', views.ChangeTypeListView.as_view(), name='changetype_list'),
    path('change-type/<int:pk>/', views.ChangeTypeDetailView.as_view(), name='changetype_detail'),
    path('change-type/add/', views.ChangeTypeCreateView.as_view(), name='changetype_add'),
    path('change-type/<int:pk>/edit/', views.ChangeTypeEditView.as_view(), name='changetype_edit'),
    path('change-type/<int:pk>/delete/', views.ChangeTypeDeleteView.as_view(), name='changetype_delete'),
    path('change-type/<int:pk>/', include(get_model_urls('business_application', 'changetype'))),

    # Change URLs
    path('change/', views.ChangeListView.as_view(), name='change_list'),
    path('change/<int:pk>/', views.ChangeDetailView.as_view(), name='change_detail'),
    path('change/add/', views.ChangeCreateView.as_view(), name='change_add'),
    path('change/<int:pk>/edit/', views.ChangeEditView.as_view(), name='change_edit'),
    path('change/<int:pk>/delete/', views.ChangeDeleteView.as_view(), name='change_delete'),
    path('change/<int:pk>/', include(get_model_urls('business_application', 'change'))),

    # Calendar URL
    path('calendar/', views.CalendarView.as_view(), name='calendar_view'),
]
