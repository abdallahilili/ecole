"""Regles metier des evaluations : saisie, verrouillage, validation."""

from decimal import Decimal, InvalidOperation

from django.db import transaction

from apps.commun.audit import enregistrer_audit
from apps.commun.constantes import Role
from apps.commun.exceptions import ErreurMetier
from apps.etudiants.services import eleves_classe
from . import resultats as moteur
from .models import Appreciation, Decision, Note, StatutNote, ValidationResultats

# Apres validation des resultats, seuls ces roles peuvent encore corriger une
# note, avec un motif obligatoire conserve dans le journal d'audit.
ROLES_CORRECTION_APRES_VALIDATION = [Role.ADMINISTRATEUR, Role.DIRECTEUR]
STATUTS_VALIDES = tuple(code for code, _ in StatutNote.CHOIX)


def resultats_valides(classe, trimestre):
    return ValidationResultats.objects.filter(classe=classe, trimestre=trimestre).exists()


def lire_valeur(brut):
    """'14,5' / 14.5 -> Decimal (2 decimales maximum) ; ErreurMetier sinon."""
    try:
        valeur = Decimal(str(brut).strip().replace(",", "."))
    except (InvalidOperation, ValueError):
        raise ErreurMetier(f"note invalide '{brut}'")
    if not valeur.is_finite() or valeur != valeur.quantize(Decimal("0.01")):
        raise ErreurMetier(f"note '{brut}' : 2 decimales maximum")
    return valeur


def controler_note(evaluation, statut, brut):
    """Retourne (statut, valeur) valides ou leve ErreurMetier(message de ligne)."""
    if statut not in STATUTS_VALIDES:
        raise ErreurMetier(f"statut invalide '{statut}'")
    if statut != StatutNote.SAISIE:
        return statut, None
    if brut in (None, ""):
        raise ErreurMetier("note manquante pour le statut 'Note saisie'")
    valeur = lire_valeur(brut)
    if valeur < 0 or valeur > evaluation.bareme:
        raise ErreurMetier(f"note {valeur} hors du bareme (0 a {evaluation.bareme:g})")
    return statut, valeur


def _etat(note):
    return None if note is None else {
        "statut": note.statut, "valeur": None if note.valeur is None else f"{note.valeur:.2f}",
    }


def verifier_verrou(evaluation, utilisateur, motif):
    """Resultats valides : correction reservee a la direction, avec motif."""
    if not resultats_valides(evaluation.classe, evaluation.trimestre):
        return None
    if utilisateur.role not in ROLES_CORRECTION_APRES_VALIDATION:
        raise ErreurMetier("Les resultats de ce trimestre sont valides : seule la direction peut corriger une note.")
    if not (motif or "").strip():
        raise ErreurMetier("Resultats valides : un motif est obligatoire pour corriger une note.")
    return motif.strip()


def enregistrer_notes(evaluation, lignes, utilisateur, motif=None):
    """Enregistre les notes d'une evaluation (liste complete ou partielle).

    Statut 'MANQUANTE' (ou vide) = efface la note. Une note n'est jamais
    transformee en zero. Toute correction d'une note existante est auditee."""
    motif = verifier_verrou(evaluation, utilisateur, motif)
    eleves = {i.etudiant_id: i.etudiant for i in eleves_classe(evaluation.classe_id, evaluation.annee_scolaire_id)}
    existantes = {n.etudiant_id: n for n in evaluation.notes.all()}
    a_ecrire, a_effacer, vus, erreurs = [], [], set(), []
    for ligne in lignes:
        identifiant = ligne.get("etudiant")
        if identifiant not in eleves:
            erreurs.append(f"etudiant {identifiant} : n'appartient pas a la classe")
            continue
        nom = eleves[identifiant].nom_complet
        if identifiant in vus:
            erreurs.append(f"{nom} : present deux fois")
            continue
        vus.add(identifiant)
        statut = ligne.get("statut") or "MANQUANTE"
        if statut == "MANQUANTE":
            if identifiant in existantes:
                a_effacer.append(existantes[identifiant])
            continue
        try:
            statut, valeur = controler_note(evaluation, statut, ligne.get("valeur"))
        except ErreurMetier as e:
            erreurs.append(f"{nom} : {e.message}")
            continue
        a_ecrire.append((identifiant, statut, valeur))
    if erreurs:
        raise ErreurMetier("Notes refusees - " + " ; ".join(erreurs[:10]) + (" ..." if len(erreurs) > 10 else ""))

    creees = modifiees = 0
    with transaction.atomic():
        for identifiant, statut, valeur in a_ecrire:
            ancienne = existantes.get(identifiant)
            if ancienne is None:
                Note.objects.create(evaluation=evaluation, etudiant_id=identifiant, statut=statut, valeur=valeur,
                                    modifie_par=utilisateur)
                creees += 1
            elif ancienne.statut != statut or ancienne.valeur != valeur:
                avant = _etat(ancienne)
                ancienne.statut, ancienne.valeur, ancienne.modifie_par = statut, valeur, utilisateur
                ancienne.save()
                modifiees += 1
                enregistrer_audit(
                    utilisateur, "MODIFICATION_NOTE", "Note", f"{evaluation.pk}:{eleves[identifiant].matricule}",
                    ancienne_valeur=avant, nouvelle_valeur={**_etat(ancienne), "motif": motif},
                )
        for note in a_effacer:
            enregistrer_audit(
                utilisateur, "SUPPRESSION_NOTE", "Note", f"{evaluation.pk}:{eleves[note.etudiant_id].matricule}",
                ancienne_valeur=_etat(note), nouvelle_valeur={"motif": motif},
            )
            note.delete()
        if creees:
            enregistrer_audit(utilisateur, "SAISIE_NOTES", "Evaluation", evaluation.pk,
                              nouvelle_valeur={"notes_creees": creees, "libelle": evaluation.libelle})
    return {"creees": creees, "modifiees": modifiees, "supprimees": len(a_effacer)}


def valider_resultats(classe, trimestre, utilisateur, accepter_incomplet=False):
    donnees = moteur.resultats_trimestre(classe, trimestre)
    if resultats_valides(classe, trimestre):
        raise ErreurMetier("Les resultats de ce trimestre sont deja valides.")
    if not any(m["evaluee"] for m in donnees["matieres"]):
        raise ErreurMetier("Aucune evaluation n'existe pour cette classe et ce trimestre.")
    incomplets = [l["nom_complet"] for l in donnees["etudiants"] if l["incomplet"]]
    if incomplets and not accepter_incomplet:
        raise ErreurMetier(
            f"{len(incomplets)} eleve(s) ont des notes ou matieres manquantes ({', '.join(incomplets[:5])}"
            f"{'...' if len(incomplets) > 5 else ''}) : completez la saisie ou validez en acceptant les resultats incomplets."
        )
    with transaction.atomic():
        ValidationResultats.objects.create(classe=classe, trimestre=trimestre, validee_par=utilisateur)
        enregistrer_audit(utilisateur, "VALIDATION_RESULTATS", "Classe", classe.pk,
                          nouvelle_valeur={"trimestre": trimestre, "incomplets": len(incomplets)})
    return {"incomplets": incomplets}


def rouvrir_resultats(classe, trimestre, utilisateur, motif):
    validation = ValidationResultats.objects.filter(classe=classe, trimestre=trimestre).first()
    if validation is None:
        raise ErreurMetier("Ces resultats ne sont pas valides.")
    if not (motif or "").strip():
        raise ErreurMetier("Un motif est obligatoire pour rouvrir des resultats valides.")
    with transaction.atomic():
        validation.delete()
        enregistrer_audit(utilisateur, "REOUVERTURE_RESULTATS", "Classe", classe.pk,
                          ancienne_valeur={"trimestre": trimestre}, nouvelle_valeur={"motif": motif.strip()})


def enregistrer_appreciations(classe, periode, lignes, utilisateur):
    """Appreciations / decision (periode 0 = annuelle). Verrouillees apres validation du trimestre."""
    if periode in (1, 2, 3) and resultats_valides(classe, periode):
        raise ErreurMetier("Resultats valides : rouvrez-les pour modifier les appreciations.")
    eleves = {i.etudiant_id for i in eleves_classe(classe.id, classe.annee_scolaire_id)}
    erreurs = []
    for ligne in lignes:
        if ligne.get("etudiant") not in eleves:
            erreurs.append(f"etudiant {ligne.get('etudiant')} hors de la classe")
        elif ligne.get("decision") and ligne["decision"] not in dict(Decision.CHOIX):
            erreurs.append(f"decision invalide '{ligne['decision']}'")
    if erreurs:
        raise ErreurMetier("Appreciations refusees : " + " ; ".join(erreurs[:10]))
    with transaction.atomic():
        for ligne in lignes:
            Appreciation.objects.update_or_create(
                classe=classe, trimestre=periode, etudiant_id=ligne["etudiant"],
                defaults={
                    "observation_professeurs": (ligne.get("observation_professeurs") or "")[:500],
                    "observation_directeur": (ligne.get("observation_directeur") or "")[:500],
                    "decision": ligne.get("decision") or "",
                },
            )
        enregistrer_audit(utilisateur, "APPRECIATIONS", "Classe", classe.pk,
                          nouvelle_valeur={"periode": periode, "eleves": len(lignes)})
