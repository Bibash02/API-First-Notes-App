from django.contrib.auth import get_user_model
from django.db.models import Count, OuterRef, Subquery
from rest_framework import mixins, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .filters import NoteFilter
from .models import Note, NoteShare, Tag
from .serializers import (
    NoteSerializer,
    NoteShareSerializer,
    RegisterSerializer,
    SharedNoteSerializer,
    TagSerializer,
)

User = get_user_model()


class NoteViewSet(viewsets.ModelViewSet):
    """Notes owned by the requesting user."""

    serializer_class = NoteSerializer
    filterset_class = NoteFilter
    search_fields = ["title", "body", "tags__name"]
    ordering_fields = ["updated_at", "created_at", "title"]
    ordering = ["-updated_at"]

    def get_queryset(self):
        qs = Note.objects.filter(owner=self.request.user).prefetch_related("tags")
        if self.action == "list":
            # Archived notes are hidden by default; ?archived=true|all opts in.
            archived = self.request.query_params.get("archived", "false").lower()
            if archived == "true":
                qs = qs.filter(is_archived=True)
            elif archived == "false":
                qs = qs.filter(is_archived=False)
            elif archived != "all":
                raise ValidationError({"archived": "Use one of: true, false, all."})
        return qs

    def _set_archived(self, value):
        note = self.get_object()
        note.is_archived = value
        note.save(update_fields=["is_archived", "updated_at"])
        return Response(self.get_serializer(note).data)

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        return self._set_archived(True)

    @action(detail=True, methods=["post"])
    def unarchive(self, request, pk=None):
        return self._set_archived(False)

    @action(detail=True, methods=["get", "post"], url_path="shares")
    def shares(self, request, pk=None):
        note = self.get_object()
        if request.method == "POST":
            serializer = NoteShareSerializer(
                data=request.data, context={"request": request, "note": note}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save(note=note)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        queryset = note.shares.select_related("shared_with")
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(NoteShareSerializer(page, many=True).data)

    @action(detail=True, methods=["delete"], url_path=r"shares/(?P<share_id>\d+)")
    def unshare(self, request, pk=None, share_id=None):
        note = self.get_object()
        deleted, _ = note.shares.filter(pk=share_id).delete()
        if not deleted:
            raise NotFound("Share not found.")
        return Response(status=status.HTTP_204_NO_CONTENT)


class SharedNoteViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Notes other people shared with me. PATCH works only with 'edit' permission."""

    serializer_class = SharedNoteSerializer
    http_method_names = ["get", "patch", "head", "options"]
    search_fields = ["title", "body"]
    ordering_fields = ["updated_at", "title"]
    ordering = ["-updated_at"]
    filterset_class = None

    def get_queryset(self):
        user = self.request.user
        my_permission = NoteShare.objects.filter(
            note=OuterRef("pk"), shared_with=user
        ).values("permission")[:1]
        return (
            Note.objects.filter(shares__shared_with=user)
            .select_related("owner")
            .prefetch_related("tags")
            .annotate(my_permission=Subquery(my_permission))
        )

    def perform_update(self, serializer):
        if serializer.instance.my_permission != NoteShare.Permission.EDIT:
            raise PermissionDenied("You only have view access to this note.")
        serializer.save()


class TagViewSet(mixins.ListModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """My tags with usage counts. Deleting a tag just detaches it from notes."""

    serializer_class = TagSerializer
    search_fields = ["name"]
    ordering_fields = ["name", "notes_count"]
    ordering = ["name"]

    def get_queryset(self):
        return Tag.objects.filter(owner=self.request.user).annotate(notes_count=Count("notes"))


class RegisterView(CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {"id": user.pk, "username": user.username, "token": token.key},
            status=status.HTTP_201_CREATED,
        )
