"""Utilitaires PDF partages (ReportLab) : entete d'etablissement, tableaux
et reponse HTTP.

Langues : francais (polices standard) et arabe. En arabe, les textes sont traduits (traduction.py), mis en forme
(lettres reliees + ordre visuel de droite a gauche) et ecrits avec la police Amiri ; les tableaux sont inverses (la
premiere colonne est a droite). Un nom saisi en caracteres arabes dans un document francais est lui aussi ecrit avec
Amiri : les noms peuvent donc etre saisis en arabe ou en caracteres latins."""

import io
import os
import re
from xml.sax.saxutils import escape

import arabic_reshaper
from bidi.algorithm import get_display
from django.conf import settings
from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .langue import est_arabe
from .parametres import lire_parametre
from .traduction import traduire

COULEUR_ENTETE = colors.HexColor("#1d4e5f")
COULEUR_FOND = colors.HexColor("#eef1f3")

_DOSSIER_POLICES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "polices")
POLICE_ARABE = "Amiri"
POLICE_ARABE_GRAS = "Amiri-Bold"
pdfmetrics.registerFont(TTFont(POLICE_ARABE, os.path.join(_DOSSIER_POLICES, "Amiri-Regular.ttf")))
pdfmetrics.registerFont(TTFont(POLICE_ARABE_GRAS, os.path.join(_DOSSIER_POLICES, "Amiri-Bold.ttf")))
pdfmetrics.registerFontFamily(
    POLICE_ARABE, normal=POLICE_ARABE, bold=POLICE_ARABE_GRAS, italic=POLICE_ARABE, boldItalic=POLICE_ARABE_GRAS,
)

_styles = getSampleStyleSheet()
STYLE_NORMAL = ParagraphStyle("normal", parent=_styles["Normal"], fontSize=9, leading=11)
STYLE_PETIT = ParagraphStyle("petit", parent=STYLE_NORMAL, fontSize=8, leading=10)
STYLE_TITRE = ParagraphStyle("titre", parent=_styles["Title"], fontSize=15, leading=18, spaceAfter=6)
STYLE_CENTRE = ParagraphStyle("centre", parent=STYLE_NORMAL, alignment=1)

# --------------------------------------------------------------------------- texte arabe

RE_ARABE = re.compile("[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]")
_reshaper = arabic_reshaper.ArabicReshaper({"delete_harakat": False, "support_ligatures": True})


def contient_arabe(texte):
    return bool(RE_ARABE.search(texte))


# Suite de lettres latines / chiffres (avec - / : . , ' _ internes) : numeros, dates, noms latins, annees « 2026-2027 ».
RE_CHAINE_LATINE = re.compile(r"[A-Za-z0-9À-ÿ]+(?:[-/:.,'_][A-Za-z0-9À-ÿ]+)*")
RE_PROTEGE = re.compile("[-]")


def _visuel(texte):
    """Ligne logique -> ligne en ordre d'affichage (lettres reliees, ordre bidirectionnel).

    Les suites latines/numeriques sont remplacees par un seul caractere « fort gauche-droite » pendant le calcul de
    l'ordre, puis restituees : elles gardent leur ordre interne (2026-2027 ne devient jamais 2027-2026)."""
    if not contient_arabe(texte):
        return texte
    chaines = []

    def garder(trouve):
        chaines.append(trouve.group(0))
        return chr(0xE000 + len(chaines) - 1)

    protege = RE_CHAINE_LATINE.sub(garder, texte)
    visuel = get_display(_reshaper.reshape(protege), base_dir="R" if est_arabe() else "L")
    return RE_PROTEGE.sub(lambda trouve: chaines[ord(trouve.group(0)) - 0xE000], visuel)


def texte_pdf(valeur):
    """Valeur -> texte du document : traduit si la langue est l'arabe, jamais None."""
    if valeur is None:
        return ""
    return traduire(str(valeur))


_cache_styles = {}


def _style_adapte(style, gras=False):
    """Meme style mais avec la police arabe ; en arabe, l'alignement a gauche devient un alignement a droite."""
    cle = (id(style), gras, est_arabe())
    if cle not in _cache_styles:
        alignement = 2 if (est_arabe() and style.alignment == 0) else style.alignment
        _cache_styles[cle] = ParagraphStyle(
            f"{style.name}-ar{'-g' if gras else ''}", parent=style,
            fontName=POLICE_ARABE_GRAS if gras else POLICE_ARABE, alignment=alignement,
        )
    return _cache_styles[cle]


class ParagrapheArabe(Paragraph):
    """Paragraphe dont le texte logique (arabe ou melange) est decoupe en lignes a la largeur disponible, puis chaque
    ligne est mise en ordre d'affichage : le retour a la ligne reste correct pour un texte de droite a gauche."""

    def __init__(self, lignes_logiques, style, gras=False):
        self._lignes_logiques = lignes_logiques      # une entree par ligne forcee (<br/>)
        self._gras = gras
        super().__init__(self._html(lignes_logiques), style)

    def _html(self, lignes):
        html = "<br/>".join(escape(ligne) for ligne in lignes)
        return f"<b>{html}</b>" if self._gras else html

    def _decouper(self, texte, largeur):
        police = POLICE_ARABE_GRAS if self._gras else POLICE_ARABE
        taille = self.style.fontSize
        lignes, courante = [], ""
        for mot in texte.split(" "):
            essai = f"{courante} {mot}" if courante else mot
            if courante and pdfmetrics.stringWidth(_visuel(essai), police, taille) > largeur:
                lignes.append(courante)
                courante = mot
            else:
                courante = essai
        lignes.append(courante)
        return lignes

    def wrap(self, largeur, hauteur):
        utile = largeur - self.style.leftIndent - self.style.rightIndent
        visuelles = []
        for ligne in self._lignes_logiques:
            visuelles += [_visuel(l) for l in self._decouper(ligne, utile)]
        Paragraph.__init__(self, self._html(visuelles), self.style)
        return super().wrap(largeur, hauteur)


def _paragraphe(valeurs, style, gras):
    textes = [texte_pdf(v) for v in valeurs]
    if est_arabe() or any(contient_arabe(t) for t in textes):
        return ParagrapheArabe(textes, _style_adapte(style, gras), gras)
    html = "<br/>".join(escape(t) for t in textes)
    return Paragraph(f"<b>{html}</b>" if gras else html, style)


def p(valeur, style=STYLE_NORMAL):
    """Paragraphe avec echappement XML (les donnees saisies ne sont jamais du balisage)."""
    return _paragraphe([valeur], style, False)


def gras(valeur, style=STYLE_NORMAL):
    return _paragraphe([valeur], style, True)


def multiligne(*valeurs, style=STYLE_NORMAL):
    """Plusieurs lignes dans une meme cellule (chaque valeur est echappee)."""
    return _paragraphe(valeurs, style, False)


# --------------------------------------------------------------------------- tableaux

_MIROIR_ALIGNEMENT = {"LEFT": "RIGHT", "RIGHT": "LEFT"}
_MIROIR_COMMANDE = {"LINEBEFORE": "LINEAFTER", "LINEAFTER": "LINEBEFORE", "LEFTPADDING": "RIGHTPADDING", "RIGHTPADDING": "LEFTPADDING"}


def _colonne(valeur, nb):
    return nb + valeur if valeur < 0 else valeur


def _commande_miroir(commande, nb):
    nom, debut, fin, *reste = commande
    c0, c1 = nb - 1 - _colonne(debut[0], nb), nb - 1 - _colonne(fin[0], nb)
    debut, fin = (min(c0, c1), debut[1]), (max(c0, c1), fin[1])
    if nom == "ALIGN" and reste:
        reste = [_MIROIR_ALIGNEMENT.get(str(reste[0]).upper(), reste[0])]
    return (_MIROIR_COMMANDE.get(nom, nom), debut, fin, *reste)


class Tableau(Table):
    """Table ReportLab sensible a la langue : en arabe, colonnes inversees (la premiere colonne est a droite) et
    textes traduits ; toute cellule contenant de l'arabe est ecrite avec la police arabe."""

    def __init__(self, donnees, colWidths=None, *args, **kwargs):
        self._arabe = est_arabe()
        self._commandes = []
        self._converti = False
        nb = max((len(ligne) for ligne in donnees), default=0)
        if self._arabe:
            donnees = [list(reversed(ligne)) for ligne in donnees]
            if isinstance(colWidths, (list, tuple)):
                colWidths = list(reversed(colWidths))
        self._nb_colonnes = nb
        super().__init__(donnees, colWidths, *args, **kwargs)

    def setStyle(self, commandes):
        liste = list(commandes.getCommands() if hasattr(commandes, "getCommands") else commandes)
        if self._arabe:
            liste = [_commande_miroir(c, self._nb_colonnes) if len(c) >= 3 and isinstance(c[1], tuple) else c for c in liste]
        self._commandes += liste
        super().setStyle(TableStyle(liste))

    # --- conversion des cellules texte (une seule fois, quand le style est connu)
    def _caracteristiques(self, colonne, ligne, nb_lignes):
        gras_, alignement, taille = False, None, None
        for nom, (c0, r0), (c1, r1), *reste in (c for c in self._commandes if len(c) >= 3 and isinstance(c[1], tuple)):
            c0, c1 = _colonne(c0, self._nb_colonnes), _colonne(c1, self._nb_colonnes)
            r0, r1 = _colonne(r0, nb_lignes), _colonne(r1, nb_lignes)
            if not (min(c0, c1) <= colonne <= max(c0, c1) and min(r0, r1) <= ligne <= max(r0, r1)):
                continue
            if nom == "FONTNAME" and reste:
                gras_ = "Bold" in str(reste[0])
            elif nom == "ALIGN" and reste:
                alignement = str(reste[0]).upper()
            elif nom == "FONTSIZE" and reste:
                taille = reste[0]
        return gras_, alignement, taille

    def _convertir(self):
        if self._converti:
            return
        self._converti = True
        nb_lignes = len(self._cellvalues)
        for r, ligne in enumerate(self._cellvalues):
            for c, valeur in enumerate(ligne):
                if not isinstance(valeur, str) or not valeur.strip():
                    continue
                texte = texte_pdf(valeur) if self._arabe else valeur
                if not (self._arabe or contient_arabe(texte)):
                    continue
                gras_, alignement, taille = self._caracteristiques(c, r, nb_lignes)
                code = {"CENTER": 1, "CENTRE": 1, "RIGHT": 2, "LEFT": 0}.get(alignement or "", 2 if self._arabe else 0)
                taille = taille or 8.5
                style = ParagraphStyle(
                    f"cellule-{code}-{taille}", parent=STYLE_NORMAL, fontSize=taille, leading=taille + 2,
                    alignment=code, fontName=POLICE_ARABE,
                )
                ligne[c] = ParagrapheArabe([texte], style, gras_)

    def wrap(self, *args):
        self._convertir()
        return super().wrap(*args)

    def split(self, *args):
        self._convertir()
        return super().split(*args)


def chemin_logo():
    chemin = getattr(settings, "LOGO_ECOLE", "")
    return chemin if chemin and os.path.isfile(chemin) else None


def _parametre_localise(cle):
    """Parametre de l'ecole dans la langue courante (cle_ar en arabe, repli sur la traduction du texte francais)."""
    if est_arabe():
        valeur = lire_parametre(f"{cle}_ar")
        if valeur:
            return valeur
    return lire_parametre(cle)


def entete_etablissement():
    """Bloc d'entete : logo (si fourni), lignes officielles et nom de l'ecole."""
    bloc = [
        p("Republique Islamique de Mauritanie", STYLE_CENTRE),
        p("Honneur - Fraternite - Justice", STYLE_CENTRE),
        p(_parametre_localise("entete_ministere"), STYLE_CENTRE),
        p(_parametre_localise("entete_region"), STYLE_CENTRE),
        gras(_parametre_localise("nom_etablissement"), STYLE_CENTRE),
    ]
    telephone = lire_parametre("telephone_etablissement")
    if telephone:
        bloc.append(p(f"Tel : {telephone}" if not est_arabe() else f"الهاتف : {telephone}", STYLE_CENTRE))
    logo = chemin_logo()
    if logo:
        image = Image(logo, width=2.2 * cm, height=2.2 * cm)
        tableau = Tableau([[bloc, image]], colWidths=[None, 2.6 * cm])
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
    texte = texte_pdf(texte)

    def dessiner(canvas, document):
        largeur, hauteur = document.pagesize
        canvas.saveState()
        canvas.setFont(POLICE_ARABE_GRAS if contient_arabe(texte) else "Helvetica-Bold", 72)
        canvas.setFillColor(colors.Color(0.82, 0.82, 0.82, alpha=0.45))
        canvas.translate(largeur / 2, hauteur / 2)
        canvas.rotate(45)
        canvas.drawCentredString(0, 0, _visuel(texte))
        canvas.restoreState()
    return dessiner


def construire_pdf(elements, paysage=False, titre="Document", filigrane=None):
    tampon = io.BytesIO()
    taille = landscape(A4) if paysage else A4
    document = SimpleDocTemplate(
        tampon, pagesize=taille, title=texte_pdf(titre),
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
