from django.db import models
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex


class Document(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()           # extracted text for FTS
    doc_type = models.CharField(max_length=50)
    file_data = models.BinaryField(null=True, blank=True)   # actual file bytes
    file_name = models.CharField(max_length=255, null=True, blank=True)
    uploaded_by = models.CharField(max_length=100, default='contributor')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    search_vector = SearchVectorField(null=True, blank=True)

    class Meta:
        indexes = [GinIndex(fields=['search_vector'])]

    def __str__(self):
        return self.title
    