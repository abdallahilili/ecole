"""Lecture des parametres de l'etablissement (table cle/valeur `Parametre`).

Chaque cle a une valeur par defaut : l'application fonctionne sans
configuration prealable. Ne jamais stocker ici de secret (jeton API,
mot de passe) : la table est lisible par tout utilisateur connecte, les
secrets restent dans les variables d'environnement du backend."""

from .models import Parametre

DEFAUTS = {
    "nom_etablissement": "Ecoles Privees El Adala - Kiffa",
    "telephone_etablissement": "",
    "entete_ministere": "Ministere de l'Education Nationale",
    "entete_region": "DREN de l'Assaba",
    # Versions arabes de l'entete des documents (utilisees quand l'interface est en arabe)
    "nom_etablissement_ar": "المدارس الخاصة العدالة - كيفة",
    "entete_ministere_ar": "وزارة التهذيب الوطني",
    "entete_region_ar": "المديرية الجهوية للتعليم بلعصابة",
    # Presences / WhatsApp
    "whatsapp_actif": "0",
    "retard_est_absence": "0",
    "langue_whatsapp": "fr",          # fr | ar : langue du message envoye aux parents
    # Evaluations
    "abs_justifiee": "exclure",       # exclure | zero
    "abs_non_justifiee": "zero",      # zero | exclure
    "moyenne_exige_toutes_evaluations": "0",
    "matiere_non_evaluee": "exclure",  # exclure | zero (le bulletin papier compte 0)
    "ex_aequo": "meme_rang",          # meme_rang | alphabetique
    "poids_trimestres": "1,1,1",
}

VRAI = ("1", "true", "oui", "vrai", "yes", "on")


def lire_parametre(cle, defaut=None):
    parametre = Parametre.objects.filter(cle=cle).first()
    if parametre is not None:
        return parametre.valeur
    return DEFAUTS.get(cle, defaut) if defaut is None else defaut


def lire_bool(cle):
    return str(lire_parametre(cle, "0")).strip().lower() in VRAI
