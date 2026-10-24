"""Regles metier de la remuneration des professeurs.

    montant brut = somme(heures validees x tarif applicable)
    montant net  = brut + primes - retenues
    solde        = net - somme des paiements (les annulations sont negatives)
"""

import calendar
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.commun.audit import enregistrer_audit
from apps.commun.exceptions import ErreurMetier
from apps.commun.references import prochaine_reference
from apps.commun.constantes import ModeRemuneration
from apps.presences.models import Seance, StatutSeanceProfesseur
from apps.professeurs.models import Professeur
from apps.referentiels.models import AnneeScolaire
from .models import (
    AjustementReleve, CorrectionHeures, LigneReleve, PaiementProfesseur, ReleveRemuneration, StatutPaiement,
    StatutReleve, TarifProfesseurMatiere, TypeAjustement, TypePaiement,
)

CENTIEME = Decimal("0.01")
ZERO = Decimal("0.00")


def arrondi(valeur):
    return Decimal(valeur).quantize(CENTIEME, rounding=ROUND_HALF_UP)


def lire_montant(brut, nom="montant"):
    """Montant strictement positif a 2 decimales maximum."""
    try:
        valeur = Decimal(str(brut).strip().replace(",", "."))
    except Exception:
        raise ErreurMetier(f"{nom.capitalize()} invalide.")
    if not valeur.is_finite() or valeur != valeur.quantize(CENTIEME):
        raise ErreurMetier(f"{nom.capitalize()} : 2 decimales maximum.")
    if valeur <= 0:
        raise ErreurMetier(f"{nom.capitalize()} doit etre strictement positif.")
    return valeur


def premier_du_mois(jour):
    return jour.replace(day=1)


def dernier_du_mois(jour):
    return jour.replace(day=calendar.monthrange(jour.year, jour.month)[1])


# ------------------------------------------------------------------ totaux

def totaux(releve):
    """Montants d'un releve : instantane fige s'il est valide, calcul courant sinon."""
    paye = sum((p.montant for p in releve.paiements.all()), ZERO)
    if releve.statut == StatutReleve.VALIDE:
        heures, brut = releve.heures_total, releve.montant_brut
        primes, retenues, net = releve.total_primes, releve.total_retenues, releve.montant_net
    else:
        lignes = list(releve.lignes.all())
        heures = sum((l.heures for l in lignes), ZERO)
        if releve.professeur.mode_remuneration == ModeRemuneration.FIXE:
            brut = arrondi(releve.professeur.salaire_fixe)
        else:
            brut = sum((l.montant for l in lignes), ZERO)
        ajustements = list(releve.ajustements.all())
        primes = sum((a.montant for a in ajustements if a.type == TypeAjustement.PRIME), ZERO)
        retenues = sum((a.montant for a in ajustements if a.type == TypeAjustement.RETENUE), ZERO)
        net = brut + primes - retenues
    if releve.statut != StatutReleve.VALIDE or paye <= 0:
        statut_paiement = StatutPaiement.NON_PAYE
    elif paye < net:
        statut_paiement = StatutPaiement.PARTIEL
    else:
        statut_paiement = StatutPaiement.PAYE
    return {
        "heures": arrondi(heures), "brut": arrondi(brut), "primes": arrondi(primes), "retenues": arrondi(retenues),
        "net": arrondi(net), "paye": arrondi(paye), "solde": arrondi(net - paye), "statut_paiement": statut_paiement,
    }


# -------------------------------------------------------------- generation

def _annee_du_mois(mois):
    annee = AnneeScolaire.objects.filter(date_debut__lte=dernier_du_mois(mois), date_fin__gte=mois).order_by("-active", "-date_debut").first()
    if annee is None:
        raise ErreurMetier(f"Aucune annee scolaire ne couvre {mois:%m/%Y}.")
    return annee


def seances_du_professeur(professeur, debut, fin):
    """Seances dont les heures reviennent au professeur (le remplacant pour une seance
    remplacee) : seuls les statuts effectue / retard / remplace donnent des heures."""
    return Seance.objects.filter(
        date__range=(debut, fin), heures_effectuees__gt=0,
    ).filter(
        Q(professeur=professeur, statut_professeur__in=(StatutSeanceProfesseur.EFFECTUE, StatutSeanceProfesseur.RETARD))
        | Q(professeur_remplacant=professeur, statut_professeur=StatutSeanceProfesseur.REMPLACE)
    ).select_related("classe", "matiere")


@transaction.atomic
def generer_releve(professeur, mois, utilisateur):
    """Cree ou recalcule le releve BROUILLON du mois. Les seances deja comptees dans
    un autre releve ne sont jamais reprises (aucune seance comptee deux fois)."""
    mois = premier_du_mois(mois)
    releve = ReleveRemuneration.objects.select_for_update().filter(professeur=professeur, mois=mois).first()
    if releve and releve.statut == StatutReleve.VALIDE:
        raise ErreurMetier(f"Le releve de {professeur.nom_complet} pour {mois:%m/%Y} est deja valide.")
    if releve is None:
        releve = ReleveRemuneration.objects.create(
            professeur=professeur, annee_scolaire=_annee_du_mois(mois), mois=mois, cree_par=utilisateur)
    else:
        releve.lignes.all().delete()   # libere les seances de ce brouillon avant de les reprendre
    releve.mode_remuneration = professeur.mode_remuneration
    releve.save(update_fields=["mode_remuneration"])

    tarifs = {t.matiere_id: t.tarif_horaire for t in TarifProfesseurMatiere.objects.filter(professeur=professeur)}
    horaire = professeur.mode_remuneration == ModeRemuneration.HORAIRE
    lignes = []
    for seance in seances_du_professeur(professeur, mois, dernier_du_mois(mois)).exclude(ligne_releve__isnull=False):
        tarif = tarifs.get(seance.matiere_id, professeur.tarif_horaire) if horaire else ZERO
        lignes.append(LigneReleve(
            releve=releve, seance=seance, classe=seance.classe, matiere=seance.matiere, date=seance.date,
            heures=seance.heures_effectuees, tarif=tarif, montant=arrondi(seance.heures_effectuees * tarif),
        ))
    LigneReleve.objects.bulk_create(lignes)
    return releve


def generer_releves_du_mois(mois, utilisateur):
    """Releves de tous les professeurs actifs ayant des heures (ou un salaire fixe)."""
    mois = premier_du_mois(mois)
    crees = []
    for professeur in Professeur.objects.filter(statut="ACTIF"):
        a_des_heures = seances_du_professeur(professeur, mois, dernier_du_mois(mois)).exists()
        existe = ReleveRemuneration.objects.filter(professeur=professeur, mois=mois).exists()
        if a_des_heures or existe or professeur.mode_remuneration == ModeRemuneration.FIXE:
            try:
                crees.append(generer_releve(professeur, mois, utilisateur))
            except ErreurMetier:
                continue   # releve deja valide : conserve tel quel
    return crees


# -------------------------------------------------------------- validation

def exiger_brouillon(releve):
    if releve.statut != StatutReleve.BROUILLON:
        raise ErreurMetier("Ce releve est valide : seules des corrections d'heures justifiees sont possibles.")


@transaction.atomic
def valider_releve(releve, utilisateur):
    releve = ReleveRemuneration.objects.select_for_update().get(pk=releve.pk)
    exiger_brouillon(releve)
    t = totaux(releve)
    horaire = releve.professeur.mode_remuneration == ModeRemuneration.HORAIRE
    if horaire and not releve.lignes.exists() and not releve.ajustements.exists():
        raise ErreurMetier("Ce releve ne contient aucune heure ni ajustement : rien a valider.")
    if t["net"] < 0:
        raise ErreurMetier(f"Le montant net serait negatif ({t['net']}) : verifiez les retenues.")
    releve.heures_total, releve.montant_brut = t["heures"], t["brut"]
    releve.total_primes, releve.total_retenues, releve.montant_net = t["primes"], t["retenues"], t["net"]
    releve.statut, releve.valide_par, releve.valide_le = StatutReleve.VALIDE, utilisateur, timezone.now()
    releve.save()
    enregistrer_audit(utilisateur, "VALIDATION_RELEVE", "ReleveRemuneration", releve.pk,
                      nouvelle_valeur={"professeur": releve.professeur.nom_complet, "mois": f"{releve.mois:%m/%Y}",
                                       "heures": str(t["heures"]), "net": str(t["net"])})
    return releve


@transaction.atomic
def rouvrir_releve(releve, utilisateur, motif):
    releve = ReleveRemuneration.objects.select_for_update().get(pk=releve.pk)
    if releve.statut != StatutReleve.VALIDE:
        raise ErreurMetier("Ce releve n'est pas valide.")
    if releve.paiements.exists():
        raise ErreurMetier("Des paiements sont enregistres : annulez-les avant de rouvrir le releve.")
    if not (motif or "").strip():
        raise ErreurMetier("Un motif est obligatoire pour rouvrir un releve valide.")
    releve.statut, releve.valide_par, releve.valide_le = StatutReleve.BROUILLON, None, None
    releve.save()
    enregistrer_audit(utilisateur, "REOUVERTURE_RELEVE", "ReleveRemuneration", releve.pk, nouvelle_valeur={"motif": motif.strip()})


# ----------------------------------------------------- primes et retenues

def ajouter_ajustement(releve, type_, libelle, montant, utilisateur):
    exiger_brouillon(releve)
    if type_ not in (TypeAjustement.PRIME, TypeAjustement.RETENUE):
        raise ErreurMetier("Type invalide (PRIME ou RETENUE).")
    if not (libelle or "").strip():
        raise ErreurMetier("Le libelle est obligatoire.")
    ajustement = AjustementReleve.objects.create(
        releve=releve, type=type_, libelle=libelle.strip()[:150], montant=lire_montant(montant), cree_par=utilisateur)
    enregistrer_audit(utilisateur, "AJUSTEMENT_RELEVE", "ReleveRemuneration", releve.pk,
                      nouvelle_valeur={"type": type_, "libelle": ajustement.libelle, "montant": str(ajustement.montant)})
    return ajustement


def supprimer_ajustement(ajustement, utilisateur):
    exiger_brouillon(ajustement.releve)
    enregistrer_audit(utilisateur, "SUPPRESSION_AJUSTEMENT", "ReleveRemuneration", ajustement.releve_id,
                      ancienne_valeur={"type": ajustement.type, "libelle": ajustement.libelle, "montant": str(ajustement.montant)})
    ajustement.delete()


# ---------------------------------------------------------------- paiements

@transaction.atomic
def enregistrer_paiement(releve, montant, mode, jour, observations, utilisateur):
    releve = ReleveRemuneration.objects.select_for_update().select_related("professeur").get(pk=releve.pk)
    if releve.statut != StatutReleve.VALIDE:
        raise ErreurMetier("Le releve d'heures doit etre valide avant tout paiement.")
    montant = lire_montant(montant)
    solde = totaux(releve)["solde"]
    if montant > solde:
        raise ErreurMetier(f"Le paiement ({montant}) depasse le solde restant a payer ({solde}).")
    paiement = PaiementProfesseur.objects.create(
        reference=prochaine_reference("REM"), releve=releve, montant=montant,
        type=TypePaiement.SOLDE if montant == solde else TypePaiement.ACOMPTE, mode_paiement=mode,
        date_paiement=jour, observations=(observations or "")[:255], enregistre_par=utilisateur,
    )
    enregistrer_audit(utilisateur, "PAIEMENT_PROFESSEUR", "PaiementProfesseur", paiement.reference,
                      nouvelle_valeur={"montant": str(montant), "type": paiement.type, "professeur": releve.professeur.nom_complet})
    return paiement


@transaction.atomic
def annuler_paiement(paiement, motif, utilisateur):
    """Annule un paiement par un paiement inverse (le paiement d'origine n'est jamais modifie)."""
    if paiement.type == TypePaiement.ANNULATION or paiement.montant <= 0:
        raise ErreurMetier("Une annulation ne peut pas etre annulee.")
    if hasattr(paiement, "annulation_par"):
        raise ErreurMetier("Ce paiement est deja annule.")
    if not (motif or "").strip():
        raise ErreurMetier("Un motif est obligatoire pour annuler un paiement.")
    annulation = PaiementProfesseur.objects.create(
        reference=prochaine_reference("REM"), releve=paiement.releve, type=TypePaiement.ANNULATION, montant=-paiement.montant,
        mode_paiement=paiement.mode_paiement, date_paiement=timezone.localdate(), annule=paiement,
        observations=f"Annulation de {paiement.reference} : {motif.strip()}"[:255], enregistre_par=utilisateur,
    )
    enregistrer_audit(utilisateur, "ANNULATION_PAIEMENT", "PaiementProfesseur", paiement.reference,
                      nouvelle_valeur={"annulation": annulation.reference, "montant": str(paiement.montant), "motif": motif.strip()})
    return annulation


# ------------------------------------------------- corrections d'heures

@transaction.atomic
def corriger_heures(releve, ligne, nouvelles_heures, motif, utilisateur):
    """Corrige les heures d'une seance deja comptee dans un releve VALIDE : motif obligatoire,
    montants recalcules, correction conservee (CorrectionHeures) et auditee."""
    releve = ReleveRemuneration.objects.select_for_update().get(pk=releve.pk)
    if releve.statut != StatutReleve.VALIDE:
        raise ErreurMetier("Releve non valide : modifiez-le directement (brouillon).")
    if ligne.releve_id != releve.pk:
        raise ErreurMetier("Cette ligne n'appartient pas a ce releve.")
    if not (motif or "").strip():
        raise ErreurMetier("Un motif est obligatoire pour corriger des heures deja validees.")
    try:
        heures = Decimal(str(nouvelles_heures).strip().replace(",", "."))
    except Exception:
        raise ErreurMetier("Nombre d'heures invalide.")
    if not heures.is_finite() or heures < 0 or heures != heures.quantize(CENTIEME):
        raise ErreurMetier("Heures : nombre positif ou nul, 2 decimales maximum.")
    if heures == ligne.heures:
        raise ErreurMetier("Les heures sont inchangees.")
    ancien_montant, ancien_heures = ligne.montant, ligne.heures
    nouveau_montant = arrondi(heures * ligne.tarif)
    nouveau_net = releve.montant_net - ancien_montant + nouveau_montant
    paye = totaux(releve)["paye"]
    if nouveau_net < paye:
        raise ErreurMetier(f"Le nouveau net ({nouveau_net}) serait inferieur aux paiements deja effectues ({paye}) : annulez d'abord un paiement.")
    ligne.heures, ligne.montant = heures, nouveau_montant
    ligne.save(update_fields=["heures", "montant"])
    releve.heures_total += heures - ancien_heures
    if releve.mode_remuneration != ModeRemuneration.FIXE:
        releve.montant_brut += nouveau_montant - ancien_montant
        releve.montant_net = nouveau_net
    releve.save()
    CorrectionHeures.objects.create(
        releve=releve, seance=ligne.seance, anciennes_heures=ancien_heures, nouvelles_heures=heures,
        ancien_montant=ancien_montant, nouveau_montant=nouveau_montant, motif=motif.strip()[:255], corrige_par=utilisateur)
    enregistrer_audit(utilisateur, "CORRECTION_HEURES", "ReleveRemuneration", releve.pk,
                      ancienne_valeur={"heures": str(ancien_heures), "montant": str(ancien_montant)},
                      nouvelle_valeur={"heures": str(heures), "montant": str(nouveau_montant), "motif": motif.strip(), "seance": ligne.seance_id})
    return ligne


# ------------------------------------------------------------ consultation

def heures_par_matiere_et_classe(professeur, du, au):
    """Heures effectuees par matiere et par classe sur une periode, avec ce qui est
    deja compte dans un releve (verification avant de generer/valider)."""
    lignes = defaultdict(lambda: {"heures": ZERO, "seances": 0, "comptabilisees": ZERO})
    for s in seances_du_professeur(professeur, du, au).select_related("ligne_releve"):
        cle = (s.matiere_id, s.matiere.nom, s.classe_id, s.classe.nom)
        ligne = lignes[cle]
        ligne["heures"] += s.heures_effectuees
        ligne["seances"] += 1
        if hasattr(s, "ligne_releve"):
            ligne["comptabilisees"] += s.heures_effectuees
    detail = [
        {"matiere": c[0], "matiere_nom": c[1], "classe": c[2], "classe_nom": c[3], "heures": str(v["heures"]),
         "seances": v["seances"], "heures_comptabilisees": str(v["comptabilisees"]),
         "heures_a_comptabiliser": str(v["heures"] - v["comptabilisees"])}
        for c, v in sorted(lignes.items(), key=lambda t: (t[0][1], t[0][3]))
    ]
    return {"total_heures": str(sum((v["heures"] for v in lignes.values()), ZERO)), "detail": detail}
