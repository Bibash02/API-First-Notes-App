from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter

from .views import NoteViewSet, RegisterView, SharedNoteViewSet, TagViewSet

router = DefaultRouter()
router.register("notes", NoteViewSet, basename="note")
router.register("shared-notes", SharedNoteViewSet, basename="shared-note")
router.register("tags", TagViewSet, basename="tag")

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/token/", obtain_auth_token, name="token"),
] + router.urls
