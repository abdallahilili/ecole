"""Bulletins scolaires PDF (modele du bulletin papier : matieres, colonnes
d'evaluations ponderees, moyenne, coefficient, total, moyenne generale,
rang, decision, observations, signatures)."""

from datetime import date
from decimal import Decimal

from reportlab.lib.units import cm
from reportlab.platypus import PageBreak, Spacer

from apps.commun.pdf import (Tableau as Table, 
    STYLE_CENTRE, STYLE_NORMAL, STYLE_PETIT, STYLE_TITRE, construire_pdf, entete_etablissement, gras, multiligne, p,
    style_tableau,
)
from apps.etudiants.models import Etudiant
from .calculs import en_texte
from .models import Decision, StatutNote


NOM_PERIODE = {0: "ANNUEL", 1: "1er TRIMESTRE", 2: "2e TRIMESTRE", 3: "3e TRIMESTRE"}
DECISIONS = dict(Decision.CHOIX)


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


def _bloc_identite(etudiant, donnees, periode):
    titre = "BULLETIN DE NOTES - " + NOM_PERIODE[periode]
    infos = Table([
        [p(f"Annee scolaire : {donnees['annee_libelle']}"), p(f"Classe : {donnees['classe_nom']}")],
        [p(f"Nom complet : {etudiant.nom_complet}"), p(f"Matricule : {etudiant.matricule}")],
        [p(f"Numero national : {etudiant.numero_national or '-'}"),
         p(f"Ne(e) le : {etudiant.date_naissance:%d/%m/%Y}" if etudiant.date_naissance else "")],
    ], colWidths=[9 * cm, 9 * cm])
    return [p(titre, STYLE_TITRE), infos, Spacer(1, 8)]


def _bloc_final(ligne, donnees, periode, avec_provisoire):
    elements = [Spacer(1, 8)]
    decision = DECISIONS.get(ligne["decision"], "")
    pied = Table([
        [gras("Decision du conseil de classe"), gras("Observations des professeurs"), gras("Observation du directeur")],
        [p(decision or " "), p(ligne["observation_professeurs"] or " "), p(ligne["observation_directeur"] or " ")],
    ], colWidths=[5.4 * cm, 6.3 * cm, 6.3 * cm], rowHeights=[0.7 * cm, 2.2 * cm])
    pied.setStyle(style_tableau())
    elements.append(pied)
    if avec_provisoire:
        elements.append(Spacer(1, 4))
        elements.append(p("Document provisoire : les resultats de cette periode ne sont pas encore valides.", STYLE_PETIT))
    if ligne["incomplet"]:
        elements.append(p("* Moyenne provisoire : des notes ou matieres sont encore manquantes.", STYLE_PETIT))
    signatures = Table([[p("Le professeur principal", STYLE_CENTRE), p(f"Fait le {date.today():%d/%m/%Y}", STYLE_CENTRE),
                         p("Le directeur", STYLE_CENTRE)]], colWidths=[6 * cm, 6 * cm, 6 * cm], rowHeights=[2 * cm])
    elements += [Spacer(1, 10), signatures]
    return elements


def _bulletin_trimestre(etudiant, ligne, donnees):
    periode = donnees["periode"]
    colonnes = _colonnes_evaluations(donnees)
    entete = ["Matieres"]
    entete += [multiligne(libelle, f"(x{_nombre(poids)})", style=STYLE_PETIT) if poids is not None
               else multiligne(libelle, style=STYLE_PETIT) for libelle, poids in colonnes]
    entete += ["Moy.", "Coeff", "Total"]
    rows = [entete]
    for matiere in donnees["matieres"]:
        detail = ligne["matieres"][matiere["id"]]
        par_libelle = {e["libelle"]: e for e in matiere["evaluations"]}
        cellules = []
        for libelle, _ in colonnes:
            evaluation = par_libelle.get(libelle)
            cellules.append(_cellule_note(detail["notes"].get(evaluation["id"]), evaluation["bareme"]) if evaluation else "")
        moyenne = _moy(detail["moyenne"]) + ("*" if detail["incomplete"] and detail["moyenne"] is not None else "")
        rows.append([p(matiere["nom"])] + cellules + [moyenne, _nombre(matiere["coefficient"]), _moy(detail["total"])])
    nb = len(colonnes)
    rows.append([gras("Total")] + [""] * nb + ["", _nombre(ligne["total_coefficients"]), _moy(ligne["total_points"])])
    # Largeur utile : 18 cm ; la colonne des matieres absorbe le reste.
    largeur_eval = min(3.2, 7.9 / max(nb, 1))
    largeurs = [(18 - nb * largeur_eval - 5.5) * cm] + [largeur_eval * cm] * nb + [1.8 * cm, 1.5 * cm, 2.2 * cm]
    tableau = Table(rows, colWidths=largeurs, repeatRows=1)
    tableau.setStyle(style_tableau())
    moyenne_classe = donnees["statistiques"]["moyenne_classe"]
    resume = Table([[
        gras(f"Moyenne generale : {_moy(ligne['moyenne_generale'])} / 20" + ("*" if ligne["incomplet"] else "")),
        gras(f"Rang : {ligne['rang'] if ligne['rang'] else '-'} / {donnees['effectif']}"),
        p(f"Moyenne de la classe : {_virgule(moyenne_classe) if moyenne_classe else '-'}"),
    ]], colWidths=[8 * cm, 4 * cm, 6 * cm])
    resume.setStyle(style_tableau(entete=False))
    return (
        entete_etablissement() + _bloc_identite(etudiant, donnees, periode)
        + [tableau, Spacer(1, 6), resume] + _bloc_final(ligne, donnees, periode, not donnees["validee"])
    )


def _bulletin_annuel(etudiant, ligne, donnees):
    entete = ["Matieres", "T1", "T2", "T3", "Moy. annuelle", "Coeff", "Total"]
    rows = [entete]
    for matiere in donnees["matieres"]:
        detail = ligne["matieres"][matiere["id"]]
        annuelle = detail["moyenne"]
        total = annuelle * matiere["coefficient"] if annuelle is not None else None
        rows.append([p(matiere["nom"])] + [_moy(detail["moyennes_trimestres"][t]) for t in (1, 2, 3)]
                    + [_moy(annuelle), _nombre(matiere["coefficient"]), _moy(total)])
    rows.append([gras("Moyenne generale")] + [_moy(ligne["moyennes_trimestres"][t]) for t in (1, 2, 3)]
                + [_moy(ligne["moyenne_generale"]), _nombre(ligne["total_coefficients"]), _moy(ligne["total_points"])])
    rows.append([gras("Rang")] + [str(ligne["rangs_trimestres"][t] or "-") for t in (1, 2, 3)]
                + [f"{ligne['rang'] or '-'} / {donnees['effectif']}", "", ""])
    tableau = Table(rows, colWidths=[5 * cm, 2 * cm, 2 * cm, 2 * cm, 2.6 * cm, 1.6 * cm, 2.2 * cm], repeatRows=1)
    tableau.setStyle(style_tableau())
    return (
        entete_etablissement() + _bloc_identite(etudiant, donnees, 0) + [tableau]
        + _bloc_final(ligne, donnees, 0, not donnees["validee"])
    )


def pdf_bulletins(donnees, ids_etudiants=None):
    """Un PDF contenant le bulletin de chaque eleve (ou des eleves demandes)."""
    lignes = [l for l in donnees["etudiants"] if ids_etudiants is None or l["etudiant"] in ids_etudiants]
    etudiants = Etudiant.objects.in_bulk([l["etudiant"] for l in lignes])
    elements = []
    for index, ligne in enumerate(lignes):
        if index:
            elements.append(PageBreak())
        construire = _bulletin_annuel if donnees["periode"] == 0 else _bulletin_trimestre
        elements += construire(etudiants[ligne["etudiant"]], ligne, donnees)
    if not elements:
        elements = [p("Aucun eleve a afficher.", STYLE_NORMAL)]
    return construire_pdf(elements, titre="Bulletins", filigrane=None if donnees["validee"] else "PROVISOIRE")
