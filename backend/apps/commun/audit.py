from .models import JournalAudit


def enregistrer_audit(utilisateur, action, modele, reference_objet, ancienne_valeur=None, nouvelle_valeur=None):
    JournalAudit.objects.create(
        utilisateur=utilisateur if utilisateur and utilisateur.is_authenticated else None,
        action=action, modele=modele, reference_objet=str(reference_objet),
        ancienne_valeur=ancienne_valeur, nouvelle_valeur=nouvelle_valeur,
    )
