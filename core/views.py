from django.http import JsonResponse
from django.db import connection

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
