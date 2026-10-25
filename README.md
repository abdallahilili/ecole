# Gestion d'ecole privee – application complete

Application de gestion d'un college/lycee prive (Mauritanie) : **backend** Django REST Framework + MySQL,
**frontend** React / TypeScript / Tailwind.

```
backend/    API Django (JWT, 6 roles, audit, calculs verifies cote serveur)
frontend/   Application web (React 19, Vite)
DEPLOIEMENT.md   Mise en production (MySQL, waitress, HTTPS, sauvegardes, WhatsApp)
```

## Fonctionnalites par phase

| Phase | Contenu |
|---|---|
| 1 | Authentification JWT, 6 roles (administrateur, directeur, responsable scolarite, responsable pedagogique, comptable, professeur), journal d'audit immuable, politique de mots de passe |
| 2 | Referentiels : annees scolaires (3 trimestres, 3 examens), niveaux, classes, salles, groupes, matieres avec **coefficients propres a chaque classe**, tarifs par classe |
| 3 | Etudiants, inscriptions, frais de scolarite et paiements immuables, professeurs et affectations, import/export Excel |
| 4 | Presences par seance, absences/retards/justifications, notifications WhatsApp aux parents (file d'envoi, relances, statuts), import Excel, historique |
| 5 | Evaluations et notes (saisie au clavier, bareme, absences), moyennes ponderees, classement, bulletins PDF individuels et par classe, verrouillage apres validation |
| 6 | Emplois du temps par **algorithme genetique** (contraintes obligatoires + preferences), editeur glisser-deposer avec refus de conflit explique, publication versionnee, PDF/Excel, creation des seances de presence |
| 7 | Remuneration des professeurs : releves mensuels calcules depuis les seances reellement effectuees, primes/retenues, validation, paiements immuables, fiche de paie PDF, espace « Ma remuneration » |
| 8 | Tableaux de bord par role (donnees reelles uniquement), recherche globale, tableaux avances (tri/filtre/selection/export serveur), durcissement securite, tests, deploiement |

## Application bilingue (francais / arabe)

Un selecteur **Français | العربية** (page de connexion et barre du haut) bascule toute l'application ; le choix est
memorise dans le navigateur.

- **Interface** : tous les textes, avec mise en page de droite a gauche en arabe (menu, tableaux, formulaires, calendrier).
- **Messages du serveur** (erreurs, validations, conflits d'emploi du temps...) : traduits selon la langue de l'interface.
- **Documents** : bulletins, listes de presence, emplois du temps, fiches et etats de paie en PDF (police Amiri incluse,
  lettres reliees, colonnes inversees) ; exports Excel/CSV avec en-tetes traduits et feuilles de droite a gauche.
- **Noms arabes** : champ « Nom (arabe) » pour les matieres et les niveaux, et noms arabes de l'ecole (*Parametres*) ; ils
  s'affichent et s'impriment quand la langue est l'arabe, avec repli sur le nom principal s'ils sont vides. Les noms des
  eleves et des professeurs peuvent etre saisis en caracteres arabes ou latins (les deux s'impriment correctement).
- **WhatsApp** : la langue du message est celle des parents (*Parametres*), independante de la langue de l'ecran.

Pour ajouter ou corriger une traduction : `frontend/src/i18n/ar.ts` (interface) et `backend/apps/commun/messages_ar.py`,
`libelles_ar.py` (messages et documents). Un test (`test_langue.py`) echoue si un message d'erreur du code n'a pas de traduction.

## Demarrage rapide (developpement)

Prerequis : Python 3.12+, Node.js 20+. MySQL est facultatif en developpement (SQLite possible).

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate          # Windows : venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                      # UTILISER_SQLITE=1 pour essayer sans MySQL
python manage.py migrate
python manage.py charger_demo --mot-de-passe "UnMotDePasseSolide-2026"   # facultatif : donnees d'exemple
python manage.py runserver

# Frontend (autre terminal)
cd frontend
npm install
cp .env.example .env.local                                # VITE_URL_API=http://localhost:8000/api
npm run dev
```

Sans `charger_demo`, creer l'administrateur : `python manage.py createsuperuser`
(ou voir `backend/README.md`). Avec `charger_demo`, les comptes `admin`, `directeur`, `scolarite`,
`pedagogie`, `comptable` et `prof1` sont crees avec le mot de passe fourni. **Ne jamais charger
les donnees de demonstration sur une base de production** (la commande refuse de s'executer sur une base non vide).

## Tests

```bash
cd backend
UTILISER_SQLITE=1 python manage.py test apps.tests        # 307 tests, ~3 min
cd ../frontend
npx tsc -b && npm run build
```

Les tests couvrent : calculs de notes/moyennes/rangs, presences et notifications, algorithme genetique
(determinisme, contraintes, cas infaisable), remuneration, droits par role (un test parcourt **toutes**
les vues et echoue si l'une n'a pas de controle de role), listes avancees, tableau de bord, donnees de demonstration.
Un parcours navigateur complet (Chrome piloté par Playwright : connexion, tableaux, presences, notes,
bulletins, glisser-deposer, remuneration, droits du professeur) a aussi ete execute sur la base de demonstration.

## Regles de gestion importantes

- **Moyenne d'une matiere** = somme(note / bareme × 20 × poids) / somme(poids) ; **moyenne generale** =
  somme(moyenne × coefficient de la classe) / somme(coefficients). Une note manquante n'est **jamais** convertie
  en zero silencieusement : une evaluation non saisie est exclue et signalee ; l'option `matiere_non_evaluee = zero`
  (page *Parametres*) reproduit le calcul des bulletins papier de l'ecole.
- Les classements utilisent la moyenne arrondie a 2 decimales ; la gestion des ex aequo est configurable.
- Les paiements (scolarite et salaires) sont **immuables** : une erreur se corrige par une ecriture d'annulation, jamais par modification.
- Les resultats valides verrouillent les notes ; la reouverture est reservee a la direction et journalisee.
- Toutes les modifications sensibles sont inscrites dans le journal d'audit.

## Points a confirmer / limites connues

- **Tarifs de classe** : interpretes comme un montant **mensuel** en UM.
- **WhatsApp** : deux modes (lien `wa.me` sans configuration, ou API officielle Meta). L'envoi automatique exige un compte
  WhatsApp Business et un modele approuve (voir `DEPLOIEMENT.md`) et n'a ete teste que contre un faux serveur.
- **Nom de l'etablissement** par defaut : « Ecoles Privees El Adala - Kiffa » (modifiable dans *Parametres*).
- **PDF** : les documents sont generes avec des polices latines ; le texte arabe n'est pas imprime.
- **MySQL** : les migrations et la suite de tests ont ete executees sur SQLite ; faire un premier `migrate` sur une
  base MySQL vide et verifier avant la mise en service.
- Le fichier `backend/.env` d'un poste de developpement doit contenir une `CLE_SECRETE` d'au moins 32 caracteres
  (sinon la bibliotheque JWT affiche un avertissement ; en production, la valeur est exigee).
