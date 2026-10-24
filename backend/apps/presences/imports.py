"""Import Excel des presences : analyse (sans ecriture), puis application.

Regles : aucune ecriture avant confirmation ; tout-ou-rien (une seule
ligne en erreur bloque l'import) ; une presence deja saisie n'est jamais
ecrasee silencieusement (elle apparait comme MODIFIE et n'est remplacee
que sur demande explicite) ; une seance validee est verrouillee."""

import re
import unicodedata
from datetime import date, datetime, time

from django.db import transaction

from apps.commun.audit import enregistrer_audit
from apps.commun.excel import lire_classeur, texte
from apps.etudiants.models import Etudiant
from .exports import (
    CODES_STATUT, LIGNE_ENTETE_IMPORT, META_ANNEE, META_CLASSE, META_DATE, META_DEBUT, META_FIN,
    META_MATIERE, PREMIERE_LIGNE_IMPORT,
)
from .models import PresenceEtudiant, StatutPresence
from .services import eleves_classe

SYNONYMES_STATUT = {
    "PRESENT": StatutPresence.PRESENT, "ABSENT": StatutPresence.ABSENT, "RETARD": StatutPresence.RETARD,
    **CODES_STATUT,
}


def _sans_accent(valeur):
    return "".join(c for c in unicodedata.normalize("NFD", valeur) if unicodedata.category(c) != "Mn")


def lire_statut(valeur):
    """'P', 'present', 'Présent'... -> constante, ou None si inconnu."""
    return SYNONYMES_STATUT.get(_sans_accent(texte(valeur)).upper())


def _matricule(valeur):
    if isinstance(valeur, float) and valeur.is_integer():
        valeur = int(valeur)
    return texte(valeur)


def _date_cellule(valeur):
    if isinstance(valeur, datetime):
        return valeur.date()
    if isinstance(valeur, date):
        return valeur
    try:
        return datetime.strptime(texte(valeur), "%Y-%m-%d").date()
    except ValueError:
        return None


def _heure_cellule(valeur):
    if isinstance(valeur, datetime):
        valeur = valeur.time()
    if isinstance(valeur, time):
        return valeur.strftime("%H:%M")
    correspondance = re.fullmatch(r"(\d{1,2}):(\d{2})(?::\d{2})?", texte(valeur))
    return f"{int(correspondance.group(1)):02d}:{correspondance.group(2)}" if correspondance else None


def verifier_metadonnees(feuille, cours):
    """Le fichier doit correspondre au cours choisi (annee, classe, matiere, date, horaires)."""
    attendu = [
        ("annee scolaire", texte(feuille.cell(row=META_ANNEE, column=2).value), cours["annee_scolaire"].libelle),
        ("classe", texte(feuille.cell(row=META_CLASSE, column=2).value), cours["classe"].nom),
        ("matiere", texte(feuille.cell(row=META_MATIERE, column=2).value), cours["matiere"].code),
    ]
    anomalies = [
        f"{nom} du fichier ('{lu or 'vide'}') different de celle choisie ('{voulu}')"
        for nom, lu, voulu in attendu if lu != voulu
    ]
    date_lue = _date_cellule(feuille.cell(row=META_DATE, column=2).value)
    if date_lue != cours["date"]:
        anomalies.append(
            f"date du fichier ({date_lue.isoformat() if date_lue else 'invalide'}) "
            f"differente de celle choisie ({cours['date'].isoformat()})"
        )
    for ligne, nom, voulu in (
        (META_DEBUT, "heure de debut", cours["heure_debut"]), (META_FIN, "heure de fin", cours["heure_fin"]),
    ):
        lue = _heure_cellule(feuille.cell(row=ligne, column=2).value)
        if lue != voulu.strftime("%H:%M"):
            anomalies.append(f"{nom} du fichier ({lue or 'invalide'}) differente de celle choisie ({voulu:%H:%M})")
    return anomalies


def analyser_import(fichier, cours, seance=None):
    """Analyse sans rien ecrire. `seance` : seance existante (ou None)."""
    feuille = lire_classeur(fichier).active
    inscriptions = {i.etudiant.matricule: i for i in eleves_classe(cours["classe"].id, cours["annee_scolaire"].id)}
    existantes = {p.etudiant_id: p for p in seance.presences.all()} if seance else {}
    autres_matricules = set(Etudiant.objects.exclude(matricule__in=list(inscriptions)).values_list("matricule", flat=True))

    resultat = {
        "anomalies_fichier": verifier_metadonnees(feuille, cours),
        "lignes": [], "non_renseignes": [],
        "seance_validee": bool(seance and seance.presences_validees),
    }
    vus, renseignes = set(), set()
    for numero, ligne in enumerate(feuille.iter_rows(min_row=PREMIERE_LIGNE_IMPORT, max_col=5, values_only=True),
                                    start=PREMIERE_LIGNE_IMPORT):
        ligne = tuple(ligne) + (None,) * (5 - len(ligne))
        if all(valeur in (None, "") for valeur in ligne[1:]):
            continue
        matricule, statut_brut, observation = _matricule(ligne[1]), ligne[3], texte(ligne[4])[:255]
        anomalies = []
        inscription = inscriptions.get(matricule)
        if not matricule:
            anomalies.append("matricule manquant (ligne incomplete)")
        elif inscription is None:
            anomalies.append(
                "etudiant hors de cette classe" if matricule in autres_matricules else "matricule inconnu"
            )
        elif matricule in vus:
            anomalies.append("matricule en double dans le fichier")
        vus.add(matricule)
        statut = lire_statut(statut_brut)
        if not texte(statut_brut):
            anomalies.append("statut manquant (ligne incomplete)")
        elif statut is None:
            anomalies.append(f"statut invalide '{texte(statut_brut)}' (attendu P, A ou R)")

        entree = {
            "ligne": numero, "matricule": matricule,
            "nom_complet": inscription.etudiant.nom_complet if inscription else texte(ligne[2]),
            "statut": statut, "observation": observation, "anomalies": anomalies,
            "etudiant": inscription.etudiant_id if inscription else None, "ancien_statut": None,
        }
        if anomalies:
            entree["etat"] = "ERREUR"
        else:
            renseignes.add(inscription.etudiant_id)
            ancienne = existantes.get(inscription.etudiant_id)
            if ancienne is None:
                entree["etat"] = "NOUVEAU"
            elif ancienne.statut == statut and ancienne.observation == observation:
                entree["etat"] = "IDENTIQUE"
            else:
                entree["etat"] = "MODIFIE"
                entree["ancien_statut"] = ancienne.statut
        resultat["lignes"].append(entree)

    resultat["non_renseignes"] = [
        i.etudiant.nom_complet for i in inscriptions.values() if i.etudiant_id not in renseignes
    ]
    etats = [entree["etat"] for entree in resultat["lignes"]]
    resultat["resume"] = {
        "lignes": len(etats), "nouveaux": etats.count("NOUVEAU"), "identiques": etats.count("IDENTIQUE"),
        "modifies": etats.count("MODIFIE"), "erreurs": etats.count("ERREUR"),
        "non_renseignes": len(resultat["non_renseignes"]),
    }
    return resultat


def blocages(resultat, remplacer):
    """Raisons pour lesquelles l'import ne peut pas etre confirme (liste vide = confirmable)."""
    raisons = list(resultat["anomalies_fichier"])
    resume = resultat["resume"]
    if resultat["seance_validee"]:
        raisons.append("la seance est validee : rouvrez-la avant d'importer")
    if resume["erreurs"]:
        raisons.append(f"{resume['erreurs']} ligne(s) en erreur")
    if resume["lignes"] == 0:
        raisons.append("le fichier ne contient aucune ligne de presence")
    if resume["modifies"] and not remplacer:
        raisons.append(
            f"{resume['modifies']} presence(s) deja saisie(s) seraient modifiees : "
            "confirmez explicitement leur remplacement"
        )
    return raisons


@transaction.atomic
def appliquer_import(seance, resultat, remplacer, utilisateur):
    appliquees = 0
    for entree in resultat["lignes"]:
        if entree["etat"] == "NOUVEAU" or (entree["etat"] == "MODIFIE" and remplacer):
            PresenceEtudiant.objects.update_or_create(
                seance=seance, etudiant_id=entree["etudiant"],
                defaults={"statut": entree["statut"], "observation": entree["observation"]},
            )
            appliquees += 1
    enregistrer_audit(
        utilisateur, "IMPORT_PRESENCES", "Seance", seance.pk,
        nouvelle_valeur={**resultat["resume"], "appliquees": appliquees, "remplacement": remplacer},
    )
    return appliquees
