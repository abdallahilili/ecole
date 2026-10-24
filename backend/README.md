# Gestion d'ecole privee - Backend (Phases 1 a 3)

Backend Django REST Framework pour la gestion d'une ecole privee
(Administration, Scolarite/Inscriptions, Professeurs). Livraison
correspondant aux phases 1 a 3 du cahier des charges :

1. Fondations (authentification JWT, 6 roles, audit).
2. Referentiels scolaires (annees scolaires, niveaux, classes, groupes,
   salles, matieres avec coefficients variables par classe).
3. Etudiants, inscriptions, frais de scolarite, professeurs et
   affectations.

Les phases suivantes (presences + notifications WhatsApp via liens
wa.me, evaluations/bulletins, emplois du temps par algorithme
genetique, remuneration des professeurs) seront livrees separement.

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

## Modules exposes (phases 1-3)

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

## Tests

31 tests couvrant les regles metier principales (une seule annee active,
capacite classe/salle, coefficients variables par classe, capacite des
inscriptions, immuabilite des paiements, import/export Excel, permissions
par role) :

```bash
export UTILISER_SQLITE=1
python manage.py test apps.tests -v 2
```

## A configurer pour les phases suivantes

- **WhatsApp** : la notification des parents (phase 4) sera implementee
  via des liens `wa.me` pre-remplis (clic manuel par le personnel), suite
  a la decision explicite du client de ne pas utiliser l'API WhatsApp
  Business. Aucune configuration externe n'est requise pour cette
  approche.
- **MySQL/MariaDB** : fournir les identifiants dans `.env` avant la mise
  en production (le developpement/les tests peuvent utiliser SQLite via
  `UTILISER_SQLITE=1`).
