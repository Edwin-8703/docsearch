from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('upload/', views.upload, name='upload'),
    path('upload/success/<int:pk>/', views.upload_success, name='upload_success'),
    path('search/', views.search, name='search'),
    path('documents/', views.document_list, name='document_list'),
    path('documents/<int:pk>/', views.detail, name='detail'),
    path('documents/<int:pk>/download/', views.download, name='download'),
    path('documents/<int:pk>/preview/', views.preview, name='preview'),
]