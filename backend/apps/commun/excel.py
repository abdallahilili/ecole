"""Utilitaires Excel partages (import/export)."""

import io

import openpyxl
from django.http import HttpResponse

from .exceptions import ErreurMetier
from .langue import est_arabe

TYPE_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def orienter_feuille(feuille):
    """Feuille de droite a gauche quand l'interface est en arabe."""
    feuille.sheet_view.rightToLeft = est_arabe()


def reponse_xlsx(classeur, nom_fichier):
    tampon = io.BytesIO()
    classeur.save(tampon)
    reponse = HttpResponse(tampon.getvalue(), content_type=TYPE_XLSX)
    reponse["Content-Disposition"] = f'attachment; filename="{nom_fichier}"'
    return reponse


TAILLE_MAX_FICHIER = 5 * 1024 * 1024


def neutraliser_formule(valeur):
    """Protege contre l'injection de formules : une cellule texte qui commence par
    = + - @ serait executee comme formule par Excel (donnees saisies par des tiers)."""
    if isinstance(valeur, str) and valeur[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + valeur
    return valeur


def lire_classeur(fichier):
    if fichier is None:
        raise ErreurMetier("Aucun fichier recu (champ 'fichier' attendu).")
    if getattr(fichier, "size", 0) > TAILLE_MAX_FICHIER:
        raise ErreurMetier("Fichier trop volumineux (5 Mo maximum).")
    try:
        return openpyxl.load_workbook(fichier, data_only=True)
    except Exception:
        raise ErreurMetier("Fichier Excel illisible ou corrompu.")


def texte(valeur):
    """Valeur de cellule -> chaine nettoyee ('' si vide)."""
    return "" if valeur is None else str(valeur).strip()
