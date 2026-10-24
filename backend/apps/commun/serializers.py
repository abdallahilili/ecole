from rest_framework import serializers
from .models import JournalAudit


class JournalAuditSerializer(serializers.ModelSerializer):
    utilisateur_nom = serializers.SerializerMethodField()

    class Meta:
        model = JournalAudit
        fields = ["id", "date_action", "utilisateur", "utilisateur_nom", "action", "modele",
                  "reference_objet", "ancienne_valeur", "nouvelle_valeur"]

    def get_utilisateur_nom(self, obj):
        return str(obj.utilisateur) if obj.utilisateur else "Systeme"
