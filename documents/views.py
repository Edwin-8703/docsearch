
from pydoc import doc

from django.shortcuts import get_object_or_404
from django.http import FileResponse, HttpResponse
import io
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchHeadline
from django.db.models import F
from .models import Document
from .utils import extract_text, export_document
from django.shortcuts import render, redirect, get_object_or_404


def home(request):
    total = Document.objects.count()
    return render(request, 'documents/home.html', {'total': total})


# ─── CONTRIBUTOR: UPLOAD ──────────────────────────────────────────────────────

def upload(request):
    if request.method == 'POST':
        uploaded_file = request.FILES.get('file')
        title = request.POST.get('title', uploaded_file.name)
        uploaded_by = request.POST.get('uploaded_by', 'contributor')

        if not uploaded_file:
            return render(request, 'documents/upload.html', {'error': 'Please select a file.'})

        # 1️⃣ Read file bytes into memory
        file_bytes = uploaded_file.read()

        # 2️⃣ Determine file extension
        ext = uploaded_file.name.rsplit('.', 1)[-1].lower()

        # 3️⃣ Extract text for searchable formats only
        content = ""
        try:
            if ext == 'pdf':
                content = extract_pdf(io.BytesIO(file_bytes))
            elif ext == 'docx':
                content = extract_docx(io.BytesIO(file_bytes))
            elif ext in ['csv']:
                content = pd.read_csv(io.BytesIO(file_bytes)).to_string()
            elif ext in ['xlsx']:
                content = pd.read_excel(io.BytesIO(file_bytes)).to_string()
        except Exception:
            content = ""

        # 4️⃣ Save everything in the database
        doc = Document.objects.create(
            title=title,
            file_data=file_bytes,          # store raw bytes in DB
            file_name=uploaded_file.name,  # original filename
            doc_type=ext,
            content=content,
            uploaded_by=uploaded_by
        )
        _update_search_vector(doc)
        
        # 5️⃣ Redirect to success page
        return redirect('upload_success', pk=doc.pk)

    # GET request → render upload form
    return render(request, 'documents/upload.html')

def upload_success(request, pk):
    doc = get_object_or_404(Document, pk=pk)
    return render(request, 'documents/upload_success.html', {'doc': doc})


# ─── SEEKER: SEARCH ───────────────────────────────────────────────────────────

def search(request):
    query = request.GET.get('q', '').strip()
    results = []
    count = 0

    if query:
        search_query = SearchQuery(query, config='english')

        results = Document.objects.filter(
            search_vector=search_query
        ).annotate(
            rank=SearchRank('search_vector', search_query),
            headline=SearchHeadline(
                'content',
                search_query,
                start_sel='<mark>',
                stop_sel='</mark>',
                max_words=50,
                min_words=20,
            )
        ).order_by('-rank')

        count = results.count()

    return render(request, 'documents/search.html', {
        'query': query,
        'results': results,
        'count': count,
    })


# ─── SEEKER: DOWNLOAD ─────────────────────────────────────────────────────────

def download(request, pk):
    doc = get_object_or_404(Document, pk=pk)
    fmt = request.GET.get('format', 'original')

    if fmt == 'original' and doc.file_data:
        content_types = {
            'pdf': 'application/pdf',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'txt': 'text/plain',
            'csv': 'text/csv',
        }
        content_type = content_types.get(doc.doc_type, 'application/octet-stream')
        file_bytes = bytes(doc.file_data)
        response = HttpResponse(file_bytes, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{doc.file_name}"'
        return response

    return export_document(doc, fmt)

# ─── DOCUMENT DETAIL ──────────────────────────────────────────────────────────

def detail(request, pk):
    doc = get_object_or_404(Document, pk=pk)
    return render(request, 'documents/detail.html', {'doc': doc})


# ─── ALL DOCUMENTS ────────────────────────────────────────────────────────────

def document_list(request):
    docs = Document.objects.order_by('-uploaded_at')
    return render(request, 'documents/list.html', {'docs': docs})


# ─── HELPER ───────────────────────────────────────────────────────────────────

def _update_search_vector(doc):
    from django.contrib.postgres.search import SearchVector
    Document.objects.filter(pk=doc.pk).update(
        search_vector=(
            SearchVector('title', weight='A', config='english') +
            SearchVector('doc_type', weight='B', config='english') +
            SearchVector('content', weight='C', config='english')
        )
    )
def preview(request, pk):
    doc = get_object_or_404(Document, pk=pk)

    if not doc.file_data:
        return HttpResponse("No file data", status=404)

    content_types = {
        'pdf': 'application/pdf',
        'txt': 'text/plain',
        'csv': 'text/csv',
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'webp': 'image/webp',
    }

    content_type = content_types.get(doc.doc_type, 'application/octet-stream')
    response = HttpResponse(bytes(doc.file_data), content_type=content_type)

    # 🔥 KEY FIX: control preview vs download
    if doc.doc_type in ['pdf', 'txt', 'csv', 'png', 'jpg', 'jpeg', 'gif', 'webp']:
        response['Content-Disposition'] = f'inline; filename="{doc.file_name}"'
    else:
        # DOC, DOCX, XLSX → force download
        response['Content-Disposition'] = f'attachment; filename="{doc.file_name}"'

    return response



