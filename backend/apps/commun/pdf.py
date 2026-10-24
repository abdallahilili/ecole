"""Utilitaires PDF partages (ReportLab) : entete d'etablissement, tableaux
et reponse HTTP. Polices standard (Latin) : les noms doivent etre saisis
en caracteres latins."""

import io
import os
from xml.sax.saxutils import escape

from django.conf import settings
from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .parametres import lire_parametre

COULEUR_ENTETE = colors.HexColor("#1d4e5f")
COULEUR_FOND = colors.HexColor("#eef1f3")

_styles = getSampleStyleSheet()
STYLE_NORMAL = ParagraphStyle("normal", parent=_styles["Normal"], fontSize=9, leading=11)
STYLE_PETIT = ParagraphStyle("petit", parent=STYLE_NORMAL, fontSize=8, leading=10)
STYLE_TITRE = ParagraphStyle("titre", parent=_styles["Title"], fontSize=15, leading=18, spaceAfter=6)
STYLE_CENTRE = ParagraphStyle("centre", parent=STYLE_NORMAL, alignment=1)


def p(valeur, style=STYLE_NORMAL):
    """Paragraphe avec echappement XML (les donnees saisies ne sont jamais du balisage)."""
    return Paragraph(escape("" if valeur is None else str(valeur)), style)


def gras(valeur, style=STYLE_NORMAL):
    return Paragraph(f"<b>{escape('' if valeur is None else str(valeur))}</b>", style)


def multiligne(*valeurs, style=STYLE_NORMAL):
    """Plusieurs lignes dans une meme cellule (chaque valeur est echappee)."""
    return Paragraph("<br/>".join(escape(str(v)) for v in valeurs), style)


def chemin_logo():
    chemin = getattr(settings, "LOGO_ECOLE", "")
    return chemin if chemin and os.path.isfile(chemin) else None


def entete_etablissement():
    """Bloc d'entete : logo (si fourni), lignes officielles et nom de l'ecole."""
    bloc = [
        p("Republique Islamique de Mauritanie", STYLE_CENTRE),
        p("Honneur - Fraternite - Justice", STYLE_CENTRE),
        p(lire_parametre("entete_ministere"), STYLE_CENTRE),
        p(lire_parametre("entete_region"), STYLE_CENTRE),
        gras(lire_parametre("nom_etablissement"), STYLE_CENTRE),
    ]
    telephone = lire_parametre("telephone_etablissement")
    if telephone:
        bloc.append(p(f"Tel : {telephone}", STYLE_CENTRE))
    logo = chemin_logo()
    if logo:
        image = Image(logo, width=2.2 * cm, height=2.2 * cm)
        tableau = Table([[bloc, image]], colWidths=[None, 2.6 * cm])
        tableau.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
        return [tableau, Spacer(1, 6)]
    return bloc + [Spacer(1, 6)]


def style_tableau(entete=True, grille=True):
    styles = [
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if grille:
        styles.append(("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#9aa5ad")))
    if entete:
        styles += [
            ("BACKGROUND", (0, 0), (-1, 0), COULEUR_FOND),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]
    return TableStyle(styles)


def _filigrane(texte):
    def dessiner(canvas, document):
        largeur, hauteur = document.pagesize
        canvas.saveState()
        canvas.setFont("Helvetica-Bold", 72)
        canvas.setFillColor(colors.Color(0.82, 0.82, 0.82, alpha=0.45))
        canvas.translate(largeur / 2, hauteur / 2)
        canvas.rotate(45)
        canvas.drawCentredString(0, 0, texte)
        canvas.restoreState()
    return dessiner


def construire_pdf(elements, paysage=False, titre="Document", filigrane=None):
    tampon = io.BytesIO()
    taille = landscape(A4) if paysage else A4
    document = SimpleDocTemplate(
        tampon, pagesize=taille, title=titre,
        leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=1.3 * cm, bottomMargin=1.3 * cm,
    )
    if filigrane:
        dessiner = _filigrane(filigrane)
        document.build(elements, onFirstPage=dessiner, onLaterPages=dessiner)
    else:
        document.build(elements)
    return tampon.getvalue()


def reponse_pdf(octets, nom_fichier):
    reponse = HttpResponse(octets, content_type="application/pdf")
    reponse["Content-Disposition"] = f'inline; filename="{nom_fichier}"'
    return reponse
