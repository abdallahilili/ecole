"""Resultats d'une classe : moyennes par matiere, moyenne generale, rang,
statistiques - par trimestre ou pour l'annee. Tout est calcule cote serveur
a partir des notes ; les valeurs restent des Decimal (voir `jsonifier`)."""

from collections import defaultdict
from decimal import Decimal

from apps.etudiants.services import eleves_classe
from apps.referentiels.models import AffectationMatiereClasse
from . import calculs
from .calculs import Notation, Regles
from .models import Appreciation, Evaluation, Note, ValidationResultats

TRIMESTRES = (1, 2, 3)


def jsonifier(valeur):
    """Decimal -> '12.34' ; recursif. Pour l'API (le PDF utilise les Decimal)."""
    if isinstance(valeur, Decimal):
        return calculs.en_texte(valeur)
    if isinstance(valeur, dict):
        return {cle: jsonifier(v) for cle, v in valeur.items()}
    if isinstance(valeur, (list, tuple)):
        return [jsonifier(v) for v in valeur]
    if hasattr(valeur, "isoformat"):
        return valeur.isoformat()
    return valeur


def _appreciations(classe, periode):
    return {
        a.etudiant_id: a for a in Appreciation.objects.filter(classe=classe, trimestre=periode)
    }


def _decrire_matieres(affectations, par_matiere, nb_notes):
    return [{
        "id": a.matiere_id, "nom": a.matiere.nom_affiche, "code": a.matiere.code, "coefficient": a.coefficient,
        "evaluee": bool(par_matiere.get(a.matiere_id)),
        "evaluations": [
            {"id": e.id, "libelle": e.libelle, "type": e.type, "bareme": e.bareme, "poids": e.poids, "date": e.date,
             "nb_notes": nb_notes.get(e.id, 0)}
            for e in par_matiere.get(a.matiere_id, [])
        ],
    } for a in affectations]


def resultats_trimestre(classe, trimestre, regles=None):
    regles = regles or Regles.depuis_parametres()
    affectations = list(
        # Ordre de creation : l'ecole choisit l'ordre d'impression des matieres en les saisissant.
        AffectationMatiereClasse.objects.filter(classe=classe).select_related("matiere").order_by("id")
    )
    coefficients = {a.matiere_id: a.coefficient for a in affectations}
    evaluations = list(Evaluation.objects.filter(classe=classe, trimestre=trimestre).order_by("date", "id"))
    par_matiere = defaultdict(list)
    for evaluation in evaluations:
        par_matiere[evaluation.matiere_id].append(evaluation)
    notes, nb_notes = {}, defaultdict(int)
    for note in Note.objects.filter(evaluation__in=evaluations):
        notes[(note.etudiant_id, note.evaluation_id)] = note
        nb_notes[note.evaluation_id] += 1
    appreciations = _appreciations(classe, trimestre)
    matiere_nom = {a.matiere_id: a.matiere.nom_affiche for a in affectations}

    lignes = []
    for inscription in eleves_classe(classe.id, classe.annee_scolaire_id):
        etudiant = inscription.etudiant
        moyennes, detail, matiere_incomplete = {}, {}, False
        for affectation in affectations:
            mid = affectation.matiere_id
            evals = par_matiere.get(mid, [])
            notes_eleve = {
                e.id: (Notation(notes[(etudiant.id, e.id)].statut, notes[(etudiant.id, e.id)].valeur)
                       if (etudiant.id, e.id) in notes else None)
                for e in evals
            }
            resultat = calculs.moyenne_matiere(evals, notes_eleve, regles) if evals else calculs.MoyenneMatiere()
            moyennes[mid] = resultat.moyenne
            matiere_incomplete = matiere_incomplete or resultat.incomplete
            detail[mid] = {
                "notes": {
                    e.id: {
                        "statut": notes[(etudiant.id, e.id)].statut if (etudiant.id, e.id) in notes else "MANQUANTE",
                        "valeur": notes[(etudiant.id, e.id)].valeur if (etudiant.id, e.id) in notes else None,
                    } for e in evals
                },
                "moyenne": resultat.moyenne, "incomplete": resultat.incomplete, "manquantes": resultat.manquantes,
                "total": resultat.moyenne * affectation.coefficient if resultat.moyenne is not None else None,
            }
        general = calculs.moyenne_generale(moyennes, coefficients, regles)
        appreciation = appreciations.get(etudiant.id)
        lignes.append({
            "etudiant": etudiant.id, "matricule": etudiant.matricule, "nom_complet": etudiant.nom_complet,
            "matieres": detail, "total_points": general.total_points,
            "total_coefficients": general.total_coefficients, "moyenne_generale": general.moyenne,
            "incomplet": general.incomplet or matiere_incomplete,
            "matieres_manquantes": [matiere_nom[m] for m in general.matieres_manquantes],
            "decision": appreciation.decision if appreciation else "",
            "observation_professeurs": appreciation.observation_professeurs if appreciation else "",
            "observation_directeur": appreciation.observation_directeur if appreciation else "",
        })

    rangs = calculs.classer([(l["etudiant"], l["moyenne_generale"], l["nom_complet"]) for l in lignes], regles)
    for ligne in lignes:
        ligne["rang"] = rangs.get(ligne["etudiant"])
    validation = ValidationResultats.objects.filter(classe=classe, trimestre=trimestre).first()
    return {
        "periode": trimestre, "classe": classe.id, "classe_nom": classe.nom,
        "annee_scolaire": classe.annee_scolaire_id, "annee_libelle": classe.annee_scolaire.libelle,
        "validee": validation is not None, "validee_le": validation.validee_le if validation else None,
        "matieres": _decrire_matieres(affectations, par_matiere, nb_notes),
        "etudiants": lignes, "effectif": len(lignes),
        "statistiques": calculs.statistiques([l["moyenne_generale"] for l in lignes]),
    }


def resultats_annuels(classe, regles=None):
    """Annee : moyennes ponderees des trois trimestres (poids configurables)."""
    regles = regles or Regles.depuis_parametres()
    trimestres = {t: resultats_trimestre(classe, t, regles) for t in TRIMESTRES}
    base = trimestres[1]
    coefficients = {m["id"]: m["coefficient"] for m in base["matieres"]}
    par_trimestre = {t: {l["etudiant"]: l for l in r["etudiants"]} for t, r in trimestres.items()}
    appreciations = _appreciations(classe, 0)

    lignes = []
    for ligne1 in base["etudiants"]:
        eid = ligne1["etudiant"]
        lignes_t = {t: par_trimestre[t].get(eid) for t in TRIMESTRES}
        moyennes_t = {t: (l["moyenne_generale"] if l else None) for t, l in lignes_t.items()}
        general, incomplete = calculs.moyenne_annuelle([moyennes_t[t] for t in TRIMESTRES], regles)
        matieres, total_points, total_coef = {}, Decimal(0), Decimal(0)
        for matiere in base["matieres"]:
            mid = matiere["id"]
            par_t = {t: (l["matieres"][mid]["moyenne"] if l else None) for t, l in lignes_t.items()}
            annuelle, _ = calculs.moyenne_annuelle([par_t[t] for t in TRIMESTRES], regles)
            matieres[mid] = {"moyennes_trimestres": par_t, "moyenne": annuelle}
            if annuelle is not None and coefficients[mid] > 0:
                total_points += annuelle * coefficients[mid]
                total_coef += coefficients[mid]
        appreciation = appreciations.get(eid)
        lignes.append({
            "etudiant": eid, "matricule": ligne1["matricule"], "nom_complet": ligne1["nom_complet"],
            "moyennes_trimestres": moyennes_t,
            "rangs_trimestres": {t: (l["rang"] if l else None) for t, l in lignes_t.items()},
            "matieres": matieres, "total_points": total_points, "total_coefficients": total_coef,
            "moyenne_generale": general,
            "incomplet": incomplete or any(l is None or l["incomplet"] for l in lignes_t.values()),
            "decision": appreciation.decision if appreciation else "",
            "observation_professeurs": appreciation.observation_professeurs if appreciation else "",
            "observation_directeur": appreciation.observation_directeur if appreciation else "",
        })
    rangs = calculs.classer([(l["etudiant"], l["moyenne_generale"], l["nom_complet"]) for l in lignes], regles)
    for ligne in lignes:
        ligne["rang"] = rangs.get(ligne["etudiant"])
    return {
        "periode": 0, "classe": classe.id, "classe_nom": classe.nom,
        "annee_scolaire": classe.annee_scolaire_id, "annee_libelle": classe.annee_scolaire.libelle,
        "validee": all(r["validee"] for r in trimestres.values()),
        "trimestres_valides": [t for t, r in trimestres.items() if r["validee"]],
        "poids_trimestres": regles.poids_trimestres,
        "matieres": [{k: m[k] for k in ("id", "nom", "code", "coefficient")} for m in base["matieres"]],
        "etudiants": lignes, "effectif": len(lignes),
        "statistiques": calculs.statistiques([l["moyenne_generale"] for l in lignes]),
    }


def resultats(classe, periode, regles=None):
    """periode : 1, 2, 3 ou 0 (annuel)."""
    return resultats_annuels(classe, regles) if periode == 0 else resultats_trimestre(classe, periode, regles)


def liste_notes(evaluation):
    """Liste de saisie : tous les eleves de la classe, 'MANQUANTE' si pas de note."""
    notes = {n.etudiant_id: n for n in evaluation.notes.all()}
    lignes = []
    for numero, inscription in enumerate(eleves_classe(evaluation.classe_id, evaluation.annee_scolaire_id), start=1):
        note = notes.get(inscription.etudiant_id)
        lignes.append({
            "numero": numero, "etudiant": inscription.etudiant_id, "matricule": inscription.etudiant.matricule,
            "nom_complet": inscription.etudiant.nom_complet,
            "statut": note.statut if note else "MANQUANTE",
            "valeur": (format(note.valeur.normalize(), "f") if note and note.valeur is not None else None),
        })
    return lignes
