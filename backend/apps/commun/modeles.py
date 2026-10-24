from django.db import models


class QuerySetImmuable(models.QuerySet):
    def update(self, *args, **kwargs):
        raise TypeError("Les enregistrements de ce type sont immuables : modification interdite.")

    def delete(self, *args, **kwargs):
        raise TypeError("Les enregistrements de ce type sont immuables : suppression interdite.")


class GestionnaireImmuable(models.Manager):
    def get_queryset(self):
        return QuerySetImmuable(self.model, using=self._db)


class ModeleImmuable(models.Model):
    """Base abstraite pour tout enregistrement constituant un historique
    immuable (paiements, journal d'audit...). Toute correction passe par
    un mouvement inverse, jamais par une modification/suppression."""

    objects = GestionnaireImmuable()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.pk is not None:
            try:
                existe = self.__class__.objects.filter(pk=self.pk).exists()
            except Exception:
                existe = False
            if existe:
                raise TypeError("Cet enregistrement est immuable : modification interdite apres creation.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError("Cet enregistrement est immuable : suppression interdite.")
