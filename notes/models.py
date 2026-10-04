from django.db import models
from django.conf import settings

# Create your models here.
class Tag(models.Model):
    """A per-user label. Names are normalised (trimmed, lower-cased) by the serializer."""
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete = models.CASCADE, related_name = "tags")
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['owner', 'name'], name='unique_tag_name_per_user')
        ]

    def __str__(self):
        return self.name

class Note(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete = models.CASCADE, related_name = 'notes')
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)
    tags = models.ManyToManyField(Tag, related_name='notes', blank=True)
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['-updated_at'], name='note_ownder_arch_upd_idx')
        ]

    def __str__(self):
        return self.title

class NoteShare(models.Model):
    class Permission(models.TextChoices):
        VIEW = 'view', 'View'
        EDIT = 'edit', 'Edit'
    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name = 'shares')
    shared_with = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='note_shares')
    permission = models.CharField(max_length=10, choices=Permission.choices, default=Permission.VIEW)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']
        constraints = [
            models.UniqueConstraint(fields=['note', 'shared_with'], name='unique_note_share_per_user')
        ]

    def __str__(self):
        return f"{self.note.title} shared with {self.shared_with.username} ({self.permission})"
