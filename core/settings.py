"""
Django settings for core project - Université Attawoune Management System
"""

from datetime import timedelta
from pathlib import Path
from urllib.parse import urlparse

from decouple import config
from django.core.exceptions import ImproperlyConfigured

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Security settings
DJANGO_ENV = config("DJANGO_ENV", default="development").strip().lower()
if DJANGO_ENV not in {"development", "test", "production"}:
    raise ImproperlyConfigured(
        "DJANGO_ENV must be one of: development, test, production"
    )
IS_PRODUCTION = DJANGO_ENV == "production"


def required_setting(name: str) -> str:
    value = config(name, default="").strip()
    if not value:
        raise ImproperlyConfigured(f"{name} is required when DJANGO_ENV=production")
    return value


SECRET_KEY = (
    required_setting("SECRET_KEY")
    if IS_PRODUCTION
    else config("SECRET_KEY", default="django-insecure-change-in-production")
)
if IS_PRODUCTION and (SECRET_KEY.startswith("django-insecure-") or len(SECRET_KEY) < 50):
    raise ImproperlyConfigured(
        "SECRET_KEY must contain at least 50 characters and must not start with "
        "django-insecure- when DJANGO_ENV=production"
    )
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = [
    host.strip()
    for host in (
        required_setting("ALLOWED_HOSTS")
        if IS_PRODUCTION
        else config("ALLOWED_HOSTS", default="localhost,127.0.0.1")
    ).split(",")
    if host.strip()
]
if IS_PRODUCTION and not ALLOWED_HOSTS:
    raise ImproperlyConfigured("ALLOWED_HOSTS must contain a host when DJANGO_ENV=production")

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party apps
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    # Local apps
    "apps.accounts",
    "apps.university",
    "apps.academics",
    "apps.students",
    "apps.teachers",
    "apps.finance",
    "apps.scheduling",
    "apps.audit",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.audit.middleware.AuditMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"

# Database
DATABASE_URL = config("DATABASE_URL", default="")
if DATABASE_URL:
    parsed_db = urlparse(DATABASE_URL)
    if parsed_db.scheme in {"sqlite", "sqlite3"}:
        database_name = parsed_db.path
        if database_name in {"", "/", "/:memory:"}:
            database_name = ":memory:"
        elif database_name.startswith("//"):
            # sqlite:////data/db.sqlite3 → absolute path (production)
            database_name = database_name[1:]
        else:
            # sqlite:///db.sqlite3 → treat as a path relative to BASE_DIR
            database_name = BASE_DIR / database_name.lstrip("/")
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": database_name,
            }
        }
    else:
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": parsed_db.path.lstrip("/"),
                "USER": parsed_db.username or "",
                "PASSWORD": parsed_db.password or "",
                "HOST": parsed_db.hostname or "",
                "PORT": parsed_db.port or "5432",
            }
        }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# Custom User Model
AUTH_USER_MODEL = "accounts.User"

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Africa/Bamako"
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Media files
# Keep uploads beside a persistent SQLite database in production (Coolify uses
# /data/db.sqlite3), while retaining backend/media for local development.
MEDIA_URL = "/media/"
default_media_root = BASE_DIR / "media"
default_database = DATABASES["default"]
if default_database["ENGINE"] == "django.db.backends.sqlite3":
    sqlite_path = Path(str(default_database["NAME"]))
    if sqlite_path.is_absolute() and sqlite_path.parent != Path("/"):
        default_media_root = sqlite_path.parent / "media"
MEDIA_ROOT = Path(config("MEDIA_ROOT", default=str(default_media_root)))

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# REST Framework Configuration
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.core.exceptions.custom_exception_handler",
}

# JWT Configuration
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# CORS Configuration
CORS_ALLOW_ALL_ORIGINS = config(
    "CORS_ALLOW_ALL_ORIGINS", default=not IS_PRODUCTION, cast=bool
)
CORS_ALLOWED_ORIGINS = [
    origin.strip().rstrip("/")
    for origin in (
        required_setting("CORS_ALLOWED_ORIGINS")
        if IS_PRODUCTION
        else config(
            "CORS_ALLOWED_ORIGINS", default="http://localhost:5173,http://127.0.0.1:5173"
        )
    ).split(",")
    if origin.strip()
]
if IS_PRODUCTION and not CORS_ALLOWED_ORIGINS:
    raise ImproperlyConfigured(
        "CORS_ALLOWED_ORIGINS must contain an origin when DJANGO_ENV=production"
    )
CORS_ALLOW_CREDENTIALS = True

# CSRF Trusted Origins
CSRF_TRUSTED_ORIGINS = [
    origin.strip().rstrip("/")
    for origin in config(
        "CSRF_TRUSTED_ORIGINS",
        default="" if IS_PRODUCTION else "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

# Production security / reverse proxy settings (Coolify terminates HTTPS)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=IS_PRODUCTION, cast=bool)
SESSION_COOKIE_SECURE = config("SESSION_COOKIE_SECURE", default=IS_PRODUCTION, cast=bool)
CSRF_COOKIE_SECURE = config("CSRF_COOKIE_SECURE", default=IS_PRODUCTION, cast=bool)
SECURE_HSTS_SECONDS = config(
    "SECURE_HSTS_SECONDS", default=31536000 if IS_PRODUCTION else 0, cast=int
)
# Enable these only when every subdomain is owned and serves HTTPS.
SECURE_HSTS_INCLUDE_SUBDOMAINS = config(
    "SECURE_HSTS_INCLUDE_SUBDOMAINS", default=False, cast=bool
)
SECURE_HSTS_PRELOAD = config("SECURE_HSTS_PRELOAD", default=False, cast=bool)

if IS_PRODUCTION:
    if DEBUG:
        raise ImproperlyConfigured("DEBUG must be false when DJANGO_ENV=production")
    for setting_name, enabled in (
        ("SECURE_SSL_REDIRECT", SECURE_SSL_REDIRECT),
        ("SESSION_COOKIE_SECURE", SESSION_COOKIE_SECURE),
        ("CSRF_COOKIE_SECURE", CSRF_COOKIE_SECURE),
    ):
        if not enabled:
            raise ImproperlyConfigured(
                f"{setting_name} must be true when DJANGO_ENV=production"
            )
    if CORS_ALLOW_ALL_ORIGINS:
        raise ImproperlyConfigured(
            "CORS_ALLOW_ALL_ORIGINS must be false when DJANGO_ENV=production"
        )
    if SECURE_HSTS_SECONDS <= 0:
        raise ImproperlyConfigured(
            "SECURE_HSTS_SECONDS must be positive when DJANGO_ENV=production"
        )

# API Documentation
SPECTACULAR_SETTINGS = {
    "TITLE": "Université Attawoune API",
    "DESCRIPTION": "API pour la gestion universitaire",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "ENUM_NAME_OVERRIDES": {
        "TuitionPaymentMethod": "apps.finance.models.TuitionPayment.PaymentMethod",
        "DebtPaymentMethod": "apps.finance.models.DebtPayment.PaymentMethod",
        "TuitionPaymentStatus": "apps.finance.models.TuitionPayment.PaymentStatus",
        "SalaryPaymentStatus": "apps.finance.models.Salary.PaymentStatus",
        "StudentDebtStatus": "apps.finance.models.StudentDebt.DebtStatus",
        "StudentStatus": "apps.students.models.Student.Status",
        "EnrollmentStatus": "apps.students.models.Enrollment.EnrollmentStatus",
        "AttendanceStatus": "apps.students.models.Attendance.AttendanceStatus",
        "TeacherContractStatus": "apps.teachers.models.TeacherContract.ContractStatus",
    },
}
