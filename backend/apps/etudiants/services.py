from .models import Inscription


def eleves_classe(classe_id, annee_id):
    """Inscriptions actives de la classe, par ordre alphabetique : une liste
    d'appel ou de notes ne contient QUE les eleves de la classe choisie."""
    return (
        Inscription.objects
        .filter(classe_id=classe_id, annee_scolaire_id=annee_id, statut="ACTIVE")
        .select_related("etudiant")
        .order_by("etudiant__nom", "etudiant__prenom", "etudiant_id")
    )
