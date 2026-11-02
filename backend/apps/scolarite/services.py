"""Fiche de paiement de scolarite d'un eleve : un mois a payer par echeance (octobre -> juillet), avec etat de paiement.

L'etat d'un mois se deduit du registre immuable des paiements (PaiementScolarite) :
  - payer un mois ajoute un paiement du reste du ;
  - annuler un paiement ajoute un paiement negatif (correction par mouvement inverse, jamais de suppression).
La fiche, la page « Paiements de scolarite » et le tableau de bord lisent donc la meme source."""

from collections import defaultdict
from datetime import date
from decimal import Decimal

from django.db import transaction

from apps.commun.audit import enregistrer_audit
from apps.commun.exceptions import ErreurMetier
from apps.commun.parametres import VRAI, lire_parametre
from apps.commun.references import prochaine_reference
from apps.etudiants.models import Inscription
from apps.referentiels.models import TarifClasse
from .models import EcheanceScolarite, GrilleFrais, ModePaiement, PaiementScolarite, TypeFrais

ZERO = Decimal("0")
MOIS_DEBUT = 10          # la fiche commence en octobre


class EtatEcheance:
    NON_PAYE = "NON_PAYE"
    PARTIEL = "PARTIEL"
    PAYE = "PAYE"


# ------------------------------------------------------------------ montant et mois de la fiche

def montant_mensuel_defaut(classe):
    """Mensualite proposee pour une classe : son tarif, sinon la grille de frais de son niveau ; None si aucun n'existe."""
    tarif = TarifClasse.objects.filter(classe=classe).first()
    if tarif:
        return tarif.montant
    grille = GrilleFrais.objects.filter(annee_scolaire_id=classe.annee_scolaire_id, niveau_id=classe.niveau_id).first()
    return grille.montant_mensuel if grille else None


def annee_dix_mois():
    """Parametre « annee de 10 mois » (defaut : oui) : la fiche va d'octobre a juillet, sinon d'octobre a juin (9 mois)."""
    return str(lire_parametre("annee_dix_mois")).strip().lower() in VRAI


def mois_de_la_fiche(inscription):
    """Premiers jours des mois de la fiche : octobre -> juillet (10 mois) ou octobre -> juin (9 mois) selon le parametre."""
    nombre = 10 if annee_dix_mois() else 9
    debut = inscription.annee_scolaire.date_debut
    premier = max(debut.month, MOIS_DEBUT)   # annee commencee apres octobre : la fiche part du mois de rentree
    return [date(debut.year + (premier - 1 + i) // 12, (premier - 1 + i) % 12 + 1, 1) for i in range(nombre)]


# ------------------------------------------------------------------ etat des mois (deduit du registre)

def _paiements_par_mois(inscription):
    """{premier jour du mois: paiements de mensualite (annulations comprises), du plus ancien au plus recent}."""
    resultat = defaultdict(list)
    paiements = PaiementScolarite.objects.select_related("enregistre_par").filter(
        inscription=inscription, type_frais=TypeFrais.MENSUALITE, mois_concerne__isnull=False
    ).order_by("date_paiement", "id")
    for paiement in paiements:
        resultat[paiement.mois_concerne.replace(day=1)].append(paiement)
    return resultat


def _total(paiements):
    return sum((p.montant for p in paiements), ZERO)


def _nom_utilisateur(utilisateur):
    return f"{utilisateur.prenom} {utilisateur.nom}".strip() or utilisateur.identifiant


def mois_payes(inscription):
    """Mois (premier jour) ayant un paiement net positif."""
    return {mois for mois, paiements in _paiements_par_mois(inscription).items() if _total(paiements) > 0}


def paye_du_mois(inscription, mois):
    return _total(_paiements_par_mois(inscription).get(mois.replace(day=1), []))


def _etat(montant, paye):
    if paye <= 0:
        return EtatEcheance.NON_PAYE
    return EtatEcheance.PAYE if paye >= montant else EtatEcheance.PARTIEL


# ------------------------------------------------------------------ generation de la fiche

@transaction.atomic
def generer_echeances(inscription, montant=None):
    """Cree les mois manquants de la fiche et aligne les mois non payes sur la mensualite ; les mois payes ne changent pas.

    Mensualite : celle fournie, sinon celle de l'inscription, sinon le tarif de la classe. Sans aucune des trois, rien
    n'est cree et None est retourne (la fiche se genere plus tard, des qu'une mensualite est saisie). Sinon retourne le
    nombre de mois crees : relancer la fonction complete une fiche existante (ex. mois ajoute au calendrier)."""
    if montant is None:
        montant = inscription.montant_mensuel
    if montant is None:
        montant = montant_mensuel_defaut(inscription.classe)
    if montant is None:
        return None
    if inscription.montant_mensuel != montant:
        inscription.montant_mensuel = montant
        inscription.save(update_fields=["montant_mensuel"])

    existantes = {e.mois: e for e in inscription.echeances.all()}
    payes = mois_payes(inscription) if existantes else set()
    calendrier = mois_de_la_fiche(inscription)
    # Mois qui ne font plus partie du calendrier (ex. juillet quand l'annee passe a 9 mois) : retires s'ils ne sont pas payes.
    hors_calendrier = [e for mois, e in existantes.items() if mois not in calendrier and mois not in payes]
    EcheanceScolarite.objects.filter(pk__in=[e.pk for e in hors_calendrier]).delete()
    for echeance in hors_calendrier:
        del existantes[echeance.mois]
    modifiees = []
    for mois, echeance in existantes.items():
        if echeance.montant != montant and mois not in payes:
            echeance.montant = montant
            modifiees.append(echeance)
    EcheanceScolarite.objects.bulk_update(modifiees, ["montant"])
    nouvelles = [
        EcheanceScolarite(inscription=inscription, mois=mois, montant=montant)
        for mois in calendrier if mois not in existantes
    ]
    EcheanceScolarite.objects.bulk_create(nouvelles)
    return len(nouvelles)


def synchroniser_fiches_annee_active():
    """Applique le parametre « annee de 10 mois » aux fiches de l'annee active : juillet est ajoute, ou retire s'il n'est
    pas paye. Les annees precedentes ne changent pas. Retourne le nombre de fiches examinees."""
    fiches = Inscription.objects.filter(
        statut="ACTIVE", annee_scolaire__active=True, echeances__isnull=False
    ).distinct().select_related("classe", "annee_scolaire")
    nombre = 0
    for inscription in fiches:
        generer_echeances(inscription)
        nombre += 1
    return nombre


# ------------------------------------------------------------------ fiche

def construire_fiche(inscription):
    """Fiche de paiement : un element par mois (montant, paye, reste, etat, dernier paiement) et les totaux."""
    paiements = _paiements_par_mois(inscription)
    lignes = []
    for echeance in inscription.echeances.order_by("mois"):
        du_mois = paiements.get(echeance.mois, [])
        paye = max(_total(du_mois), ZERO)
        positifs = [p for p in du_mois if p.montant > 0]
        dernier = positifs[-1] if paye > 0 and positifs else None
        lignes.append({
            "id": echeance.id, "mois": echeance.mois, "montant": echeance.montant, "paye": paye,
            "reste": max(echeance.montant - paye, ZERO), "statut": _etat(echeance.montant, paye),
            "reference": dernier.reference if dernier else None,
            "date_paiement": dernier.date_paiement if dernier else None,
            "mode_paiement": dernier.mode_paiement if dernier else None,
            "encaisse_par": _nom_utilisateur(dernier.enregistre_par) if dernier else None,
        })
    etudiant, classe = inscription.etudiant, inscription.classe
    return {
        "inscription": inscription.id, "etudiant": inscription.etudiant_id, "etudiant_nom": etudiant.nom_complet,
        "matricule": etudiant.matricule, "numero_inscription": inscription.numero_inscription, "classe_nom": classe.nom, "annee_scolaire_libelle": inscription.annee_scolaire.libelle,
        "montant_mensuel": inscription.montant_mensuel,
        "lignes": lignes,
        "totaux": {
            "du": sum((l["montant"] for l in lignes), ZERO), "paye": sum((l["paye"] for l in lignes), ZERO),
            "reste": sum((l["reste"] for l in lignes), ZERO),
            "mois_payes": sum(1 for l in lignes if l["statut"] == EtatEcheance.PAYE), "nombre_mois": len(lignes),
        },
    }


def _montant_json(valeur):
    return f"{valeur:.2f}"


def fiche_en_json(fiche):
    """Fiche prete pour la reponse JSON : montants en texte (« 900.00 »), dates ISO."""
    def ligne(l):
        return {
            **l, "mois": l["mois"].isoformat(),
            "montant": _montant_json(l["montant"]), "paye": _montant_json(l["paye"]), "reste": _montant_json(l["reste"]),
            "date_paiement": l["date_paiement"].isoformat() if l["date_paiement"] else None,
        }
    return {
        **fiche,
        "montant_mensuel": _montant_json(fiche["montant_mensuel"]) if fiche["montant_mensuel"] is not None else None,
        "lignes": [ligne(l) for l in fiche["lignes"]],
        "totaux": {**fiche["totaux"], **{c: _montant_json(fiche["totaux"][c]) for c in ("du", "paye", "reste")}},
    }


# ------------------------------------------------------------------ changement d'etat

def _echeance_verrouillee(echeance):
    """Relit l'echeance en la verrouillant : deux clics simultanes ne creent pas deux paiements."""
    return EcheanceScolarite.objects.select_for_update().select_related("inscription").get(pk=echeance.pk)


@transaction.atomic
def payer_echeance(echeance, utilisateur, jour=None, mode=ModePaiement.ESPECES, observations=""):
    """Marque le mois comme paye : enregistre au registre le reste du de ce mois."""
    echeance = _echeance_verrouillee(echeance)
    reste = echeance.montant - paye_du_mois(echeance.inscription, echeance.mois)
    if reste <= 0:
        raise ErreurMetier("Ce mois est deja paye.")
    paiement = PaiementScolarite.objects.create(
        reference=prochaine_reference("SCOL"), inscription=echeance.inscription, type_frais=TypeFrais.MENSUALITE,
        mois_concerne=echeance.mois, montant=reste, mode_paiement=mode, date_paiement=jour or date.today(),
        enregistre_par=utilisateur, observations=(observations or "")[:255],
    )
    enregistrer_audit(
        utilisateur, "CREATION", "PaiementScolarite", paiement.reference,
        nouvelle_valeur={"montant": str(reste), "type": TypeFrais.MENSUALITE, "mois": echeance.mois.isoformat()},
    )
    return paiement


@transaction.atomic
def annuler_paiement_echeance(echeance, utilisateur, motif=""):
    """Remet le mois en « non paye » : ajoute au registre un paiement negatif qui annule ce qui avait ete verse."""
    echeance = _echeance_verrouillee(echeance)
    du_mois = _paiements_par_mois(echeance.inscription).get(echeance.mois, [])
    verse = _total(du_mois)
    if verse <= 0:
        raise ErreurMetier("Ce mois n'est pas paye : rien a annuler.")
    positifs = [p for p in du_mois if p.montant > 0]
    observations = "Annulation de " + ", ".join(p.reference for p in positifs)
    if motif:
        observations += f" - {motif}"
    annulation = PaiementScolarite.objects.create(
        reference=prochaine_reference("ANN-SCOL"), inscription=echeance.inscription, type_frais=TypeFrais.MENSUALITE,
        mois_concerne=echeance.mois, montant=-verse, mode_paiement=positifs[-1].mode_paiement, date_paiement=date.today(),
        enregistre_par=utilisateur, observations=observations[:255],
    )
    enregistrer_audit(
        utilisateur, "ANNULATION", "PaiementScolarite", annulation.reference,
        ancienne_valeur={"montant": str(verse), "mois": echeance.mois.isoformat()},
    )
    return annulation
