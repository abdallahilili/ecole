"""Indicateurs des tableaux de bord : tous calcules a partir des donnees reelles
de la base (aucun chiffre fictif). Chaque section est une fonction independante ;
`SECTIONS_PAR_ROLE` decide ce que chaque role peut voir."""

from datetime import datetime, timedelta
from decimal import Decimal

from django.db.models import Count, F, IntegerField, OuterRef, Q, Subquery, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.commun.constantes import Role
from apps.commun.parametres import lire_bool
from apps.emplois_du_temps.models import EmploiDuTemps, SeanceProgrammee, StatutEmploi
from apps.etudiants.models import Etudiant, Inscription
from apps.evaluations.models import Evaluation, ValidationResultats
from apps.presences.models import (
    NotificationWhatsApp, PresenceEtudiant, Seance, StatutNotification, StatutPresence, StatutSeanceProfesseur,
)
from apps.professeurs.models import AffectationProfesseur, Professeur
from apps.referentiels.models import AnneeScolaire, Classe, Matiere, Salle
from apps.remuneration import services as remuneration
from apps.remuneration.models import PaiementProfesseur, ReleveRemuneration, StatutReleve
from apps.scolarite.models import PaiementScolarite

FENETRE_JOURS = 30


def annee_courante():
    return AnneeScolaire.objects.filter(active=True).first() or AnneeScolaire.objects.order_by("-date_debut").first()


def trimestre_courant(annee, jour):
    if annee is None:
        return 1
    if annee.debut_trimestre3 and jour >= annee.debut_trimestre3:
        return 3
    if annee.debut_trimestre2 and jour >= annee.debut_trimestre2:
        return 2
    return 1


def _texte(valeur):
    """Montant ou nombre d'heures a 2 decimales, quelle que soit la base de donnees ('3' -> '3.00')."""
    return None if valeur is None else f"{Decimal(valeur):.2f}"


def _effectif_classe():
    return Inscription.objects.filter(
        classe_id=OuterRef("classe_id"), annee_scolaire_id=OuterRef("annee_scolaire_id"), statut="ACTIVE",
    ).order_by().values("classe_id").annotate(n=Count("pk")).values("n")


# ----------------------------------------------------------------- sections

def effectifs(contexte):
    annee = contexte["annee"]
    par_classe = list(
        Classe.objects.filter(annee_scolaire=annee).annotate(n=Count("inscriptions", filter=Q(inscriptions__statut="ACTIVE")))
        .order_by("niveau__ordre", "nom").values("nom", "n", "capacite")
    )
    par_niveau = list(
        Inscription.objects.filter(annee_scolaire=annee, statut="ACTIVE").values("classe__niveau__nom", "classe__niveau__ordre")
        .annotate(n=Count("pk")).order_by("classe__niveau__ordre")
    )
    return {
        "etudiants_actifs": Inscription.objects.filter(annee_scolaire=annee, statut="ACTIVE").count() if annee else 0,
        "etudiants_enregistres": Etudiant.objects.filter(actif=True).count(),
        "par_classe": [{"classe": c["nom"], "effectif": c["n"], "capacite": c["capacite"]} for c in par_classe],
        "par_niveau": [{"niveau": n["classe__niveau__nom"], "effectif": n["n"]} for n in par_niveau],
    }


def structure(contexte):
    annee = contexte["annee"]
    return {
        "professeurs_actifs": Professeur.objects.filter(statut="ACTIF").count(),
        "classes": Classe.objects.filter(annee_scolaire=annee).count() if annee else 0,
        "matieres": Matiere.objects.count(),
        "salles": Salle.objects.count(),
    }


def presences_etudiants(contexte):
    debut = contexte["aujourdhui"] - timedelta(days=FENETRE_JOURS)
    base = PresenceEtudiant.objects.filter(seance__presences_validees=True, seance__date__gte=debut, seance__date__lte=contexte["aujourdhui"])
    comptes = {c["statut"]: c["n"] for c in base.values("statut").annotate(n=Count("pk"))}
    total = sum(comptes.values())
    absents = comptes.get(StatutPresence.ABSENT, 0)
    recentes = base.filter(statut=StatutPresence.ABSENT).select_related("etudiant", "seance__classe", "seance__matiere").order_by(
        "-seance__date", "-seance__heure_debut")[:8]
    return {
        "periode_jours": FENETRE_JOURS, "total": total, "presents": comptes.get(StatutPresence.PRESENT, 0),
        "absents": absents, "retards": comptes.get(StatutPresence.RETARD, 0),
        "taux_presence": round(100 * (total - absents) / total, 1) if total else None,
        "dernieres_absences": [{
            "etudiant": p.etudiant.nom_complet, "classe": p.seance.classe.nom, "matiere": p.seance.matiere.nom_affiche,
            "date": p.seance.date.isoformat(), "heure": p.seance.heure_debut.strftime("%H:%M"),
        } for p in recentes],
    }


def presences_professeurs(contexte):
    debut = contexte["aujourdhui"] - timedelta(days=FENETRE_JOURS)
    seances = Seance.objects.filter(date__gte=debut, date__lte=contexte["aujourdhui"])
    comptes = {c["statut_professeur"]: c["n"] for c in seances.values("statut_professeur").annotate(n=Count("pk"))}
    effectuees = sum(comptes.get(s, 0) for s in StatutSeanceProfesseur.COMPTEES)
    absentes = comptes.get(StatutSeanceProfesseur.ABSENT, 0)
    return {
        "periode_jours": FENETRE_JOURS, "par_statut": comptes, "seances_effectuees": effectuees, "absences": absentes,
        "a_renseigner": comptes.get(StatutSeanceProfesseur.PLANIFIE, 0),
        "taux_realisation": round(100 * effectuees / (effectuees + absentes), 1) if (effectuees + absentes) else None,
        "heures_effectuees": _texte(seances.aggregate(h=Coalesce(Sum("heures_effectuees"), Decimal("0")))["h"]),
    }


def notifications(contexte):
    debut = timezone.now() - timedelta(days=FENETRE_JOURS)
    comptes = {c["statut"]: c["n"] for c in NotificationWhatsApp.objects.filter(cree_le__gte=debut).values("statut").annotate(n=Count("pk"))}
    return {
        "actif": lire_bool("whatsapp_actif"), "periode_jours": FENETRE_JOURS,
        "en_attente": comptes.get(StatutNotification.EN_ATTENTE, 0), "echecs": comptes.get(StatutNotification.ECHEC, 0),
        "envoyees": comptes.get(StatutNotification.ENVOYE, 0) + comptes.get(StatutNotification.LIVRE, 0),
    }


def remuneration_section(contexte):
    jour = contexte["aujourdhui"]
    debut_mois = remuneration.premier_du_mois(jour)
    heures = Seance.objects.filter(date__range=(debut_mois, remuneration.dernier_du_mois(jour)), heures_effectuees__gt=0).aggregate(
        h=Coalesce(Sum("heures_effectuees"), Decimal("0")))["h"]
    valides = ReleveRemuneration.objects.filter(statut=StatutReleve.VALIDE).prefetch_related("paiements")
    dus = sum((remuneration.totaux(r)["solde"] for r in valides), remuneration.ZERO)
    derniers = PaiementProfesseur.objects.select_related("releve__professeur").filter(montant__gt=0).order_by("-date_paiement", "-id")[:5]
    return {
        "heures_du_mois": _texte(heures), "montants_dus": _texte(dus),
        "releves_a_valider": ReleveRemuneration.objects.filter(statut=StatutReleve.BROUILLON).count(),
        "derniers_paiements": [{
            "reference": p.reference, "professeur": p.releve.professeur.nom_complet, "montant": _texte(p.montant),
            "date": p.date_paiement.isoformat(),
        } for p in derniers],
    }


def scolarite_section(contexte):
    jour = contexte["aujourdhui"]
    paiements = PaiementScolarite.objects.filter(date_paiement__range=(remuneration.premier_du_mois(jour), remuneration.dernier_du_mois(jour)))
    total = paiements.aggregate(t=Coalesce(Sum("montant"), Decimal("0")))["t"]
    derniers = PaiementScolarite.objects.select_related("inscription__etudiant", "inscription__classe").order_by("-date_paiement", "-id")[:5]
    return {
        "encaisse_mois": _texte(total), "nombre_paiements_mois": paiements.count(),
        "derniers_paiements": [{
            "reference": p.reference, "etudiant": p.inscription.etudiant.nom_complet, "classe": p.inscription.classe.nom,
            "montant": _texte(p.montant), "date": p.date_paiement.isoformat(),
        } for p in derniers],
    }


def emploi_du_temps_section(contexte):
    annee = contexte["annee"]
    publie = EmploiDuTemps.objects.filter(annee_scolaire=annee, statut=StatutEmploi.PUBLIE).first() if annee else None
    dernier_brouillon = EmploiDuTemps.objects.filter(annee_scolaire=annee, statut=StatutEmploi.BROUILLON).order_by("-cree_le").first() if annee else None
    rapport = dernier_brouillon.rapport if dernier_brouillon and dernier_brouillon.rapport else {}
    return {
        "publie": {"id": publie.pk, "nom": publie.nom, "publie_le": publie.publie_le.isoformat() if publie.publie_le else None,
                   "seances": publie.seances.count()} if publie else None,
        "brouillons": EmploiDuTemps.objects.filter(annee_scolaire=annee, statut=StatutEmploi.BROUILLON).count() if annee else 0,
        "derniere_generation": {"id": dernier_brouillon.pk, "nom": dernier_brouillon.nom, "publiable": rapport.get("publiable"),
                                "conflits": len(rapport.get("conflits", []))} if dernier_brouillon and rapport else None,
    }


def evaluations_section(contexte):
    annee, jour = contexte["annee"], contexte["aujourdhui"]
    if annee is None:
        return {"prochaines": [], "notes_manquantes": [], "resultats_a_valider": [], "bulletins_prets": 0, "trimestre": 1}
    trimestre = trimestre_courant(annee, jour)
    base = Evaluation.objects.filter(annee_scolaire=annee).select_related("classe", "matiere")
    prochaines = base.filter(date__gte=jour).order_by("date", "id")[:5]
    # Evaluations deja passees dont certaines notes sont encore a saisir (au moins un eleve sans note).
    manquantes = list(
        base.filter(trimestre=trimestre, date__lte=jour)
        .annotate(nb_notes=Count("notes"), effectif=Coalesce(Subquery(_effectif_classe(), output_field=IntegerField()), 0))
        .filter(nb_notes__lt=F("effectif")).order_by("classe__nom", "date")[:10]
    )
    paires = set(base.values_list("classe_id", "trimestre"))
    validees = set(ValidationResultats.objects.filter(classe__annee_scolaire=annee).values_list("classe_id", "trimestre"))
    noms_classes = dict(Classe.objects.filter(annee_scolaire=annee).values_list("id", "nom"))
    a_valider = sorted(paires - validees, key=lambda p: (noms_classes.get(p[0], ""), p[1]))
    return {
        "trimestre": trimestre,
        "prochaines": [{"classe": e.classe.nom, "matiere": e.matiere.nom_affiche, "libelle": e.libelle, "date": e.date.isoformat()} for e in prochaines],
        "notes_manquantes": [{"classe": e.classe.nom, "matiere": e.matiere.nom_affiche, "libelle": e.libelle,
                              "manquantes": e.effectif - e.nb_notes} for e in manquantes],
        "resultats_a_valider": [{"classe": noms_classes.get(c, "?"), "trimestre": t} for c, t in a_valider[:10]],
        "bulletins_prets": len(validees),
    }


def mon_espace(contexte):
    """Tableau de bord du professeur connecte : uniquement ses propres donnees."""
    utilisateur, jour, maintenant = contexte["utilisateur"], contexte["aujourdhui"], contexte["maintenant"]
    fiche = utilisateur.professeur_id
    if not fiche:
        return {"fiche_liee": False}
    annee = contexte["annee"]
    mes = Q(professeur_id=fiche) | Q(professeur_remplacant_id=fiche)

    prochains = []
    publie = EmploiDuTemps.objects.filter(annee_scolaire=annee, statut=StatutEmploi.PUBLIE).first() if annee else None
    if publie:
        programmees = list(SeanceProgrammee.objects.filter(emploi=publie, professeur_id=fiche).select_related("classe", "matiere", "salle"))
        for decalage in range(8):
            date_ = jour + timedelta(days=decalage)
            for s in (p for p in programmees if p.jour == date_.weekday()):
                if datetime.combine(date_, s.heure_debut) >= maintenant.replace(tzinfo=None):
                    prochains.append({"date": date_.isoformat(), "debut": s.heure_debut.strftime("%H:%M"), "fin": s.heure_fin.strftime("%H:%M"),
                                      "classe": s.classe.nom, "matiere": s.matiere.nom_affiche, "salle": s.salle.nom if s.salle else None})
        prochains.sort(key=lambda c: (c["date"], c["debut"]))

    a_valider = Seance.objects.filter(mes, date__lte=jour, presences_validees=False).select_related("classe", "matiere").order_by("-date")
    effectuees = Seance.objects.filter(mes, statut_professeur__in=StatutSeanceProfesseur.COMPTEES).select_related("classe", "matiere").order_by("-date", "-heure_debut")
    heures_mois = Seance.objects.filter(
        mes, statut_professeur__in=StatutSeanceProfesseur.COMPTEES,
        date__range=(remuneration.premier_du_mois(jour), remuneration.dernier_du_mois(jour))).aggregate(h=Coalesce(Sum("heures_effectuees"), Decimal("0")))["h"]
    affectations = AffectationProfesseur.objects.filter(professeur_id=fiche, annee_scolaire=annee).select_related("classe", "matiere") if annee else []
    mes_evaluations = []
    if annee:
        a_completer = Evaluation.objects.filter(annee_scolaire=annee, trimestre=trimestre_courant(annee, jour)).annotate(
            nb_notes=Count("notes"), effectif=Coalesce(Subquery(_effectif_classe(), output_field=IntegerField()), 0),
        ).filter(nb_notes__lt=F("effectif")).select_related("classe", "matiere")
        mes_evaluations = [
            e for e in a_completer if any(a.classe_id == e.classe_id and a.matiere_id == e.matiere_id for a in affectations)
        ][:6]
    dernier_releve = ReleveRemuneration.objects.filter(professeur_id=fiche, statut=StatutReleve.VALIDE).order_by("-mois").first()
    totaux = remuneration.totaux(dernier_releve) if dernier_releve else None
    return {
        "fiche_liee": True,
        "prochains_cours": prochains[:6],
        "mes_classes": [{"classe": a.classe.nom, "matiere": a.matiere.nom_affiche} for a in affectations],
        "seances_a_valider": {"nombre": a_valider.count(), "liste": [{"date": s.date.isoformat(), "classe": s.classe.nom, "matiere": s.matiere.nom_affiche} for s in a_valider[:5]]},
        "heures_du_mois": _texte(heures_mois),
        "historique_seances": [{"date": s.date.isoformat(), "classe": s.classe.nom, "matiere": s.matiere.nom_affiche, "heures": _texte(s.heures_effectuees)} for s in effectuees[:5]],
        "saisie_notes": [{"classe": e.classe.nom, "matiere": e.matiere.nom_affiche, "libelle": e.libelle, "manquantes": e.effectif - e.nb_notes} for e in mes_evaluations],
        "remuneration": {"mois": dernier_releve.mois.isoformat(), "net": _texte(totaux["net"]), "paye": _texte(totaux["paye"]), "solde": _texte(totaux["solde"])} if dernier_releve else None,
    }


SECTIONS = {
    "effectifs": effectifs, "structure": structure, "presences_etudiants": presences_etudiants,
    "presences_professeurs": presences_professeurs, "notifications": notifications, "remuneration": remuneration_section,
    "scolarite": scolarite_section, "emploi_du_temps": emploi_du_temps_section, "evaluations": evaluations_section,
    "mon_espace": mon_espace,
}

SECTIONS_PAR_ROLE = {
    Role.ADMINISTRATEUR: ["effectifs", "structure", "presences_etudiants", "presences_professeurs", "notifications",
                          "remuneration", "scolarite", "emploi_du_temps", "evaluations"],
    Role.DIRECTEUR: ["effectifs", "structure", "presences_etudiants", "presences_professeurs", "notifications",
                     "remuneration", "scolarite", "emploi_du_temps", "evaluations"],
    Role.RESPONSABLE_SCOLARITE: ["effectifs", "structure", "presences_etudiants", "notifications"],
    Role.RESPONSABLE_PEDAGOGIQUE: ["structure", "evaluations", "presences_etudiants", "presences_professeurs", "emploi_du_temps"],
    Role.COMPTABLE: ["scolarite", "remuneration"],
    Role.PROFESSEUR: ["mon_espace"],
}


def tableau_de_bord(utilisateur):
    maintenant = timezone.localtime()
    contexte = {"utilisateur": utilisateur, "annee": annee_courante(), "aujourdhui": maintenant.date(), "maintenant": maintenant}
    annee = contexte["annee"]
    return {
        "role": utilisateur.role,
        "date": contexte["aujourdhui"].isoformat(),
        "annee_scolaire": {"id": annee.pk, "libelle": annee.libelle} if annee else None,
        "sections": {nom: SECTIONS[nom](contexte) for nom in SECTIONS_PAR_ROLE.get(utilisateur.role, [])},
    }

