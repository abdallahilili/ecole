"""Envoi des notifications via l'API officielle WhatsApp Business Platform.

- Les messages sont envoyes avec un MODELE approuve par Meta (obligatoire
  hors fenetre de 24 h) : les 7 variables sont, dans l'ordre, nom de
  l'eleve, classe, matiere, date, heure de debut, heure de fin, ecole.
- Un message n'est `ENVOYE` que lorsque l'API a repondu en l'acceptant
  (identifiant de message recu) ; `LIVRE` n'est positionne que sur
  confirmation de livraison recue par le webhook.
- Echec transitoire (reseau, 5xx, 429) : nouvelle tentative avec delai
  croissant jusqu'a WHATSAPP_MAX_TENTATIVES ; echec definitif (4xx) :
  `ECHEC` immediat. Rejouable ensuite manuellement.
"""

import hashlib
import hmac
import json
import urllib.error
import urllib.request
from datetime import timedelta

from django.conf import settings
from django.db.models import F
from django.utils import timezone

from .models import CanalNotification, NotificationWhatsApp, StatutNotification
from .services import langue_message, parametres_message

ORDRE_VARIABLES = ("nom_complet", "classe", "matiere", "date", "heure_debut", "heure_fin", "etablissement")


class ErreurWhatsApp(Exception):
    def __init__(self, message, definitif=False):
        super().__init__(message)
        self.message = message
        self.definitif = definitif


def modele_et_langue(langue):
    """Nom et code de langue du modele approuve par Meta pour la langue du message (un modele par langue)."""
    if langue == "ar":
        return settings.WHATSAPP_MODELE_AR, settings.WHATSAPP_LANGUE_AR
    return settings.WHATSAPP_MODELE, settings.WHATSAPP_LANGUE


def api_configuree(langue="fr"):
    return bool(settings.WHATSAPP_JETON and settings.WHATSAPP_ID_NUMERO and modele_et_langue(langue)[0])


def envoyer_modele(telephone, variables, langue="fr"):
    """Envoie le modele approuve ; retourne l'identifiant du message accepte par l'API."""
    url = f"{settings.WHATSAPP_URL_API}/{settings.WHATSAPP_VERSION_API}/{settings.WHATSAPP_ID_NUMERO}/messages"
    nom_modele, code_langue = modele_et_langue(langue)
    corps = {
        "messaging_product": "whatsapp",
        "to": telephone,
        "type": "template",
        "template": {
            "name": nom_modele,
            "language": {"code": code_langue},
            "components": [{
                "type": "body",
                "parameters": [{"type": "text", "text": str(valeur)} for valeur in variables],
            }],
        },
    }
    requete = urllib.request.Request(
        url, data=json.dumps(corps).encode("utf-8"), method="POST",
        headers={"Authorization": f"Bearer {settings.WHATSAPP_JETON}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(requete, timeout=15) as reponse:
            donnees = json.loads(reponse.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read().decode("utf-8")).get("error", {}).get("message", "")
        except Exception:
            detail = ""
        definitif = 400 <= e.code < 500 and e.code != 429
        raise ErreurWhatsApp(f"API WhatsApp {e.code} : {detail or e.reason}", definitif=definitif)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise ErreurWhatsApp(f"Reseau : {e}", definitif=False)
    except ValueError:
        raise ErreurWhatsApp("Reponse de l'API illisible.", definitif=False)

    messages = donnees.get("messages") or []
    if not messages or not messages[0].get("id"):
        # Pas d'identifiant = acceptation non confirmee : jamais "envoye".
        raise ErreurWhatsApp("L'API n'a pas confirme l'acceptation du message.", definitif=False)
    return messages[0]["id"]


def delai_avant_nouvelle_tentative(tentatives):
    return timedelta(minutes=5 * 2 ** max(0, tentatives - 1))


def envoyer_notification(notification, maintenant=None):
    """Traite UNE notification en file. Retourne 'envoyee', 'reportee' ou 'echec'."""
    maintenant = maintenant or timezone.now()
    reclamee = NotificationWhatsApp.objects.filter(
        pk=notification.pk, statut=StatutNotification.EN_ATTENTE, tentatives=notification.tentatives,
    ).update(tentatives=F("tentatives") + 1)
    if not reclamee:  # un autre traitement l'a deja prise en charge
        return "ignoree"
    notification.refresh_from_db()

    langue = langue_message()
    parametres = parametres_message(notification.presence, langue)
    variables = [parametres[nom] for nom in ORDRE_VARIABLES]
    try:
        identifiant = envoyer_modele(notification.telephone, variables) if langue == "fr" else envoyer_modele(notification.telephone, variables, langue)
    except ErreurWhatsApp as e:
        notification.erreur = e.message[:500]
        if e.definitif or notification.tentatives >= settings.WHATSAPP_MAX_TENTATIVES:
            notification.statut = StatutNotification.ECHEC
            resultat = "echec"
        else:
            notification.prochaine_tentative = maintenant + delai_avant_nouvelle_tentative(notification.tentatives)
            resultat = "reportee"
    else:
        notification.statut = StatutNotification.ENVOYE
        notification.canal = CanalNotification.API
        notification.identifiant_message_api = identifiant
        notification.envoye_le = maintenant
        notification.erreur = ""
        resultat = "envoyee"
    notification.save()
    return resultat


def traiter_file(limite=50, maintenant=None):
    """Envoie les notifications en attente et echues. Appelee par le bouton
    'Envoyer maintenant' et par la commande `traiter_notifications_whatsapp`."""
    bilan = {"api_configuree": api_configuree(), "envoyees": 0, "reportees": 0, "echecs": 0}
    if not bilan["api_configuree"]:
        return bilan
    maintenant = maintenant or timezone.now()
    en_attente = NotificationWhatsApp.objects.filter(
        statut=StatutNotification.EN_ATTENTE, prochaine_tentative__lte=maintenant,
    ).exclude(telephone="").select_related("presence__etudiant", "presence__seance__classe", "presence__seance__matiere")
    for notification in en_attente.order_by("id")[:limite]:
        resultat = envoyer_notification(notification, maintenant)
        cle = {"envoyee": "envoyees", "reportee": "reportees", "echec": "echecs"}.get(resultat)
        if cle:
            bilan[cle] += 1
    return bilan


# ----------------------------------------------------------------- webhook

def signature_valide(corps, en_tete):
    """Verifie X-Hub-Signature-256 (HMAC-SHA256 du corps avec le secret de l'application)."""
    secret = settings.WHATSAPP_SECRET_APPLICATION
    if not secret or not en_tete or not en_tete.startswith("sha256="):
        return False
    attendu = hmac.new(secret.encode("utf-8"), corps, hashlib.sha256).hexdigest()
    return hmac.compare_digest(attendu, en_tete[len("sha256="):])


def appliquer_statuts(donnees):
    """Met a jour les notifications depuis un evenement 'statuses' du webhook."""
    modifiees = 0
    for entree in donnees.get("entry", []):
        for changement in entree.get("changes", []):
            for statut in changement.get("value", {}).get("statuses", []):
                notification = NotificationWhatsApp.objects.filter(identifiant_message_api=statut.get("id", "")).first()
                if notification is None:
                    continue
                etat = statut.get("status")
                if etat in ("delivered", "read"):
                    notification.statut = StatutNotification.LIVRE
                    notification.erreur = ""
                elif etat == "failed":
                    erreurs = statut.get("errors") or [{}]
                    notification.statut = StatutNotification.ECHEC
                    notification.erreur = str(erreurs[0].get("message") or erreurs[0].get("title") or "Echec de livraison")[:500]
                else:  # 'sent' : deja ENVOYE
                    continue
                notification.save(update_fields=["statut", "erreur"])
                modifiees += 1
    return modifiees
