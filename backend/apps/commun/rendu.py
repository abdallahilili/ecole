"""Rendu JSON localise : en arabe, les messages renvoyes par l'API sont traduits avant l'envoi.

Les donnees saisies par les utilisateurs (noms, libelles...) ne sont jamais touchees : seuls les textes situes sous
une cle de message (detail, anomalies, conflits...) sont traduits, ou tous les textes d'une reponse d'erreur."""

from rest_framework.renderers import JSONRenderer

from .langue import est_arabe
from .traduction import traduire

CLES_MESSAGES = {
    "detail", "message", "messages", "anomalies", "erreurs", "blocages", "diagnostics", "conflits",
    "arret", "avertissements", "non_renseignes_message", "resume_texte",
}


def traduire_donnees(valeur, tout=False, dans_message=False):
    if isinstance(valeur, str):
        return traduire(valeur) if (tout or dans_message) else valeur
    if isinstance(valeur, dict):
        return {cle: traduire_donnees(v, tout, dans_message or cle in CLES_MESSAGES) for cle, v in valeur.items()}
    if isinstance(valeur, (list, tuple)):
        return [traduire_donnees(v, tout, dans_message) for v in valeur]
    return valeur


class RendererJSONLocalise(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        if data is not None and est_arabe():
            reponse = (renderer_context or {}).get("response")
            erreur = reponse is not None and reponse.status_code >= 400
            data = traduire_donnees(data, tout=erreur)
        return super().render(data, accepted_media_type, renderer_context)
