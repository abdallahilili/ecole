# Gestion d'ecole privee - Frontend (Phases 1 a 8)

Application React/TypeScript/Tailwind consommant l'API Django du
backend : tableaux de bord par role, referentiels, etudiants et scolarite, presences et
notifications, notes et bulletins, emplois du temps (glisser-deposer), remuneration,
parametres et utilisateurs. Le menu et les routes dependent du role de l'utilisateur.

## Installation

```bash
npm install
cp .env.example .env.local   # facultatif : sans VITE_URL_API, /api est relaye vers le backend (port 8000)
npm run dev -- --host        # --host : accessible aussi depuis le reseau local / Tailscale
```

## Build de production

```bash
npm run build
npm run preview   # pour verifier le build localement
```

## Variables d'environnement

| Variable | Description |
|---|---|
| `VITE_URL_API` | URL de base de l'API backend (ex: `https://ecole.exemple.mr/api`). Facultative : par defaut `/api`, relaye par Vite vers `127.0.0.1:8000` en developpement |

## Structure

- `src/composants/` : composants generiques reutilisables (tableau,
  formulaire CRUD generique `PageCrud`, modales, notifications).
- `src/pages/` : une page par module (referentiels, etudiants,
  professeurs, scolarite, utilisateurs).
- `src/hooks/useListe.ts` : hooks generiques de liste paginee/recherche
  et de chargement d'options pour les listes deroulantes.
- `src/services/` : client API (jeton JWT + rafraichissement
  automatique) et service d'authentification.

## Comptes

Connectez-vous avec un compte cree cote backend (voir le README du
backend, section "Creer le premier utilisateur administrateur").
