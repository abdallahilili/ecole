# Gestion d'ecole privee - Frontend (Phases 1 a 8)

Application React/TypeScript/Tailwind consommant l'API Django du
backend : tableaux de bord par role, referentiels, etudiants et scolarite, presences et
notifications, notes et bulletins, emplois du temps (glisser-deposer), remuneration,
parametres et utilisateurs. Le menu et les routes dependent du role de l'utilisateur.

## Installation

```bash
npm install
cp .env.example .env.local   # ajuster VITE_URL_API si besoin
npm run dev
```

## Build de production

```bash
npm run build
npm run preview   # pour verifier le build localement
```

## Variables d'environnement

| Variable | Description |
|---|---|
| `VITE_URL_API` | URL de base de l'API backend (ex: `http://localhost:8000/api`) |

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
