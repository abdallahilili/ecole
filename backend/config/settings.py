"""
Configuration du projet Gestion d'Ecole Privee.
Noms francais partout (modeles, colonnes, URLs, parametres DRF), sauf les
attributs imposes par Django/DRF/SimpleJWT (password, is_active,
last_login), documentes comme exceptions.
"""

from pathlib import Path
from datetime import timedelta
import os
import sys

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DEBUG = os.getenv("DEBUG", "1") == "1"
EN_TEST = "test" in sys.argv

# Cle secrete : tolerance en developpement uniquement. En production (DEBUG=0)
# une cle absente, courte ou d'exemple est refusee au demarrage.
CLE_SECRETE = os.getenv("CLE_SECRETE", "")
if not CLE_SECRETE:
    if not DEBUG:
        raise ImproperlyConfigured("CLE_SECRETE est obligatoire en production (DEBUG=0).")
    CLE_SECRETE = "cle-de-developpement-uniquement-a-remplacer-avant-la-mise-en-production"
elif not DEBUG and (len(CLE_SECRETE) < 32 or "change-moi" in CLE_SECRETE.lower()):
    raise ImproperlyConfigured(
        "CLE_SECRETE trop courte ou d'exemple : generez-en une de 32 caracteres minimum "
        "(python -c \"import secrets; print(secrets.token_urlsafe(50))\")."
    )
SECRET_KEY = CLE_SECRETE

# Hotes autorises (separes par des virgules). Ex. en production : ecole.exemple.mr
ALLOWED_HOSTS = [h.strip() for h in os.getenv("HOTES_AUTORISES", "localhost,127.0.0.1,[::1]").split(",") if h.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "apps.commun",
    "apps.utilisateurs",
    "apps.referentiels",
    "apps.etudiants",
    "apps.professeurs",
    "apps.scolarite",
    "apps.presences",
    "apps.evaluations",
    "apps.emplois_du_temps",
    "apps.remuneration",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",   # fichiers statiques de l'administration, sans serveur web dedie
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

UTILISER_SQLITE = os.getenv("UTILISER_SQLITE", "0") == "1"

if UTILISER_SQLITE:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": os.getenv("BD_NOM", "ecole"),
            "USER": os.getenv("BD_UTILISATEUR", "root"),
            "PASSWORD": os.getenv("BD_MOT_DE_PASSE", ""),
            "HOST": os.getenv("BD_HOTE", "127.0.0.1"),
            "PORT": os.getenv("BD_PORT", "3306"),
            "OPTIONS": {"charset": "utf8mb4"},
        }
    }

AUTH_USER_MODEL = "utilisateurs.Utilisateur"

# Politique de mot de passe (appliquee a la creation, la reinitialisation et le changement).
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Africa/Nouakchott"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"          # python manage.py collectstatic
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"                 # photos des etudiants et professeurs
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "apps.commun.pagination.PaginationStandard",
    "PAGE_SIZE": 20,
    "SEARCH_PARAM": "recherche",
    "ORDERING_PARAM": "tri",
    "EXCEPTION_HANDLER": "apps.commun.exceptions.gestionnaire_exceptions",
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
    # Limitation des essais de connexion (par adresse IP) ; assouplie pendant les tests automatiques.
    "DEFAULT_THROTTLE_RATES": {
        "connexion": "10000/min" if EN_TEST else "10/min",
        "rafraichir": "10000/min" if EN_TEST else "60/min",
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),   # renouvele automatiquement par le frontend
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

ORIGINES_CORS = os.getenv(
    "ORIGINES_CORS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",")
CORS_ALLOWED_ORIGINS = [o.strip() for o in ORIGINES_CORS if o.strip()]

FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

# --- Durcissement en production (DEBUG=0) ---------------------------------
if not DEBUG:
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"
    SECURE_REFERRER_POLICY = "same-origin"
    # FORCER_HTTPS=1 des que le site est servi en HTTPS (recommande) : redirection, cookies securises, HSTS.
    if os.getenv("FORCER_HTTPS", "0") == "1":
        SECURE_SSL_REDIRECT = True
        SESSION_COOKIE_SECURE = True
        CSRF_COOKIE_SECURE = True
        SECURE_HSTS_SECONDS = 31536000
        SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")   # derriere un proxy inverse (nginx, IIS...)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "{asctime} {levelname} {name} : {message}", "style": "{"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "simple"}},
    "root": {"handlers": ["console"], "level": "WARNING"},
    "loggers": {
        "apps": {"handlers": ["console"], "level": "INFO", "propagate": False},
        # Les refus metier (400/403) sont normaux : on ne journalise que les vraies erreurs serveur.
        "django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False},
    },
}

# Logo de l'ecole imprime sur les PDF (chemin absolu d'un PNG/JPG, optionnel).
LOGO_ECOLE = os.getenv("LOGO_ECOLE", "")

# WhatsApp Business Platform (API officielle Meta) - OPTIONNEL. Sans ces
# variables, les notifications restent en file d'attente et le personnel
# peut les envoyer via un lien wa.me pre-rempli. Ces secrets ne sont
# JAMAIS exposes au frontend.
WHATSAPP_JETON = os.getenv("WHATSAPP_JETON", "")
WHATSAPP_ID_NUMERO = os.getenv("WHATSAPP_ID_NUMERO", "")
WHATSAPP_MODELE = os.getenv("WHATSAPP_MODELE", "")
WHATSAPP_LANGUE = os.getenv("WHATSAPP_LANGUE", "fr")
WHATSAPP_VERSION_API = os.getenv("WHATSAPP_VERSION_API", "v21.0")
WHATSAPP_URL_API = os.getenv("WHATSAPP_URL_API", "https://graph.facebook.com")
WHATSAPP_JETON_VERIFICATION = os.getenv("WHATSAPP_JETON_VERIFICATION", "")
WHATSAPP_SECRET_APPLICATION = os.getenv("WHATSAPP_SECRET_APPLICATION", "")
WHATSAPP_MAX_TENTATIVES = int(os.getenv("WHATSAPP_MAX_TENTATIVES", "3"))
