from django.urls import path
from . import views

urlpatterns = [path("", views.ScriptsView.as_view(), name="index"),
               path("script/<int:pk>", views.ScriptView.as_view(), name="script")]
