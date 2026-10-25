"""Briques communes des vues : permissions par role et listes avancees.

`ListeAvanceeMixin` ajoute a toute liste, de facon generique et sure :
  - ?recherche=a b        recherche globale (chaque mot doit etre trouve dans un champ de `search_fields`)
  - ?tri=nom | ?tri=-nom  tri serveur (plusieurs cles separees par des virgules)
  - ?col_<champ>=valeur   filtre par colonne (contient pour le texte, egalite sinon)
  - GET export/           export CSV / Excel / PDF du resultat filtre, de la page ou de la selection
  - POST supprimer-multiple/   suppression groupee (tout ou rien, memes regles que la suppression unitaire)
Seuls les champs reellement exposes par le serializer (hors ecriture seule et champs calcules)
sont triables/filtrables : aucun champ sensible n'est accessible par ce biais."""

import json

from django.db import models, transaction
from django.db.models import Q
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from . import exports_generiques as export
from .audit import enregistrer_audit
from .exceptions import ErreurMetier
from .permissions import PermissionParRole

VRAI = ("1", "true", "oui", "vrai")
MAX_SUPPRESSION_MULTIPLE = 500


def _champ_modele(modele, chemin):
    """Dernier champ ORM du chemin 'a__b__c' (None si invalide)."""
    champ = None
    for index, nom in enumerate(chemin.split("__")):
        try:
            champ = modele._meta.get_field(nom)
        except Exception:
            return None
        if index < len(chemin.split("__")) - 1:
            if not getattr(champ, "is_relation", False) or champ.related_model is None:
                return None
            modele = champ.related_model
    return champ


class ListeAvanceeMixin:
    search_fields = ()
    alias_tri = {}   # {"nom_complet": ("nom", "prenom")} : tri sur une propriete calculee
    # Listes : seuls les elements « en usage » sont renvoyes, sauf ?inactifs=1. `"auto"` : champ booleen `actif` du modele
    # s'il existe ; sinon un tuple (champ, valeur_en_usage) pour un champ existant (ex. ("statut", "ACTIF")) ou None.
    filtre_actif = "auto"

    def filtre_actif_courant(self):
        """(champ ORM, valeur en usage) de cette liste, ou None si le modele n'a pas de notion d'inactif."""
        if self.filtre_actif != "auto":
            return self.filtre_actif
        classe = self.get_serializer_class()
        modele = getattr(getattr(classe, "Meta", None), "model", None)
        champ = _champ_modele(modele, "actif") if modele is not None else None
        return ("actif", True) if isinstance(champ, models.BooleanField) else None

    # --------------------------------------------------------- champs exposes

    def champs_orm(self):
        """{champ du serializer: chemin ORM} pour les champs triables/filtrables."""
        if hasattr(self, "_cache_champs_orm"):
            return self._cache_champs_orm
        resultat = {}
        classe = self.get_serializer_class()
        modele = getattr(getattr(classe, "Meta", None), "model", None)
        if modele is not None:
            for nom, champ in classe().fields.items():
                if champ.write_only or isinstance(champ, serializers.SerializerMethodField):
                    continue
                chemin = (champ.source if champ.source not in (None, "*") else nom).replace(".", "__")
                if _champ_modele(modele, chemin) is not None:
                    resultat[nom] = chemin
        for nom, chemins in self.alias_tri.items():
            resultat.setdefault(nom, chemins)
        self._cache_champs_orm = resultat
        return resultat

    # --------------------------------------------------------------- filtrage

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        if getattr(self, "action", None) in ("retrieve", "update", "partial_update", "destroy"):
            return queryset
        params = self.request.query_params
        champs = self.champs_orm()

        # Listes (pas les actions sur un element) : par defaut, uniquement ce qui est en usage. Un filtre explicite
        # sur ce champ (?actif=, ?statut=, col_actif=...) ou ?inactifs=1 (afficher aussi les inactifs) le desactive.
        filtre = None if getattr(self, "detail", False) else self.filtre_actif_courant()
        if filtre and str(params.get("inactifs", "")).lower() not in VRAI and not params.get(filtre[0]) and not params.get(f"col_{filtre[0]}"):
            queryset = queryset.filter(**{filtre[0]: filtre[1]})

        mots = (params.get("recherche") or "").split()
        if mots and self.search_fields:
            for mot in mots:
                condition = Q()
                for champ in self.search_fields:
                    condition |= Q(**{f"{champ}__icontains": mot})
                queryset = queryset.filter(condition)

        modele = queryset.model
        for cle, valeur in params.items():
            if not cle.startswith("col_") or valeur == "":
                continue
            chemin = champs.get(cle[4:])
            if not isinstance(chemin, str):
                continue
            champ = _champ_modele(modele, chemin)
            if isinstance(champ, (models.CharField, models.TextField)):
                queryset = queryset.filter(**{f"{chemin}__icontains": valeur})
            elif isinstance(champ, models.BooleanField):
                queryset = queryset.filter(**{chemin: valeur.lower() in VRAI})
            elif champ is not None:
                try:
                    queryset = queryset.filter(**{chemin: valeur})
                except Exception:   # valeur incompatible avec le type du champ : filtre ignore
                    continue

        tri = []
        for cle in (params.get("tri") or "").split(","):
            cle = cle.strip()
            chemin = champs.get(cle.lstrip("-"))
            if not chemin:
                continue
            for element in (chemin if isinstance(chemin, (tuple, list)) else (chemin,)):
                tri.append(("-" if cle.startswith("-") else "") + element)
        if tri:
            queryset = queryset.order_by(*tri, "pk")
        return queryset

    # ----------------------------------------------------------------- export

    @action(detail=False, methods=["get"], url_path="export")
    def export_donnees(self, request):
        """?fichier=xlsx|csv|pdf &colonnes=[{"cle":..,"titre":..}] &ids=1,2,3 &titre=... (+ memes filtres que la liste)"""
        params = request.query_params
        qs = self.filter_queryset(self.get_queryset())
        if params.get("ids"):
            try:
                ids = [int(i) for i in params["ids"].split(",") if i.strip()]
            except ValueError:
                raise ErreurMetier("Parametre 'ids' invalide.")
            qs = qs.filter(pk__in=ids)
        serializer = self.get_serializer(qs[:export.LIMITE_LIGNES], many=True)
        champs_disponibles = {n for n, c in self.get_serializer().fields.items() if not c.write_only}

        try:
            demandees = json.loads(params["colonnes"]) if params.get("colonnes") else []
        except ValueError:
            raise ErreurMetier("Parametre 'colonnes' invalide.")
        colonnes = [(c["cle"], str(c.get("titre") or c["cle"])) for c in demandees
                    if isinstance(c, dict) and c.get("cle") in champs_disponibles]
        if not colonnes:
            colonnes = [(n, n) for n in self.get_serializer().fields if n in champs_disponibles]

        titres = [t for _, t in colonnes]
        lignes = export.lignes_de(serializer.data, colonnes)
        nom = f"export_{self.basename or 'liste'}"
        format_ = params.get("fichier", "xlsx")
        titre = params.get("titre") or self.basename or "Liste"
        if format_ == "csv":
            return export.reponse_csv(titres, lignes, nom)
        if format_ == "pdf":
            return export.reponse_pdf_liste(titre, titres, lignes, nom)
        if format_ == "xlsx":
            return export.reponse_xlsx_liste(titre, titres, lignes, nom)
        raise ErreurMetier("Format d'export invalide (xlsx, csv ou pdf).")


class ViewSetGestion(ListeAvanceeMixin, viewsets.ModelViewSet):
    permission_classes = [PermissionParRole]

    @action(detail=False, methods=["post"], url_path="supprimer-multiple")
    def supprimer_multiple(self, request):
        """{ids: [...]} : supprime la selection (tout ou rien). Memes droits et memes regles de
        conservation que la suppression unitaire ; la liste est limitee a 500 elements."""
        self.action = "destroy"           # applique les droits de la suppression
        self.check_permissions(request)
        ids = request.data.get("ids")
        if not isinstance(ids, list) or not ids:
            raise ErreurMetier("Selectionnez au moins un element.")
        if len(ids) > MAX_SUPPRESSION_MULTIPLE:
            raise ErreurMetier(f"Suppression limitee a {MAX_SUPPRESSION_MULTIPLE} elements a la fois.")
        objets = list(self.get_queryset().filter(pk__in=ids))
        if len(objets) != len(set(ids)):
            raise ErreurMetier("Certains elements sont introuvables ou ne vous sont pas accessibles : aucune suppression effectuee.")
        identifiants = [o.pk for o in objets]   # avant la suppression : Django remet pk a None apres delete()
        with transaction.atomic():
            for objet in objets:
                try:
                    self.perform_destroy(objet)
                except ErreurMetier as e:
                    raise ErreurMetier(f"{objet} : {e.message}")
            enregistrer_audit(request.user, "SUPPRESSION_MULTIPLE", self.basename or "liste", len(objets),
                              ancienne_valeur={"ids": identifiants})
        return Response({"supprimes": len(objets)})


class ViewSetLecture(ListeAvanceeMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = [PermissionParRole]
