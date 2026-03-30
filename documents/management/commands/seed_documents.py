from django.core.management.base import BaseCommand
from documents.models import Document
from django.contrib.postgres.search import SearchVector
import io


class Command(BaseCommand):
    help = 'Seed 500 health documents from PubMed as PDF files'

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=500)
        parser.add_argument('--clear', action='store_true')

    def handle(self, *args, **kwargs):
        count = kwargs['count']
        clear = kwargs['clear']

        if clear:
            Document.objects.all().delete()
            self.stdout.write('Cleared existing documents.')

        self.stdout.write('Loading PubMed dataset from Hugging Face...')

        try:
            from datasets import load_dataset
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib.units import cm
        except ImportError:
            self.stdout.write(self.style.ERROR('Run: pip install datasets reportlab'))
            return

        try:
            dataset = load_dataset(
                'ccdv/pubmed-summarization',
                'document',
                split='train',
                trust_remote_code=True
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to load dataset: {e}'))
            return

        self.stdout.write(f'Dataset loaded. Seeding {count} PDF documents...')

        styles = getSampleStyleSheet()
        created = 0

        for i, item in enumerate(dataset):
            if created >= count:
                break

            title = f"Medical Article {i+1}"
            content = item.get('article', '') or ''
            abstract = item.get('abstract', '') or ''

            if len(content.split()) < 500:
                continue

            full_content = content
            if abstract:
                full_content = f"Abstract:\n{abstract}\n\n{content}"

            # Generate PDF from content
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(
                buffer, pagesize=A4,
                rightMargin=2*cm, leftMargin=2*cm,
                topMargin=2*cm, bottomMargin=2*cm
            )
            story = []
            story.append(Paragraph(title, styles['Title']))
            story.append(Spacer(1, 0.5*cm))

            for para in full_content.split('\n'):
                if para.strip():
                    try:
                        story.append(Paragraph(para.strip(), styles['Normal']))
                        story.append(Spacer(1, 0.2*cm))
                    except Exception:
                        continue

            doc.build(story)
            pdf_bytes = buffer.getvalue()

            document = Document(
                title=title[:255],
                content=full_content,
                doc_type='pdf',
                file_data=pdf_bytes,
                file_name=f"medical_article_{i+1}.pdf",
                uploaded_by='huggingface/pubmed',
            )
            document.save()
            created += 1

            if created % 50 == 0:
                self.stdout.write(f'  {created}/{count} documents created...')

        self.stdout.write('Updating search vectors...')
        Document.objects.filter(search_vector=None).update(
            search_vector=(
                SearchVector('title', weight='A', config='english') +
                SearchVector('doc_type', weight='B', config='english') +
                SearchVector('content', weight='C', config='english')
            )
        )

        self.stdout.write(self.style.SUCCESS(f'Done! {created} PDF documents seeded and indexed.'))