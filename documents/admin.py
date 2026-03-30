from django.contrib import admin
from .models import Document

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'doc_type', 'uploaded_by', 'uploaded_at']
    search_fields = ['title', 'content']
    list_filter = ['doc_type', 'uploaded_by']