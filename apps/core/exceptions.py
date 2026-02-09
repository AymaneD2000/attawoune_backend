"""
Custom exception handlers for consistent API error responses.

This module provides a custom exception handler that formats all API errors
in a consistent structure:

{
    "error": {
        "code": "ERROR_CODE",
        "message": "Human readable message",
        "details": {...}  # Optional additional details
    }
}
"""

from rest_framework.views import exception_handler
from rest_framework import status
from django.http import Http404
from django.core.exceptions import PermissionDenied, ValidationError as DjangoValidationError
from rest_framework.exceptions import (
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied as DRFPermissionDenied,
    NotFound,
    MethodNotAllowed,
    ValidationError as DRFValidationError,
    Throttled,
    APIException,
)


# Error code mappings
ERROR_CODES = {
    'authentication_failed': 'AUTH_FAILED',
    'not_authenticated': 'AUTH_REQUIRED',
    'permission_denied': 'PERMISSION_DENIED',
    'not_found': 'NOT_FOUND',
    'method_not_allowed': 'METHOD_NOT_ALLOWED',
    'validation_error': 'VALIDATION_ERROR',
    'throttled': 'RATE_LIMITED',
    'server_error': 'SERVER_ERROR',
}

# Human-readable error messages in French
ERROR_MESSAGES = {
    'AUTH_FAILED': "Échec de l'authentification. Vérifiez vos identifiants.",
    'AUTH_REQUIRED': "Authentification requise. Veuillez vous connecter.",
    'PERMISSION_DENIED': "Vous n'avez pas la permission d'effectuer cette action.",
    'NOT_FOUND': "La ressource demandée n'a pas été trouvée.",
    'METHOD_NOT_ALLOWED': "Cette méthode HTTP n'est pas autorisée pour cette ressource.",
    'VALIDATION_ERROR': "Erreur de validation des données.",
    'RATE_LIMITED': "Trop de requêtes. Veuillez réessayer plus tard.",
    'SERVER_ERROR': "Une erreur interne s'est produite. Veuillez réessayer.",
}


def custom_exception_handler(exc, context):
    """
    Custom exception handler that provides consistent error responses.
    
    Args:
        exc: The exception that was raised
        context: Additional context containing the view, request, args, and kwargs
        
    Returns:
        Response object with formatted error
    """
    # Call DRF's default exception handler first
    response = exception_handler(exc, context)
    
    if response is not None:
        # Determine error code and message
        error_code = _get_error_code(exc)
        error_message = _get_error_message(exc, error_code)
        
        # Build error response
        error_data = {
            'error': {
                'code': error_code,
                'message': error_message,
            }
        }
        
        # Add details for validation errors
        details = _get_error_details(exc, response)
        if details:
            error_data['error']['details'] = details
        
        # Add status code to response data
        error_data['error']['status_code'] = response.status_code
        
        response.data = error_data
    
    return response


def _get_error_code(exc):
    """
    Get the error code based on exception type.
    
    Args:
        exc: The exception that was raised
        
    Returns:
        String error code
    """
    if isinstance(exc, AuthenticationFailed):
        return ERROR_CODES['authentication_failed']
    elif isinstance(exc, NotAuthenticated):
        return ERROR_CODES['not_authenticated']
    elif isinstance(exc, (DRFPermissionDenied, PermissionDenied)):
        return ERROR_CODES['permission_denied']
    elif isinstance(exc, (NotFound, Http404)):
        return ERROR_CODES['not_found']
    elif isinstance(exc, MethodNotAllowed):
        return ERROR_CODES['method_not_allowed']
    elif isinstance(exc, (DRFValidationError, DjangoValidationError)):
        return ERROR_CODES['validation_error']
    elif isinstance(exc, Throttled):
        return ERROR_CODES['throttled']
    elif hasattr(exc, 'code'):
        return exc.code
    else:
        return ERROR_CODES['server_error']


def _get_error_message(exc, error_code):
    """
    Get a human-readable error message.
    
    Args:
        exc: The exception that was raised
        error_code: The error code
        
    Returns:
        Human-readable error message
    """
    # Try to get custom message from exception
    if hasattr(exc, 'detail') and isinstance(exc.detail, str):
        return exc.detail
    
    # Use default message for error code
    return ERROR_MESSAGES.get(error_code, ERROR_MESSAGES['SERVER_ERROR'])


def _get_error_details(exc, response):
    """
    Extract error details from the exception.
    
    Args:
        exc: The exception that was raised
        response: The DRF response object
        
    Returns:
        Dictionary of error details or None
    """
    if isinstance(exc, (DRFValidationError, DjangoValidationError)):
        # For validation errors, include field-specific errors
        if hasattr(exc, 'detail'):
            if isinstance(exc.detail, dict):
                return _format_validation_errors(exc.detail)
            elif isinstance(exc.detail, list):
                return {'non_field_errors': exc.detail}
    
    elif isinstance(exc, Throttled):
        # Include retry information for throttled requests
        return {
            'available_in': f"{exc.wait} secondes" if exc.wait else None
        }
    
    elif hasattr(exc, 'details') and exc.details:
        return exc.details

    return None


def _format_validation_errors(errors, parent_key=''):
    """
    Format validation errors into a flat structure.
    
    Args:
        errors: Dictionary of validation errors
        parent_key: Parent key for nested fields
        
    Returns:
        Formatted error dictionary
    """
    formatted = {}
    
    for key, value in errors.items():
        full_key = f"{parent_key}.{key}" if parent_key else key
        
        if isinstance(value, dict):
            # Nested errors
            formatted.update(_format_validation_errors(value, full_key))
        elif isinstance(value, list):
            # List of error messages
            formatted[full_key] = [
                str(v) if hasattr(v, '__str__') else v 
                for v in value
            ]
        else:
            formatted[full_key] = str(value)
    
    return formatted


class APIError(APIException):
    """
    Custom API exception for domain-specific errors.
    
    Usage:
        raise APIError(
            code='CONFLICT_DETECTED',
            message='Un conflit d\'horaire a été détecté.',
            details={'time_slot': 'Lundi 08:00-10:00'},
            status_code=409
        )
    """
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = 'API_ERROR'
    default_detail = "Une erreur s'est produite."
    
    def __init__(self, code=None, message=None, details=None, status_code=None):
        self.code = code or self.default_code
        self.detail = message or self.default_detail
        self.details = details
        
        if status_code:
            self.status_code = status_code
        
        super().__init__(self.detail)


class ConflictError(APIError):
    """Exception for data conflicts (e.g., schedule conflicts)."""
    status_code = status.HTTP_409_CONFLICT
    default_code = 'CONFLICT'
    default_detail = "Un conflit a été détecté."


class ResourceNotFoundError(APIError):
    """Exception for resource not found errors."""
    status_code = status.HTTP_404_NOT_FOUND
    default_code = 'NOT_FOUND'
    default_detail = "La ressource demandée n'a pas été trouvée."


class BusinessRuleError(APIError):
    """Exception for business rule violations."""
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_code = 'BUSINESS_RULE_VIOLATION'
    default_detail = "L'opération viole une règle métier."
