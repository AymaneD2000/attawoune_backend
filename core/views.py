import mimetypes
from pathlib import Path

from django.conf import settings
from django.db import connection
from django.http import FileResponse, Http404, JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def student_photo(request, path):
    """Serve public student photos without exposing private uploaded receipts."""
    photo_root = (Path(settings.MEDIA_ROOT) / "students" / "photos").resolve()
    requested_file = (photo_root / path).resolve()

    try:
        requested_file.relative_to(photo_root)
    except ValueError as exc:
        raise Http404 from exc

    if not requested_file.is_file():
        raise Http404

    content_type, encoding = mimetypes.guess_type(requested_file.name)
    response = FileResponse(
        requested_file.open("rb"),
        content_type=content_type or "application/octet-stream",
    )
    if encoding:
        response["Content-Encoding"] = encoding
    response["Cache-Control"] = "public, max-age=3600"
    response["X-Content-Type-Options"] = "nosniff"
    return response


def health_check(request):
    """
    Simple health check endpoint to verify the API is running and DB is accessible.
    """
    health_status = {
        'status': 'ok',
        'database': 'unknown'
    }
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            row = cursor.fetchone()
            if row:
                health_status['database'] = 'connected'
    except Exception as e:
        health_status['status'] = 'error'
        health_status['database'] = 'error'
        health_status['details'] = str(e)
        return JsonResponse(health_status, status=503)
        
    return JsonResponse(health_status)
