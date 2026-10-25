"""Excel des evaluations : modele de saisie, import des notes (apercu puis
confirmation, tout-ou-rien, jamais d'ecrasement silencieux), export du
classement."""

import unicodedata
from decimal import Decimal

import openpyxl
from django.db import transaction
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from apps.commun.audit import enregistrer_audit
from apps.commun.exceptions import ErreurMetier
from apps.commun.excel import lire_classeur, orienter_feuille, texte
from apps.commun.traduction import traduire
from apps.etudiants.models import Etudiant
from apps.etudiants.services import eleves_classe
from . import services
from .calculs import en_texte
from .models import StatutNote

LIGNE_ENTETE = 8
PREMIERE_LIGNE = 9
CODES_STATUT = {
    "A": StatutNote.ABSENT, "ABS": StatutNote.ABSENT, "ABSENT": StatutNote.ABSENT,
    "AJ": StatutNote.ABSENT_JUSTIFIE, "ABSJ": StatutNote.ABSENT_JUSTIFIE, "ABSENTJUSTIFIE": StatutNote.ABSENT_JUSTIFIE,
    "NA": StatutNote.NON_APPLICABLE, "N/A": StatutNote.NON_APPLICABLE, "NONAPPLICABLE": StatutNote.NON_APPLICABLE,
}
CODE_DE_STATUT = {StatutNote.ABSENT: "A", StatutNote.ABSENT_JUSTIFIE: "AJ", StatutNote.NON_APPLICABLE: "NA"}
ENTETE_FOND = PatternFill("solid", fgColor="EEF1F3")


def _sans_accent(valeur):
    return "".join(c for c in unicodedata.normalize("NFD", valeur) if unicodedata.category(c) != "Mn")


def _largeurs(feuille, largeurs):
    for index, largeur in enumerate(largeurs, start=1):
        feuille.column_dimensions[get_column_letter(index)].width = largeur


def xlsx_modele_notes(evaluation, lignes):
    """Modele pre-rempli : eleves de la classe, notes deja saisies incluses."""
    classeur = openpyxl.Workbook()
    feuille = classeur.active
    feuille.title = traduire("Notes")
    orienter_feuille(feuille)
    meta = [
        ("Annee scolaire", evaluation.annee_scolaire.libelle), ("Classe", evaluation.classe.nom),
        ("Matiere (code)", evaluation.matiere.code), ("Trimestre", evaluation.trimestre),
        ("Evaluation", evaluation.libelle), ("Bareme", float(evaluation.bareme)),
    ]
    for index, (etiquette, valeur) in enumerate(meta, start=1):
        feuille.cell(row=index, column=1, value=traduire(etiquette)).font = Font(bold=True)
        feuille.cell(row=index, column=2, value=valeur)
    feuille.cell(row=7, column=1, value=traduire(
        "Note : nombre (virgule ou point). A = absent, AJ = absent justifie, NA = non applicable. "
        "Laisser vide = pas de note. Ne pas modifier les lignes 1 a 6."
    )).font = Font(italic=True)
    for index, titre in enumerate(["N°", "Matricule", "Nom complet", "Note / statut"], start=1):
        cellule = feuille.cell(row=LIGNE_ENTETE, column=index, value=traduire(titre))
        cellule.font = Font(bold=True)
        cellule.fill = ENTETE_FOND
    for decalage, ligne in enumerate(lignes):
        rang = PREMIERE_LIGNE + decalage
        feuille.cell(row=rang, column=1, value=ligne["numero"])
        feuille.cell(row=rang, column=2, value=ligne["matricule"])
        feuille.cell(row=rang, column=3, value=ligne["nom_complet"])
        if ligne["statut"] == StatutNote.SAISIE:
            feuille.cell(row=rang, column=4, value=float(ligne["valeur"]))
        elif ligne["statut"] in CODE_DE_STATUT:
            feuille.cell(row=rang, column=4, value=CODE_DE_STATUT[ligne["statut"]])
    _largeurs(feuille, [22, 16, 34, 16])
    return classeur


def lire_cellule_note(brut):
    """-> (statut, valeur_brute) ou (None, None) si vide ; ErreurMetier si illisible."""
    if brut is None or texte(brut) == "":
        return None, None
    if isinstance(brut, (int, float, Decimal)):
        return StatutNote.SAISIE, brut
    code = _sans_accent(texte(brut)).upper().replace(" ", "")
    if code in CODES_STATUT:
        return CODES_STATUT[code], None
    return StatutNote.SAISIE, texte(brut)


def _matricule(valeur):
    if isinstance(valeur, float) and valeur.is_integer():
        valeur = int(valeur)
    return texte(valeur)


def verifier_metadonnees(feuille, evaluation):
    lus = [feuille.cell(row=ligne, column=2).value for ligne in range(1, 7)]
    attendu = [
        ("annee scolaire", texte(lus[0]), evaluation.annee_scolaire.libelle),
        ("classe", texte(lus[1]), evaluation.classe.nom),
        ("matiere", texte(lus[2]), evaluation.matiere.code),
        ("trimestre", texte(lus[3]), str(evaluation.trimestre)),
        ("evaluation", texte(lus[4]), evaluation.libelle),
    ]
    anomalies = [f"{nom} du fichier ('{lu or 'vide'}') different de celle choisie ('{voulu}')" for nom, lu, voulu in attendu if lu != voulu]
    try:
        if Decimal(str(lus[5]).replace(",", ".")) != evaluation.bareme:
            anomalies.append(f"bareme du fichier ({lus[5]}) different de celui de l'evaluation ({evaluation.bareme:g})")
    except Exception:
        anomalies.append("bareme du fichier illisible")
    return anomalies


def analyser_import(fichier, evaluation):
    feuille = lire_classeur(fichier).active
    inscriptions = {i.etudiant.matricule: i for i in eleves_classe(evaluation.classe_id, evaluation.annee_scolaire_id)}
    existantes = {n.etudiant_id: n for n in evaluation.notes.all()}
    autres = set(Etudiant.objects.exclude(matricule__in=list(inscriptions)).values_list("matricule", flat=True))
    resultat = {
        "anomalies_fichier": verifier_metadonnees(feuille, evaluation), "lignes": [],
        "resultats_valides": services.resultats_valides(evaluation.classe, evaluation.trimestre),
    }
    vus, renseignes = set(), set()
    for numero, ligne in enumerate(feuille.iter_rows(min_row=PREMIERE_LIGNE, max_col=4, values_only=True), start=PREMIERE_LIGNE):
        ligne = tuple(ligne) + (None,) * (4 - len(ligne))
        if all(v in (None, "") for v in ligne[1:]):
            continue
        matricule = _matricule(ligne[1])
        anomalies, statut, valeur = [], None, None
        inscription = inscriptions.get(matricule)
        if not matricule:
            anomalies.append("matricule manquant (ligne incomplete)")
        elif inscription is None:
            anomalies.append("etudiant hors de cette classe" if matricule in autres else "matricule inconnu")
        elif matricule in vus:
            anomalies.append("matricule en double dans le fichier")
        vus.add(matricule)
        statut_lu, brut = lire_cellule_note(ligne[3])
        if statut_lu is None:
            etat_ligne = "VIDE"
        else:
            try:
                statut, valeur = services.controler_note(evaluation, statut_lu, brut)
            except ErreurMetier as e:
                anomalies.append(e.message)
            etat_ligne = "NOTE"
        entree = {
            "ligne": numero, "matricule": matricule,
            "nom_complet": inscription.etudiant.nom_complet if inscription else texte(ligne[2]),
            "statut": statut, "valeur": None if valeur is None else str(valeur), "anomalies": anomalies,
            "etudiant": inscription.etudiant_id if inscription else None, "ancienne": None,
        }
        if anomalies:
            entree["etat"] = "ERREUR"
        elif etat_ligne == "VIDE":
            entree["etat"] = "VIDE"          # pas de note : on ne change rien
        else:
            renseignes.add(inscription.etudiant_id)
            ancienne = existantes.get(inscription.etudiant_id)
            if ancienne is None:
                entree["etat"] = "NOUVEAU"
            elif ancienne.statut == statut and ancienne.valeur == valeur:
                entree["etat"] = "IDENTIQUE"
            else:
                entree["etat"] = "MODIFIE"
                entree["ancienne"] = en_texte(ancienne.valeur) if ancienne.valeur is not None else ancienne.statut
        resultat["lignes"].append(entree)
    etats = [e["etat"] for e in resultat["lignes"]]
    resultat["non_renseignes"] = [i.etudiant.nom_complet for i in inscriptions.values() if i.etudiant_id not in renseignes]
    resultat["resume"] = {
        "lignes": len(etats), "nouveaux": etats.count("NOUVEAU"), "identiques": etats.count("IDENTIQUE"),
        "modifies": etats.count("MODIFIE"), "erreurs": etats.count("ERREUR"), "vides": etats.count("VIDE"),
        "non_renseignes": len(resultat["non_renseignes"]),
    }
    return resultat


def blocages(resultat, remplacer, utilisateur, motif):
    raisons = list(resultat["anomalies_fichier"])
    resume = resultat["resume"]
    if resume["erreurs"]:
        raisons.append(f"{resume['erreurs']} ligne(s) en erreur")
    if resume["nouveaux"] + resume["modifies"] + resume["identiques"] == 0:
        raisons.append("le fichier ne contient aucune note")
    if resume["modifies"] and not remplacer:
        raisons.append(f"{resume['modifies']} note(s) deja saisie(s) seraient modifiees : confirmez explicitement leur remplacement")
    if resultat["resultats_valides"]:
        if utilisateur.role not in services.ROLES_CORRECTION_APRES_VALIDATION:
            raisons.append("resultats valides : seule la direction peut corriger des notes")
        elif not (motif or "").strip():
            raisons.append("resultats valides : un motif est obligatoire")
    return raisons


@transaction.atomic
def appliquer_import(evaluation, resultat, remplacer, utilisateur, motif):
    lignes = [
        {"etudiant": e["etudiant"], "statut": e["statut"], "valeur": e["valeur"]}
        for e in resultat["lignes"] if e["etat"] == "NOUVEAU" or (e["etat"] == "MODIFIE" and remplacer)
    ]
    bilan = services.enregistrer_notes(evaluation, lignes, utilisateur, motif)
    enregistrer_audit(utilisateur, "IMPORT_NOTES", "Evaluation", evaluation.pk,
                      nouvelle_valeur={**resultat["resume"], **bilan, "remplacement": remplacer})
    return bilan


def xlsx_notes(evaluation, lignes):
    """Export de la grille de notes (meme disposition que le modele, reimportable)."""
    return xlsx_modele_notes(evaluation, lignes)


def xlsx_classement(donnees):
    """Classement d'une classe (trimestre ou annee) : rang, eleve, moyennes, moyenne generale."""
    classeur = openpyxl.Workbook()
    feuille = classeur.active
    feuille.title = traduire("Classement")
    orienter_feuille(feuille)
    annuel = donnees["periode"] == 0
    titre = traduire("Annuel") if annuel else traduire(f"Trimestre {donnees['periode']}")
    feuille.append([traduire(f"Classement - {donnees['classe_nom']} - {donnees['annee_libelle']} - {titre}")])
    feuille["A1"].font = Font(bold=True, size=12)
    feuille.append([traduire("Resultats valides" if donnees["validee"] else "Resultats PROVISOIRES (non valides)")])
    feuille.append([])
    entete = ["Rang", "Matricule", "Nom complet"] + [m["nom"] for m in donnees["matieres"]]
    entete += (["T1", "T2", "T3"] if annuel else []) + ["Total", "Moyenne generale", "Decision", "Remarque"]
    entete = [traduire(h) for h in entete]
    feuille.append(entete)
    ligne_entete = feuille.max_row
    for index in range(1, len(entete) + 1):
        cellule = feuille.cell(row=ligne_entete, column=index)
        cellule.font = Font(bold=True)
        cellule.fill = ENTETE_FOND
    for eleve in sorted(donnees["etudiants"], key=lambda e: (e["rang"] is None, e["rang"] or 0, e["nom_complet"])):
        ligne = [eleve["rang"], eleve["matricule"], eleve["nom_complet"]]
        for matiere in donnees["matieres"]:
            moyenne = eleve["matieres"][matiere["id"]]["moyenne"]
            ligne.append(float(moyenne.quantize(Decimal("0.01"))) if moyenne is not None else None)
        if annuel:
            ligne += [float(eleve["moyennes_trimestres"][t].quantize(Decimal("0.01"))) if eleve["moyennes_trimestres"][t] is not None else None for t in (1, 2, 3)]
        ligne.append(float(eleve["total_points"].quantize(Decimal("0.01"))))
        moyenne = eleve["moyenne_generale"]
        ligne.append(float(moyenne.quantize(Decimal("0.01"))) if moyenne is not None else None)
        ligne.append(eleve["decision"])
        ligne.append(traduire("Incomplet : notes manquantes") if eleve["incomplet"] else "")
        feuille.append(ligne)
    _largeurs(feuille, [7, 14, 32] + [14] * (len(entete) - 3))
    return classeur
