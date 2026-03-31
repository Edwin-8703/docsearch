from django.core.management.base import BaseCommand
from documents.models import Document
from django.contrib.postgres.search import SearchVector


class Command(BaseCommand):
    help = 'Update search vectors for all documents'

    def handle(self, *args, **kwargs):
        self.stdout.write('Updating search vectors...')
        Document.objects.filter(search_vector=None).update(
            search_vector=(
                SearchVector('title', weight='A', config='english') +
                SearchVector('doc_type', weight='B', config='english') +
                SearchVector('content', weight='C', config='english')
            )
        )
        count = Document.objects.exclude(search_vector=None).count()
        self.stdout.write(self.style.SUCCESS(f'Done! {count} documents indexed.'))