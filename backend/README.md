# Gestion d'ecole privee - Backend (Phases 1 a 8)

Backend Django REST Framework pour la gestion d'une ecole privee. Voir le
`README.md` a la racine pour le detail des phases, `DEPLOIEMENT.md` pour la
mise en production.

## Installation

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env     # puis completer BD_* avec vos identifiants MySQL/MariaDB
python manage.py migrate
python manage.py createsuperuser   # ou creer un utilisateur via le shell (voir ci-dessous)
python manage.py runserver
```

Pour tester rapidement sans MySQL (SQLite en memoire) :

```bash
export UTILISER_SQLITE=1
python manage.py migrate
python manage.py test apps.tests
```

## Variables d'environnement (.env)

| Variable | Description |
|---|---|
| `CLE_SECRETE` | Cle secrete Django (a changer en production) |
| `DEBUG` | 1 en developpement, 0 en production |
| `UTILISER_SQLITE` | 1 pour utiliser SQLite au lieu de MySQL (tests rapides) |
| `BD_NOM`, `BD_UTILISATEUR`, `BD_MOT_DE_PASSE`, `BD_HOTE`, `BD_PORT` | Connexion MySQL/MariaDB |
| `ORIGINES_CORS` | Origines autorisees pour le frontend (separees par des virgules) |
| `HOTES_AUTORISES`, `FORCER_HTTPS` | Hotes autorises et durcissement HTTPS en production |
| `FICHIER_SQLITE` | Chemin du fichier SQLite (avec `UTILISER_SQLITE=1`) |
| `LOGO_ECOLE` | Logo imprime sur les documents PDF (facultatif) |
| `WHATSAPP_*` | Envoi automatique WhatsApp (facultatif, voir `DEPLOIEMENT.md`) |

La liste exhaustive et commentee est dans `.env.example`. Avec `DEBUG=0`, `CLE_SECRETE`
(32 caracteres minimum) est obligatoire.

## Creer le premier utilisateur administrateur

```bash
python manage.py shell -c "
from apps.utilisateurs.models import Utilisateur
from apps.commun.constantes import Role
Utilisateur.objects.create_user(
    identifiant='admin', mot_de_passe='CHANGEZ_MOI',
    nom='Administrateur', role=Role.ADMINISTRATEUR,
    is_staff=True, is_superuser=True,
)
"
```

## Modules exposes

- `api/auth/` : connexion (JWT), rafraichissement de jeton, profil (`/moi/`).
- `api/utilisateurs/` : gestion des comptes (6 roles).
- `api/referentiels/` : annees-scolaires, niveaux, classes, tarifs-classes
  (tarif en UM propre a chaque classe), groupes, salles, matieres,
  affectations-matiere-classe (coefficients/volumes horaires variables
  par classe).
- `api/etudiants/` : etudiants, inscriptions (avec controle de capacite
  de classe).
- `api/etudiants/etudiants/modele-import/`, `/exporter/`, `/importer/` :
  import/export Excel des etudiants (import tout-ou-rien, jamais
  d'ecrasement silencieux).
- `api/professeurs/` : professeurs, affectations (matiere/classe/groupe).
- `api/scolarite/` : grilles de frais par niveau, paiements (immuables,
  reference automatique `SCOL-AAAA-NNNNN`), `paiements/situation/<id_inscription>/`
  pour la situation mensuelle d'un eleve (equivalent numerique de la
  fiche papier de suivi des mensualites).

- `api/presences/` : seances, appel (present/absent/retard/justifie), historique, notifications WhatsApp, webhook.
- `api/evaluations/` : evaluations, notes (import/export Excel), resultats, bulletins PDF, classements.
- `api/emplois-du-temps/` : emplois, generation genetique, editeur de seances, verification des conflits, publication, PDF/Excel, planification, disponibilites.
- `api/remuneration/` : tarifs, releves mensuels, paiements, fiches PDF, etat mensuel.
- `api/tableau-de-bord/` : indicateurs par role ; `recherche/` : recherche globale.
- `api/parametres/` (parametres de l'ecole) et `api/journal-audit/`.

Toutes les listes acceptent `page`, `taille_page`, `tri`, `recherche`, des filtres par colonne et un export
(`exporter/` : xlsx, csv, pdf ; selection ou resultats filtres). Les champs triables/filtrables sont
deduits du serializer (jamais de champ sensible).

## Commandes de gestion

| Commande | Role |
|---|---|
| `charger_niveaux_classes [--annee ...]` | Cree Fondamental/College/Lycee et leurs classes (idempotent) |
| `charger_demo --mot-de-passe ...` | Donnees d'exemple (refuse une base non vide) |
| `traiter_notifications_whatsapp [--boucle]` | Envoie la file de notifications WhatsApp |

## Tests

307 tests (calculs, presences, evaluations, algorithme genetique, remuneration, securite par role,
listes avancees, tableau de bord, donnees de demonstration, bilinguisme francais/arabe) :

```bash
export UTILISER_SQLITE=1
python manage.py test apps.tests
```

## Notes de conception

- Les documents PDF utilisent des polices latines : le texte arabe n'y est pas imprime.
- Les notifications WhatsApp fonctionnent par file d'attente (`EN_ATTENTE`, `ENVOYE`, `LIVRE`, `ECHEC`) ;
  sans configuration `WHATSAPP_*`, un lien `wa.me` pre-rempli est propose (clic manuel du personnel).
- MySQL/MariaDB : fournir les identifiants dans `.env` ; le developpement et les tests peuvent utiliser SQLite.
