# Deploiement en production

Ce guide installe l'application sur un serveur (Windows ou Linux) avec MySQL/MariaDB.
Le backend (Django) est servi par **waitress**, les fichiers statiques par **whitenoise**,
le frontend (fichiers compiles) et le HTTPS par un serveur web frontal (nginx, Apache, IIS ou Caddy).

## 1. Prerequis

- Python 3.12+ (teste avec 3.14), MySQL 8 / MariaDB 10.6+, Node.js 20+ (uniquement pour compiler le frontend).
- Un nom de domaine et un certificat HTTPS (Let's Encrypt ou autre).

## 2. Base de donnees

```sql
CREATE DATABASE ecole CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'ecole'@'localhost' IDENTIFIED BY 'mot-de-passe-solide';
GRANT ALL PRIVILEGES ON ecole.* TO 'ecole'@'localhost';
```

## 3. Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate          # Windows : venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                      # puis editer (voir ci-dessous)
python manage.py migrate
python manage.py createsuperuser                          # ou creer l'administrateur via le shell (README)
python manage.py collectstatic --noinput
python manage.py check --deploy
waitress-serve --listen=127.0.0.1:8000 config.wsgi:application
```

Valeurs minimales du fichier `.env` en production :

```
DEBUG=0
CLE_SECRETE=<au moins 32 caracteres aleatoires>
HOTES_AUTORISES=ecole.exemple.mr
FORCER_HTTPS=1
UTILISER_SQLITE=0
BD_NOM=ecole
BD_UTILISATEUR=ecole
BD_MOT_DE_PASSE=<mot de passe>
ORIGINES_CORS=https://ecole.exemple.mr
```

Avec `DEBUG=0`, l'application **refuse de demarrer** si `CLE_SECRETE` est absente ou trop courte.
La liste complete des variables est dans `backend/.env.example`.

### Lancer waitress comme service

- **Linux** : unite systemd (`ExecStart=.../venv/bin/waitress-serve --listen=127.0.0.1:8000 config.wsgi:application`, `Restart=always`).
- **Windows** : NSSM (`nssm install ElAdalApi`) ou le Planificateur de taches (« Au demarrage », « Executer meme si l'utilisateur n'est pas connecte »).

## 4. Frontend

```bash
cd frontend
npm ci
VITE_URL_API=https://ecole.exemple.mr/api npm run build      # PowerShell : $env:VITE_URL_API="..."; npm run build
```

Publier le contenu de `frontend/dist/` comme site statique. `VITE_URL_API` est integree
a la compilation : recompiler si l'adresse de l'API change.

## 5. Serveur web frontal (exemple nginx)

```nginx
server {
    listen 443 ssl http2;
    server_name ecole.exemple.mr;
    # ssl_certificate / ssl_certificate_key ...

    root /var/www/ecole/dist;                 # contenu de frontend/dist
    index index.html;

    location / { try_files $uri /index.html; }   # application monopage : toute route -> index.html

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $remote_addr;
        client_max_body_size 10m;             # imports Excel (5 Mo max cote application)
    }
    location /static/ { alias /chemin/backend/staticfiles/; }   # facultatif (whitenoise les sert deja)
    location /media/  { alias /chemin/backend/media/; }         # photos des etudiants et professeurs
}
server { listen 80; server_name ecole.exemple.mr; return 301 https://$host$request_uri; }
```

L'en-tete `X-Forwarded-Proto` est necessaire quand `FORCER_HTTPS=1`.

## 6. Sauvegardes

- Base : `mysqldump --single-transaction ecole | gzip > ecole-$(date +%F).sql.gz` chaque nuit (cron / Planificateur de taches).
- Photos : sauvegarder le dossier `backend/media/`.
- Conserver les sauvegardes hors du serveur et **tester une restauration** avant d'en avoir besoin.

## 7. Mises a jour

1. Sauvegarder la base.
2. Recuperer le nouveau code, `pip install -r requirements.txt`.
3. `python manage.py migrate` (les migrations n'effacent aucune donnee), `collectstatic`.
4. Recompiler le frontend si besoin, redemarrer waitress.

## 8. Notifications WhatsApp d'absence

Deux modes coexistent ; l'application choisit automatiquement.

### Mode 1 – lien `wa.me` (aucune configuration)
Si les variables `WHATSAPP_*` sont vides, chaque absence cree une notification avec un lien
`wa.me` pre-rempli : le personnel clique, WhatsApp s'ouvre avec le message pret, il appuie sur « Envoyer ».
Rien n'est envoye sans action humaine, et l'etat reste « en attente » tant que l'envoi n'est pas confirme.

La langue du message est choisie dans *Parametres* → « Langue des messages WhatsApp » (francais ou arabe) : c'est la langue des
**parents**, independante de la langue d'affichage de l'application. En arabe, le message utilise le texte arabe ci-dessous.

### Mode 2 – envoi automatique (WhatsApp Business Platform de Meta) — **necessite une configuration externe**
Prerequis a obtenir aupres de Meta (hors de ce projet, delai de validation possible) :

1. Un compte Meta Business verifie et une application avec le produit « WhatsApp ».
2. Un numero d'envoi : son identifiant → `WHATSAPP_ID_NUMERO`; un jeton d'acces permanent → `WHATSAPP_JETON`.
3. Un **modele de message** approuve (categorie « Utilitaire », langue `fr`) dont le corps contient
   exactement 7 variables, dans cet ordre :

   ```
   Bonjour, nous vous informons que votre enfant {{1}}, inscrit en classe de {{2}}, a ete absent au cours de
   {{3}} le {{4}}, de {{5}} a {{6}}. Merci de prendre contact avec l'administration si necessaire. {{7}}.
   ```
   {{1}} nom de l'eleve, {{2}} classe, {{3}} matiere, {{4}} date, {{5}} heure de debut, {{6}} heure de fin, {{7}} etablissement.
   Renseigner son nom dans `WHATSAPP_MODELE`.
   Pour des messages en arabe, faire approuver un second modele (langue `ar`) avec les **memes 7 variables dans le meme ordre** :

   ```
   مرحبًا، نُعلمكم بأن ابنكم {{1}}، المسجّل في القسم {{2}}، قد تغيّب عن حصة {{3}} يوم {{4}}، من {{5}} إلى {{6}}.
   يرجى الاتصال بالإدارة عند الحاجة. {{7}}.
   ```
   puis renseigner `WHATSAPP_MODELE_AR` (et `WHATSAPP_LANGUE_AR`, `ar` par defaut).
4. Webhook (statuts « livre » / « echec ») : URL `https://ecole.exemple.mr/api/presences/whatsapp/webhook/`,
   jeton de verification = `WHATSAPP_JETON_VERIFICATION`, secret de l'application = `WHATSAPP_SECRET_APPLICATION`
   (les requetes dont la signature HMAC est invalide sont rejetees).
5. Planifier le traitement de la file d'envoi (toutes les minutes) :

   ```bash
   python manage.py traiter_notifications_whatsapp               # un passage (cron / Planificateur)
   python manage.py traiter_notifications_whatsapp --boucle      # processus continu (service)
   ```

Un message passe a « envoye » seulement quand l'API l'accepte, a « livre » seulement sur confirmation
du webhook. Les echecs temporaires sont retentes avec delai croissant (`WHATSAPP_MAX_TENTATIVES`),
les echecs definitifs sont visibles et rejouables dans la page *Notifications*.
Le mode 2 n'a pu etre teste qu'avec un faux serveur : **faire un essai reel avec un numero de test Meta avant la mise en service.**

## 9. Liste de verification avant ouverture

- [ ] `python manage.py check --deploy` sans avertissement bloquant
- [ ] `DEBUG=0`, cle secrete forte, HTTPS actif (`FORCER_HTTPS=1`)
- [ ] Compte administrateur cree, mot de passe fort ; comptes de demonstration **absents**
- [ ] Parametres de l'ecole renseignes (page *Parametres*) : nom, entete des documents, regles de calcul
- [ ] Sauvegarde automatique configuree et restauration testee
- [ ] Planification `traiter_notifications_whatsapp` active (mode 2 uniquement)
