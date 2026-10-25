from django.db.models import Q
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.commun.constantes import MODULES_PAR_ROLE
from apps.etudiants.models import Etudiant
from apps.professeurs.models import Professeur
from apps.referentiels.models import Classe, Matiere
from . import services


class TableauDeBordView(APIView):
    """Indicateurs reels adaptes au role de l'utilisateur connecte : chaque role ne recoit
    QUE ses sections (le filtrage est fait ici, cote serveur)."""

    def get(self, request):
        return Response(services.tableau_de_bord(request.user))


class RechercheGlobaleView(APIView):
    """Recherche transversale de la barre du haut : etudiants, professeurs, classes, matieres.
    Chaque categorie n'est interrogee que si le menu du role y donne acces (meme regle que l'interface)."""

    LIMITE = 5

    def get(self, request):
        terme = (request.query_params.get("q") or "").strip()
        modules = set(MODULES_PAR_ROLE.get(request.user.role, []))
        if len(terme) < 2:
            return Response({"termes": terme, "resultats": []})
        mots = terme.split()

        def contient(champs):
            condition = Q()
            for mot in mots:
                sous = Q()
                for champ in champs:
                    sous |= Q(**{f"{champ}__icontains": mot})
                condition &= sous
            return condition

        resultats = []
        if "etudiants" in modules:
            for e in Etudiant.objects.filter(contient(["matricule", "nom", "prenom", "numero_national"]))[: self.LIMITE]:
                resultats.append({"type": "Etudiant", "libelle": e.nom_complet, "detail": e.matricule, "chemin": "/etudiants/tous", "recherche": e.matricule})
        if "professeurs" in modules:
            for p in Professeur.objects.filter(contient(["matricule", "nom", "prenom"]))[: self.LIMITE]:
                resultats.append({"type": "Professeur", "libelle": p.nom_complet, "detail": p.matricule, "chemin": "/professeurs", "recherche": p.matricule})
        if "classes" in modules:
            for c in Classe.objects.filter(contient(["nom"])).select_related("annee_scolaire")[: self.LIMITE]:
                resultats.append({"type": "Classe", "libelle": c.nom, "detail": c.annee_scolaire.libelle, "chemin": "/classes", "recherche": c.nom})
        if "matieres" in modules:
            for m in Matiere.objects.filter(contient(["nom", "code"]))[: self.LIMITE]:
                resultats.append({"type": "Matiere", "libelle": m.nom, "detail": m.code, "chemin": "/matieres", "recherche": m.code})
        return Response({"termes": terme, "resultats": resultats})
