"""Documents PDF de la scolarite : fiche de paiement de l'annee (tous les mois) et recu d'un mois paye."""

from reportlab.lib.units import cm
from reportlab.platypus import Spacer

from apps.commun.pdf import Tableau as Table, STYLE_PETIT, STYLE_TITRE, construire_pdf, entete_etablissement, gras, p, style_tableau
from apps.remuneration.documents import nom_mois, um
from .models import ModePaiement
from .services import EtatEcheance

LIBELLES_ETAT = {EtatEcheance.NON_PAYE: "Non paye", EtatEcheance.PARTIEL: "Partiel", EtatEcheance.PAYE: "Paye"}
LIBELLES_MODE = dict(ModePaiement.CHOIX)


def _date(valeur):
    return f"{valeur:%d/%m/%Y}" if valeur else "-"


def _en_tete_eleve(fiche):
    """Identite de l'eleve : etiquette / valeur / etiquette / valeur (les colonnes s'inversent d'elles-memes en arabe)."""
    tableau = Table([
        [gras("Etudiant :"), p(fiche["etudiant_nom"]), gras("N° d'inscription :"), p(fiche["numero_inscription"])],
        [gras("Classe :"), p(fiche["classe_nom"]), gras("Annee scolaire :"), p(fiche["annee_scolaire_libelle"])],
    ], colWidths=[3 * cm, 6 * cm, 3 * cm, 6 * cm])
    tableau.setStyle(style_tableau(entete=False, grille=False))
    return tableau


def pdf_fiche(fiche):
    """Fiche de paiement : un mois par ligne (montant, paye, etat, date, mode, numero de recu) et les totaux."""
    elements = entete_etablissement() + [p("FICHE DE PAIEMENT DE LA SCOLARITE", STYLE_TITRE), _en_tete_eleve(fiche), Spacer(1, 8)]

    donnees = [["N°", "Mois", "Montant", "Paye", "Etat", "Date", "Mode", "Recu"]]
    for numero, ligne in enumerate(fiche["lignes"], start=1):
        paye = ligne["statut"] != EtatEcheance.NON_PAYE
        donnees.append([
            str(numero), p(nom_mois(ligne["mois"])), um(ligne["montant"]), um(ligne["paye"]) if paye else "-",
            p(LIBELLES_ETAT[ligne["statut"]]), _date(ligne["date_paiement"]),
            p(LIBELLES_MODE.get(ligne["mode_paiement"], "-")) if paye else "-", ligne["reference"] or "-",
        ])
    tableau = Table(donnees, repeatRows=1, colWidths=[0.9 * cm, 3 * cm, 2.6 * cm, 2.6 * cm, 1.9 * cm, 2.2 * cm, 1.9 * cm, 2.9 * cm])
    tableau.setStyle(style_tableau())
    elements += [tableau, Spacer(1, 8)]

    totaux = fiche["totaux"]
    bilan = Table([
        [gras("Total du"), um(totaux["du"])],
        [gras("Total paye"), um(totaux["paye"])],
        [gras("Reste a payer"), gras(um(totaux["reste"]))],
    ], colWidths=[6 * cm, 5 * cm])
    bilan.setStyle(style_tableau(entete=False))
    elements += [bilan, Spacer(1, 6), p("Montants en UM.", STYLE_PETIT)]

    signatures = Table([[p("Le parent / tuteur"), p("Le comptable")]], colWidths=[9 * cm, 9 * cm], rowHeights=[2 * cm])
    elements += [Spacer(1, 14), signatures]
    return construire_pdf(elements, titre="Fiche de paiement de la scolarite")


def pdf_recu(fiche, ligne):
    """Recu d'un mois paye : eleve, mois, montant verse, mode, numero de recu et date."""
    elements = entete_etablissement() + [p("RECU DE PAIEMENT", STYLE_TITRE), _en_tete_eleve(fiche), Spacer(1, 8)]

    detail = [
        [gras("Numero du recu"), p(ligne["reference"] or "-")],
        [gras("Date de paiement"), _date(ligne["date_paiement"])],
        [gras("Mensualite du mois"), p(nom_mois(ligne["mois"]))],
        [gras("Montant verse"), gras(um(ligne["paye"]))],
        [gras("Mode de paiement"), p(LIBELLES_MODE.get(ligne["mode_paiement"], "-"))],
        [gras("Encaisse par"), p(ligne["encaisse_par"] or "-")],
    ]
    if ligne["reste"] > 0:
        detail.append([gras("Reste a payer pour ce mois"), um(ligne["reste"])])
    tableau = Table(detail, colWidths=[6 * cm, 12 * cm])
    tableau.setStyle(style_tableau(entete=False))
    elements += [tableau, Spacer(1, 6), p("Montants en UM.", STYLE_PETIT)]

    signatures = Table([[p("Le parent / tuteur"), p("Le comptable (signature et cachet)")]], colWidths=[9 * cm, 9 * cm], rowHeights=[2.5 * cm])
    elements += [Spacer(1, 14), signatures]
    return construire_pdf(elements, titre="Recu de paiement")
