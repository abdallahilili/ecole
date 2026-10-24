"""Regles metier des presences : liste d'appel, validation, notifications."""

import re

from django.db import transaction
from django.utils import timezone

from apps.commun.audit import enregistrer_audit
from apps.commun.exceptions import ErreurMetier
from apps.commun.parametres import lire_bool, lire_parametre
from apps.etudiants.services import eleves_classe
from .models import (
    NotificationWhatsApp, PresenceEtudiant, StatutNotification, StatutPresence,
)

MESSAGE_ABSENCE = (
    "Bonjour, nous vous informons que votre enfant {nom_complet}, inscrit en classe de {classe}, "
    "a été absent au cours de {matiere} le {date}, de {heure_debut} à {heure_fin}. "
    "Merci de prendre contact avec l'administration si nécessaire. {etablissement}."
)


# ---------------------------------------------------------------- liste d'appel

def liste_appel(seance):
    # Une seance non encore enregistree (modele d'import) n'a pas de presences.
    presences = {p.etudiant_id: p for p in seance.presences.all()} if seance.pk else {}
    lignes = []
    for numero, inscription in enumerate(eleves_classe(seance.classe_id, seance.annee_scolaire_id), start=1):
        presence = presences.get(inscription.etudiant_id)
        lignes.append({
            "numero": numero,
            "etudiant": inscription.etudiant_id,
            "inscription": inscription.id,
            "matricule": inscription.etudiant.matricule,
            "nom_complet": inscription.etudiant.nom_complet,
            "statut": presence.statut if presence else None,
            "observation": presence.observation if presence else "",
        })
    return lignes


def verifier_modifiable(seance):
    if seance.presences_validees:
        raise ErreurMetier(
            "Les presences de cette seance sont validees : rouvrez la seance (direction) pour les modifier."
        )


def enregistrer_presences(seance, lignes):
    """Enregistre (brouillon) les presences. Un statut vide efface la ligne."""
    verifier_modifiable(seance)
    autorises = {i.etudiant_id for i in eleves_classe(seance.classe_id, seance.annee_scolaire_id)}
    vus, erreurs = set(), []
    for ligne in lignes:
        identifiant = ligne.get("etudiant")
        statut = ligne.get("statut") or None
        if identifiant not in autorises:
            erreurs.append(f"l'etudiant {identifiant} n'appartient pas a la classe")
        elif identifiant in vus:
            erreurs.append(f"l'etudiant {identifiant} est present deux fois")
        elif statut is not None and statut not in StatutPresence.VALEURS:
            erreurs.append(f"statut invalide '{statut}' pour l'etudiant {identifiant}")
        vus.add(identifiant)
    if erreurs:
        raise ErreurMetier("Presences refusees : " + " ; ".join(erreurs[:10]))

    with transaction.atomic():
        for ligne in lignes:
            statut = ligne.get("statut") or None
            if statut is None:
                seance.presences.filter(etudiant_id=ligne["etudiant"]).delete()
            else:
                PresenceEtudiant.objects.update_or_create(
                    seance=seance, etudiant_id=ligne["etudiant"],
                    defaults={"statut": statut, "observation": (ligne.get("observation") or "")[:255]},
                )


def valider_seance(seance, utilisateur):
    """Confirme les presences (tous les eleves doivent avoir un statut), puis
    met en file les notifications d'absence. Tout ou rien."""
    with transaction.atomic():
        seance.refresh_from_db()
        verifier_modifiable(seance)
        lignes = liste_appel(seance)
        if not lignes:
            raise ErreurMetier("Aucun eleve actif n'est inscrit dans cette classe.")
        sans_statut = [ligne["nom_complet"] for ligne in lignes if ligne["statut"] is None]
        if sans_statut:
            raise ErreurMetier(
                f"{len(sans_statut)} eleve(s) sans statut de presence : " + ", ".join(sans_statut[:10])
                + ("..." if len(sans_statut) > 10 else "")
            )
        seance.presences_validees = True
        seance.validee_le = timezone.now()
        seance.validee_par = utilisateur
        seance.save(update_fields=["presences_validees", "validee_le", "validee_par"])
        enregistrer_audit(
            utilisateur, "VALIDATION_PRESENCES", "Seance", seance.pk,
            nouvelle_valeur={"classe": seance.classe.nom, "date": str(seance.date), "matiere": seance.matiere.nom},
        )
        notifications = creer_notifications(seance)
    return notifications


def rouvrir_seance(seance, utilisateur, motif):
    if not seance.presences_validees:
        raise ErreurMetier("Cette seance n'est pas validee.")
    if not (motif or "").strip():
        raise ErreurMetier("Un motif est obligatoire pour rouvrir une seance validee.")
    seance.presences_validees = False
    seance.validee_le = None
    seance.validee_par = None
    seance.save(update_fields=["presences_validees", "validee_le", "validee_par"])
    enregistrer_audit(
        utilisateur, "REOUVERTURE_PRESENCES", "Seance", seance.pk,
        ancienne_valeur={"validee": True}, nouvelle_valeur={"motif": motif.strip()},
    )


# --------------------------------------------------------------- notifications

def normaliser_telephone(valeur):
    """Numero au format international sans '+' (ex. 22222288896), ou None.
    Un numero local mauritanien a 8 chiffres recoit l'indicatif 222."""
    chiffres = re.sub(r"\D", "", valeur or "")
    if chiffres.startswith("00"):
        chiffres = chiffres[2:]
    if len(chiffres) == 8:
        chiffres = "222" + chiffres
    return chiffres if 9 <= len(chiffres) <= 15 else None


def destinataire(etudiant):
    """(telephone normalise, nom du destinataire) : numero de notification,
    puis pere, mere, tuteur."""
    contacts = [
        (etudiant.nom_pere, etudiant.telephone_pere),
        (etudiant.nom_mere, etudiant.telephone_mere),
        (etudiant.nom_tuteur, etudiant.telephone_tuteur),
    ]
    candidats = [(None, etudiant.telephone_principal)] + contacts
    for nom, numero in candidats:
        telephone = normaliser_telephone(numero)
        if not telephone:
            continue
        if nom is None:
            nom = next((n for n, t in contacts if n and normaliser_telephone(t) == telephone), "")
        return telephone, nom or "Parent / tuteur"
    return None, "Parent / tuteur"


def parametres_message(presence):
    seance = presence.seance
    return {
        "nom_complet": presence.etudiant.nom_complet,
        "classe": seance.classe.nom,
        "matiere": seance.matiere.nom,
        "date": seance.date.strftime("%d/%m/%Y"),
        "heure_debut": seance.heure_debut.strftime("%H:%M"),
        "heure_fin": seance.heure_fin.strftime("%H:%M"),
        "etablissement": lire_parametre("nom_etablissement"),
    }


def texte_message(presence):
    return MESSAGE_ABSENCE.format(**parametres_message(presence))


def creer_notification(presence, manuelle=False):
    telephone, nom = destinataire(presence.etudiant)
    notification = NotificationWhatsApp(
        presence=presence, destinataire_nom=nom, telephone=telephone or "",
        message=texte_message(presence), declenchee_manuellement=manuelle,
    )
    if not telephone:
        notification.statut = StatutNotification.ECHEC
        notification.erreur = "Aucun numero de telephone valide pour ce parent / tuteur."
    notification.save()
    return notification


def statuts_notifies():
    """Un retard n'est notifie que s'il constitue une absence (parametre)."""
    statuts = [StatutPresence.ABSENT]
    if lire_bool("retard_est_absence"):
        statuts.append(StatutPresence.RETARD)
    return statuts


def creer_notifications(seance):
    if not lire_bool("whatsapp_actif"):
        return {"actif": False, "creees": 0, "sans_telephone": []}
    creees, sans_telephone = 0, []
    absences = (
        seance.presences.filter(statut__in=statuts_notifies(), notification__isnull=True)
        .select_related("etudiant", "seance__classe", "seance__matiere")
    )
    for presence in absences:
        notification = creer_notification(presence)
        creees += 1
        if not notification.telephone:
            sans_telephone.append(presence.etudiant.nom_complet)
    return {"actif": True, "creees": creees, "sans_telephone": sans_telephone}
