from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Note, NoteShare, Tag

User = get_user_model()

MAX_TAGS_PER_NOTE = 20


class TagListField(serializers.ListField):
    """
    Tags are exposed as a plain list of names: ["work", "ideas"].
    Input is normalised (trimmed, lower-cased, de-duplicated, order kept).
    """

    child = serializers.CharField(max_length=50)

    def to_representation(self, value):
        # `value` is the related manager; .all() hits the prefetch cache.
        return sorted(tag.name for tag in value.all())

    def to_internal_value(self, data):
        names = super().to_internal_value(data)
        cleaned = []
        for name in names:
            name = name.strip().lower()
            if not name:
                raise serializers.ValidationError("Tag names cannot be blank.")
            if name not in cleaned:
                cleaned.append(name)
        if len(cleaned) > MAX_TAGS_PER_NOTE:
            raise serializers.ValidationError(
                f"A note can have at most {MAX_TAGS_PER_NOTE} tags."
            )
        return cleaned


def _set_tags(note, names):
    tags = [Tag.objects.get_or_create(owner=note.owner, name=n)[0] for n in names]
    note.tags.set(tags)


class NoteSerializer(serializers.ModelSerializer):
    tags = TagListField(required=False)

    class Meta:
        model = Note
        fields = ["id", "title", "body", "tags", "is_archived", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        tag_names = validated_data.pop("tags", [])
        note = Note.objects.create(owner=self.context["request"].user, **validated_data)
        _set_tags(note, tag_names)
        return note

    def update(self, instance, validated_data):
        tag_names = validated_data.pop("tags", None)
        instance = super().update(instance, validated_data)
        if tag_names is not None:
            _set_tags(instance, tag_names)
        return instance


class TagSerializer(serializers.ModelSerializer):
    notes_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Tag
        fields = ["id", "name", "notes_count"]


class NoteShareSerializer(serializers.ModelSerializer):
    shared_with = serializers.SlugRelatedField(
        slug_field="username", queryset=User.objects.all()
    )

    class Meta:
        model = NoteShare
        fields = ["id", "shared_with", "permission", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_shared_with(self, user):
        note = self.context["note"]
        if user.pk == note.owner_id:
            raise serializers.ValidationError("You cannot share a note with yourself.")
        if note.shares.filter(shared_with=user).exists():
            raise serializers.ValidationError("This note is already shared with that user.")
        return user


class SharedNoteSerializer(serializers.ModelSerializer):
    """What a recipient sees. Only title/body are editable, and only with 'edit' permission."""

    owner = serializers.CharField(source="owner.username", read_only=True)
    permission = serializers.CharField(source="my_permission", read_only=True)
    tags = TagListField(read_only=True)

    class Meta:
        model = Note
        fields = ["id", "title", "body", "tags", "owner", "permission", "updated_at"]
        read_only_fields = ["id", "updated_at"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta:
        model = User
        fields = ["id", "username", "email", "password"]
        read_only_fields = ["id"]

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
