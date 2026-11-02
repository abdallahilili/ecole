"""Bulletins scolaires PDF et classement de la classe, en A4 paysage.

Le bulletin reprend le bulletin papier de l'ecole (entete, N° d'appel, identite, tableau des matieres, observations des
professeurs, decision, date, total / moyenne generale / rang, observations du directeur) ; il est toujours bilingue.
Le classement est un tableau : une ligne par eleve."""

from datetime import date
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Flowable, KeepInFrame, PageBreak, Spacer, Table as TableFixe, TableStyle

from apps.commun.langue import en_langue
from apps.commun.pdf import (
    Tableau as Table,
    STYLE_NORMAL, STYLE_PETIT, STYLE_TITRE, bilingue, construire_pdf, contient_arabe, entete_etablissement, gras, p,
    style_tableau,
)
from apps.commun.traduction import traduire
from apps.etudiants.models import Etudiant
from apps.referentiels.models import Matiere
from .calculs import en_texte
from .models import Decision, StatutNote


NOM_PERIODE = {0: "ANNUEL", 1: "1er TRIMESTRE", 2: "2e TRIMESTRE", 3: "3e TRIMESTRE"}
DECISIONS = dict(Decision.CHOIX)
STYLE_COLONNE = ParagraphStyle("colonne-classement", parent=STYLE_PETIT, fontSize=7, leading=8.5, alignment=1)
STYLE_COLONNE_ETROIT = ParagraphStyle("colonne-classement-etroit", parent=STYLE_COLONNE, fontSize=6, leading=7.5)
STYLE_CELLULE = ParagraphStyle("cellule-classement", parent=STYLE_NORMAL, fontSize=8.5, leading=10.2)


def _virgule(texte):
    """Convention des documents francais : virgule decimale (14,58)."""
    return texte.replace(".", ",")


def _nombre(valeur):
    """12.50 -> '12,5' ; 20.00 -> '20'."""
    return _virgule(format(Decimal(valeur).normalize(), "f"))


def _moy(valeur):
    return "-" if valeur is None else _virgule(en_texte(valeur))


def _cellule_note(note, bareme):
    if note is None:
        return ""
    statut = note["statut"]
    if statut == StatutNote.SAISIE:
        texte = _nombre(note["valeur"])
        return texte if bareme == 20 else f"{texte}/{_nombre(bareme)}"
    return {StatutNote.ABSENT: "Abs", StatutNote.ABSENT_JUSTIFIE: "Abs.J", StatutNote.NON_APPLICABLE: "NA"}.get(statut, "-")


def _colonnes_evaluations(donnees):
    """Colonnes = libelles d'evaluations distincts (ordre d'apparition) ; le
    poids est indique dans l'en-tete s'il est le meme pour toutes les matieres."""
    colonnes = {}
    for matiere in donnees["matieres"]:
        for evaluation in matiere["evaluations"]:
            colonnes.setdefault(evaluation["libelle"], set()).add(evaluation["poids"])
    return [(libelle, next(iter(poids)) if len(poids) == 1 else None) for libelle, poids in colonnes.items()]


# --------------------------------------------------------------------------- bulletin (A4 paysage, toujours bilingue)
# Comme le bulletin papier : francais a gauche, arabe a droite, quelle que soit la langue de l'interface, en noir et blanc
# (traits fins, ni fonds ni couleurs). La page est faite de tableaux a largeurs fixes (pas de miroir des colonnes) dont les
# cellules sont deja des paragraphes.
#
#   entete de l'ecole
#   [ titre fr | N° d'appel | titre ar ]
#   [ identite fr | classe | identite ar ]
#   [ matiere fr / ar | notes | moyenne | coeff | total | observation de la matiere ]
#   [ total | moyenne generale | rang | decision ] [ observations du directeur ] [ date et signature ]

LARGEUR_PAGE, LARGEUR_NOM = 26.0, 6.0                                   # cm
HAUTEUR_ENTETE, HAUTEUR_BAS, HAUTEUR_BANDEAU, HAUTEUR_LIGNE_MAX = 1.5, 2.6, 0.65, 0.76      # cm
TRAIT = colors.black
STYLE_B_CENTRE = ParagraphStyle("bulletin-centre", parent=STYLE_CELLULE, alignment=1)
STYLE_B_VALEUR = ParagraphStyle("bulletin-valeur", parent=STYLE_CELLULE, fontSize=12, leading=14, alignment=1, fontName="Helvetica-Bold")
STYLE_B_GRAND = ParagraphStyle("bulletin-grand", parent=STYLE_CELLULE, fontSize=13, leading=15, alignment=1, fontName="Helvetica-Bold")
STYLE_B_DECISION = ParagraphStyle("bulletin-decision", parent=STYLE_CELLULE, fontSize=9.5, leading=12, alignment=1, fontName="Helvetica-Bold")
STYLE_B_TITRE = ParagraphStyle("bulletin-titre", parent=STYLE_CELLULE, fontSize=11, leading=13)
STYLE_B_EVAL = ParagraphStyle("bulletin-evaluation", parent=STYLE_COLONNE, fontSize=6.5, leading=8)       # colonnes etroites
STYLE_B_LIGNE = ParagraphStyle("bulletin-ligne", parent=STYLE_CELLULE, fontSize=7.5, leading=9, fontName="Helvetica-Bold")
STYLE_B_ZONE = ParagraphStyle("bulletin-zone", parent=STYLE_CELLULE, fontSize=8, leading=9.5, alignment=1)
# Observation du directeur : taille decroissante jusqu'a ce que le texte saisi tienne dans le cadre.
STYLES_OBSERVATION = [ParagraphStyle(f"bulletin-observation-{t}", parent=STYLE_CELLULE, fontSize=t, leading=t * 1.3) for t in (8.5, 8, 7.5, 7, 6.5)]


def _fr(texte, style=STYLE_CELLULE, fort=False):
    """Paragraphe en francais, meme si l'interface est en arabe."""
    with en_langue("fr"):
        return (gras if fort else p)(texte, style)


def _ar(texte, style=STYLE_CELLULE, fort=False):
    """Paragraphe en arabe : une cle francaise du dictionnaire est traduite, un texte deja arabe est ecrit tel quel."""
    with en_langue("ar"):
        return (gras if fort else p)(texte, style)


def _libre(texte, style):
    """Texte saisi (observations) : ecrit dans sa propre ecriture, sans traduction."""
    return (_ar if contient_arabe(texte) else _fr)(texte, style)


def _entete(fr, style=STYLE_COLONNE, fort=True, ar=None):
    """Titre de colonne : francais (gras) au-dessus, arabe en dessous."""
    return [_fr(fr, style, fort), _ar(fr if ar is None else ar, style)]


def _style_base(*commandes):
    return TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        *commandes,
    ])


def _sans_marge():
    return TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), *[(c, (0, 0), (-1, -1), 0) for c in ("LEFTPADDING", "RIGHTPADDING", "TOPPADDING", "BOTTOMPADDING")]])


class ZoneTexte(Flowable):
    """Zone de texte saisi (observation), reduit au besoin pour tenir ; vide si rien n'est saisi. Le cadre est trace par le tableau."""

    def __init__(self, largeur, hauteur, texte=""):
        super().__init__()
        self.largeur, self.hauteur, self.paragraphe = largeur, hauteur, None
        for style in STYLES_OBSERVATION if texte else []:
            self.paragraphe = _libre(texte, style)
            if self.paragraphe.wrap(largeur - 10, hauteur)[1] <= hauteur - 6:
                break

    def wrap(self, largeur, hauteur):
        return self.largeur, self.hauteur

    def draw(self):
        if self.paragraphe:
            _, hauteur = self.paragraphe.wrap(self.largeur - 10, self.hauteur)
            self.paragraphe.drawOn(self.canv, 5, self.hauteur - hauteur - 4)


def _bandeau_titre(ligne, periode):
    """Titre francais | N° d'appel | titre arabe."""
    titre = "BULLETIN DE NOTES - " + NOM_PERIODE[periode]
    tableau = TableFixe([[
        _fr(titre, STYLE_B_TITRE, True), _fr("N° d'appel", STYLE_B_CENTRE), _fr(ligne["numero_inscription"], STYLE_B_GRAND),
        _ar("N° d'appel", STYLE_B_CENTRE), _ar(titre, STYLE_B_TITRE, True),
    ]], colWidths=[9.3 * cm, 2.7 * cm, 1.8 * cm, 2.7 * cm, 9.5 * cm], rowHeights=[0.85 * cm])
    tableau.setStyle(_style_base(
        ("BOX", (0, 0), (0, 0), 0.6, TRAIT), ("BOX", (1, 0), (3, 0), 0.6, TRAIT), ("LINEAFTER", (1, 0), (2, 0), 0.6, TRAIT),
        ("BOX", (4, 0), (4, 0), 0.6, TRAIT), ("LEFTPADDING", (0, 0), (0, 0), 8), ("RIGHTPADDING", (4, 0), (4, 0), 8),
    ))
    return tableau


def _bloc_eleve(etudiant, donnees):
    """Annee, nom et numero national en francais (gauche) et en arabe (droite), la classe au centre."""
    textes = [f"Annee scolaire : {donnees['annee_libelle']}", f"Nom complet : {etudiant.nom_complet}",
              f"Numero national : {etudiant.numero_national or '-'}"]
    classe = f"Classe : {donnees['classe_nom']}"
    tableau = TableFixe(
        [[_fr(textes[0]), _fr(classe, STYLE_B_CENTRE, True), _ar(textes[0])],
         [_fr(textes[1]), _ar(classe, STYLE_B_CENTRE, True), _ar(textes[1])],
         [_fr(textes[2]), "", _ar(textes[2])]],
        colWidths=[9.8 * cm, 6.4 * cm, 9.8 * cm], rowHeights=[0.55 * cm] * 3,
    )
    tableau.setStyle(_style_base(
        ("BOX", (0, 0), (-1, -1), 0.6, TRAIT), ("LINEAFTER", (0, 0), (1, -1), 0.6, TRAIT),
        ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (0, -1), 8), ("RIGHTPADDING", (2, 0), (2, -1), 8),
    ))
    return tableau


def _tableau_matieres(ligne, donnees, noms, hauteur_ligne):
    """Une ligne par matiere : nom (francais / arabe), notes, moyenne, coefficient, total et observation de la matiere."""
    annuel = donnees["periode"] == 0
    if annuel:
        valeurs = [_entete(t) for t in ("T1", "T2", "T3")]
        queue, largeur_valeur = [2.2, 1.4, 2.0], 2.2
        tete_queue = [_entete("Moy. annuelle"), _entete("Coeff"), _entete("Total")]
    else:
        colonnes = _colonnes_evaluations(donnees)
        queue = [2.0, 1.4, 2.0]
        largeur_valeur = max(1.2, min(2.4, (LARGEUR_PAGE - LARGEUR_NOM - sum(queue) - 6.0) / max(len(colonnes), 1)))
        etroit = largeur_valeur < 2.1                                  # titres longs dans peu de place : police reduite
        valeurs = [_entete(f"{libelle} (x{_nombre(poids)})" if poids is not None else libelle,
                           STYLE_B_EVAL if etroit else STYLE_COLONNE, not etroit,
                           traduire(libelle, "ar") + (f" ({_nombre(poids)}x)" if poids is not None else ""))
                   for libelle, poids in colonnes]
        tete_queue = [_entete("Moy. matiere"), _entete("Coeff"), _entete("Total")]
    largeur_obs = LARGEUR_PAGE - LARGEUR_NOM - largeur_valeur * len(valeurs) - sum(queue)

    lignes = [[_entete("Matieres")] + valeurs + tete_queue + [_entete("Observations des professeurs")]]
    for matiere in donnees["matieres"]:
        detail = ligne["matieres"][matiere["id"]]
        if annuel:
            notes = [_moy(detail["moyennes_trimestres"][t]) for t in (1, 2, 3)]
            moyenne = _moy(detail["moyenne"])
            total = _moy(detail["moyenne"] * matiere["coefficient"] if detail["moyenne"] is not None else None)
        else:
            par_libelle = {e["libelle"]: e for e in matiere["evaluations"]}
            notes = []
            for libelle, _ in colonnes:
                evaluation = par_libelle.get(libelle)
                notes.append(_cellule_note(detail["notes"].get(evaluation["id"]), evaluation["bareme"]) if evaluation else "")
            moyenne = _moy(detail["moyenne"]) + ("*" if detail["incomplete"] and detail["moyenne"] is not None else "")
            total = _moy(detail["total"])
        nom_fr, nom_ar = noms[matiere["id"]]
        lignes.append([bilingue(nom_fr, nom_ar, STYLE_CELLULE)] + [_fr(v, STYLE_B_CENTRE) for v in notes]
                      + [_fr(moyenne, STYLE_B_CENTRE, True), _fr(_nombre(matiere["coefficient"]), STYLE_B_CENTRE), _fr(total, STYLE_B_CENTRE), ""])
    nb_matieres = len(donnees["matieres"])
    if annuel:
        general = ligne["moyenne_generale"]
        lignes.append([bilingue("Moyenne generale", traduire("Moyenne generale", "ar"), STYLE_B_LIGNE)]
                      + [_fr(_moy(ligne["moyennes_trimestres"][t]), STYLE_B_CENTRE) for t in (1, 2, 3)]
                      + [_fr(_moy(general) + ("*" if ligne["incomplet"] and general is not None else ""), STYLE_B_CENTRE, True),
                         _fr(_nombre(ligne["total_coefficients"]), STYLE_B_CENTRE), _fr(_moy(ligne["total_points"]), STYLE_B_CENTRE), ""])
        lignes.append([bilingue("Rang", traduire("Rang", "ar"), STYLE_B_LIGNE)]
                      + [_fr(str(ligne["rangs_trimestres"][t] or "-"), STYLE_B_CENTRE) for t in (1, 2, 3)]
                      + [_fr(f"{ligne['rang'] or '-'} / {donnees['effectif']}", STYLE_B_CENTRE, True), "", "", ""])
    commandes = [
        ("GRID", (0, 0), (-1, -1), 0.5, TRAIT),
        ("LEFTPADDING", (1, 0), (-2, 0), 1), ("RIGHTPADDING", (1, 0), (-2, 0), 1), ("LEFTPADDING", (0, 1), (0, -1), 6),
    ]
    if ligne["observation_professeurs"] and nb_matieres:
        # Une observation generale deja saisie est imprimee sur toute la hauteur des matieres, a la place des cases vides.
        lignes[1][-1] = ZoneTexte(largeur_obs * cm, nb_matieres * hauteur_ligne * cm, ligne["observation_professeurs"])
        commandes += [("SPAN", (-1, 1), (-1, nb_matieres)), *[(c, (-1, 1), (-1, nb_matieres), 0) for c in ("LEFTPADDING", "RIGHTPADDING", "TOPPADDING", "BOTTOMPADDING")]]
    tableau = TableFixe(
        lignes, colWidths=[LARGEUR_NOM * cm] + [largeur_valeur * cm] * len(valeurs) + [l * cm for l in queue] + [largeur_obs * cm],
        rowHeights=[HAUTEUR_ENTETE * cm] + [hauteur_ligne * cm] * (len(lignes) - 1),
    )
    tableau.setStyle(_style_base(*commandes))
    return tableau


def _resume(ligne, largeur):
    """Total, moyenne generale, rang et decision, sous le tableau des matieres."""
    general = ligne["moyenne_generale"]
    decision = DECISIONS.get(ligne["decision"], "")
    valeurs = [
        _fr(_moy(ligne["total_points"]), STYLE_B_VALEUR),
        _fr(_moy(general) + ("*" if ligne["incomplet"] and general is not None else ""), STYLE_B_VALEUR),
        _fr(str(ligne["rang"] or "-"), STYLE_B_VALEUR),
        bilingue(decision, traduire(decision, "ar"), STYLE_B_DECISION) if decision else "",
    ]
    cles = ("Total", "Moyenne generale", "Rang", "Decision")
    tableau = TableFixe([[_entete(c, STYLE_B_ZONE) for c in cles], valeurs],
                        colWidths=[l / 11.8 * largeur * cm for l in (2.4, 3.2, 2.2, 4.0)], rowHeights=[1.1 * cm, (HAUTEUR_BAS - 1.1) * cm])
    tableau.setStyle(_style_base(("GRID", (0, 0), (-1, -1), 0.5, TRAIT)))
    return tableau


def _cadre_directeur(largeur, texte):
    """Petit carre « Observations du directeur »."""
    tableau = TableFixe(
        [[_fr("Observations du directeur", STYLE_B_ZONE, True), _ar("Observations du directeur", STYLE_B_ZONE, True)],
         [ZoneTexte(largeur * cm, (HAUTEUR_BAS - HAUTEUR_BANDEAU) * cm, texte), ""]],
        colWidths=[largeur / 2 * cm] * 2, rowHeights=[HAUTEUR_BANDEAU * cm, (HAUTEUR_BAS - HAUTEUR_BANDEAU) * cm],
    )
    tableau.setStyle(_style_base(("BOX", (0, 0), (-1, -1), 0.5, TRAIT), ("LINEBELOW", (0, 0), (-1, 0), 0.5, TRAIT), ("SPAN", (0, 1), (1, 1)),
                                 ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                                 *[(c, (0, 1), (-1, 1), 0) for c in ("LEFTPADDING", "RIGHTPADDING", "TOPPADDING", "BOTTOMPADDING")]))
    return tableau


def _cadre_date(largeur):
    """Petit carre « Date » et « Le directeur » (espace de signature)."""
    date_ = f"Date : {date.today():%d/%m/%Y}"
    tableau = TableFixe(
        [[_fr(date_, STYLE_B_ZONE, True), _ar(date_, STYLE_B_ZONE, True)],
         [_fr("Le directeur", STYLE_B_ZONE, True), _ar("Le directeur", STYLE_B_ZONE, True)], ["", ""]],
        colWidths=[largeur / 2 * cm] * 2, rowHeights=[HAUTEUR_BANDEAU * cm, HAUTEUR_BANDEAU * cm, (HAUTEUR_BAS - 2 * HAUTEUR_BANDEAU) * cm],
    )
    tableau.setStyle(_style_base(("BOX", (0, 0), (-1, -1), 0.5, TRAIT), ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3)))
    return tableau


def _mentions(ligne, donnees):
    """Mentions de bas de page (resultats provisoires, moyenne incomplete)."""
    mentions = []
    if not donnees["validee"]:
        mentions.append("Document provisoire : les resultats de cette periode ne sont pas encore valides.")
    if ligne["incomplet"]:
        mentions.append("* Moyenne provisoire : des notes ou matieres sont encore manquantes.")
    return mentions


def _page_bulletin(etudiant, ligne, donnees, noms):
    """Une page de bulletin pour un eleve (trimestre ou annee). `noms` : id de matiere -> (nom francais, nom arabe)."""
    mentions = _mentions(ligne, donnees)
    lignes_tableau = len(donnees["matieres"]) + (2 if donnees["periode"] == 0 else 0)
    place = 6.4 if mentions else 7.2                                      # cm disponibles pour les lignes du tableau
    hauteur_ligne = max(0.4, min(HAUTEUR_LIGNE_MAX, place / max(lignes_tableau, 1)))     # reduite si beaucoup de matieres
    bas = TableFixe([[_resume(ligne, 11.8), "", _cadre_directeur(8.0, ligne["observation_directeur"]), "", _cadre_date(5.6)]],
                    colWidths=[11.8 * cm, 0.3 * cm, 8.0 * cm, 0.3 * cm, 5.6 * cm])
    bas.setStyle(_sans_marge())

    elements = entete_etablissement(LARGEUR_PAGE * cm) + [
        _bandeau_titre(ligne, donnees["periode"]), Spacer(1, 4), _bloc_eleve(etudiant, donnees), Spacer(1, 6),
        _tableau_matieres(ligne, donnees, noms, hauteur_ligne), Spacer(1, 0.3 * cm), bas,
    ]
    if mentions:
        notes = TableFixe([[_fr(m, STYLE_PETIT), _ar(m, STYLE_PETIT)] for m in mentions], colWidths=[LARGEUR_PAGE / 2 * cm] * 2)
        notes.setStyle(TableStyle([("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
        elements += [Spacer(1, 4), notes]
    return [KeepInFrame(LARGEUR_PAGE * cm, 17.9 * cm, elements, mode="shrink")]       # filet de securite : jamais plus d'une page


def pdf_bulletins(donnees, ids_etudiants=None):
    """Un PDF paysage contenant le bulletin de chaque eleve (ou des eleves demandes), une page par eleve."""
    lignes = [l for l in donnees["etudiants"] if ids_etudiants is None or l["etudiant"] in ids_etudiants]
    etudiants = Etudiant.objects.in_bulk([l["etudiant"] for l in lignes])
    matieres = Matiere.objects.in_bulk([m["id"] for m in donnees["matieres"]])
    noms = {mid: (matiere.nom, matiere.nom_ar) for mid, matiere in matieres.items()}
    elements = []
    for index, ligne in enumerate(lignes):
        if index:
            elements.append(PageBreak())
        elements += _page_bulletin(etudiants[ligne["etudiant"]], ligne, donnees, noms)
    if not elements:
        elements = [p("Aucun eleve a afficher.", STYLE_NORMAL)]
    return construire_pdf(elements, paysage=True, titre="Bulletins", filigrane=None if donnees["validee"] else "PROVISOIRE")


def pdf_classement(donnees):
    """Classement de la classe en paysage : rang, N° d'appel (= N° d'inscription), moyenne par matiere, total,
    moyenne generale et decision. Les matieres se partagent la largeur qui reste apres les colonnes fixes."""
    periode, annuel, matieres = donnees["periode"], donnees["periode"] == 0, donnees["matieres"]
    largeur_utile = 26                                               # cm : A4 paysage moins les marges et le cadre
    fixes = [1.1, 1.5] + ([1.3] * 3 if annuel else []) + [1.7, 1.8, 2.0]
    reste = largeur_utile - sum(fixes)
    largeur_matiere = max(1.0, min(2.2, (reste - 3.6) / len(matieres))) if matieres else 0
    largeur_nom = max(3.0, reste - largeur_matiere * len(matieres))
    largeurs = [1.1, 1.5, largeur_nom] + [largeur_matiere] * len(matieres) + fixes[2:]
    etroit = largeur_matiere < 1.4                                   # noms longs dans peu de place : police reduite, sans gras
    style_matiere = STYLE_COLONNE_ETROIT if etroit else STYLE_COLONNE
    nom_matiere = p if etroit else gras

    entete = [gras("Rang", STYLE_COLONNE), gras("N° d'appel", STYLE_COLONNE), gras("Nom complet", STYLE_COLONNE)]
    entete += [[nom_matiere(m["nom"], style_matiere), p(f"coef {_nombre(m['coefficient'])}", style_matiere)] for m in matieres]
    entete += [gras(t, STYLE_COLONNE) for t in (["T1", "T2", "T3"] if annuel else [])]
    entete += [gras("Total", STYLE_COLONNE), gras("Moyenne generale", STYLE_COLONNE), gras("Decision", STYLE_COLONNE)]
    rows = [entete]
    for ligne in sorted(donnees["etudiants"], key=lambda e: (e["rang"] is None, e["rang"] or 0, e["nom_complet"])):
        cellules = [str(ligne["rang"] or "-"), ligne["numero_inscription"], p(ligne["nom_complet"], STYLE_CELLULE)]
        for matiere in matieres:
            detail = ligne["matieres"][matiere["id"]]
            marque = "*" if detail.get("incomplete") and detail["moyenne"] is not None else ""
            cellules.append(_moy(detail["moyenne"]) + marque)
        if annuel:
            cellules += [_moy(ligne["moyennes_trimestres"][t]) for t in (1, 2, 3)]
        marque = "*" if ligne["incomplet"] and ligne["moyenne_generale"] is not None else ""
        cellules += [_moy(ligne["total_points"]), _moy(ligne["moyenne_generale"]) + marque, p(DECISIONS.get(ligne["decision"], "") or " ", STYLE_CELLULE)]
        rows.append(cellules)

    tableau = Table(rows, colWidths=[l * cm for l in largeurs], repeatRows=1)
    style = style_tableau()
    style.add("ALIGN", (0, 1), (1, -1), "CENTER")
    style.add("ALIGN", (3, 1), (-2, -1), "CENTER")
    style.add("FONTNAME", (-2, 1), (-2, -1), "Helvetica-Bold")
    style.add("LEFTPADDING", (0, 0), (-1, -1), 3)
    style.add("RIGHTPADDING", (0, 0), (-1, -1), 3)
    if matieres:
        style.add("LEFTPADDING", (3, 0), (2 + len(matieres), 0), 1)
        style.add("RIGHTPADDING", (3, 0), (2 + len(matieres), 0), 1)
    tableau.setStyle(style)

    infos = Table([[p(f"Annee scolaire : {donnees['annee_libelle']}"), p(f"Classe : {donnees['classe_nom']}"),
                    p(f"Effectif : {donnees['effectif']}")]], colWidths=[largeur_utile / 3 * cm] * 3)
    statistiques = donnees["statistiques"]
    valeur = lambda cle, suffixe="": _virgule(statistiques[cle]) + suffixe if statistiques[cle] else "-"
    resume = Table([[
        gras(f"Moyenne de la classe : {valeur('moyenne_classe')}"), p(f"Plus haute : {valeur('plus_haute')}"),
        p(f"Plus basse : {valeur('plus_basse')}"), p(f"Taux de reussite : {valeur('taux_reussite', ' %')}"),
    ]], colWidths=[largeur_utile / 4 * cm] * 4)
    resume.setStyle(style_tableau(entete=False))

    elements = entete_etablissement(largeur_utile * cm) + [p("RESULTATS DE LA CLASSE - " + NOM_PERIODE[periode], STYLE_TITRE), infos, Spacer(1, 6)]
    if donnees["etudiants"]:
        elements += [tableau, Spacer(1, 6), resume]
    else:
        elements.append(p("Aucun eleve a afficher.", STYLE_NORMAL))
    if not donnees["validee"]:
        elements += [Spacer(1, 4), p("Document provisoire : les resultats de cette periode ne sont pas encore valides.", STYLE_PETIT)]
    if any(l["incomplet"] for l in donnees["etudiants"]):
        elements.append(p("* Moyenne provisoire : des notes ou matieres sont encore manquantes.", STYLE_PETIT))
    return construire_pdf(elements, paysage=True, titre="Classement", filigrane=None if donnees["validee"] else "PROVISOIRE")
