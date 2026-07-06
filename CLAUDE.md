# China AI Import Assistant

## Description
SaaS d'aide à l'importation depuis la Chine avec IA.

## Stack
- Frontend : Next.js
- Backend : FastAPI
- Base de données : PostgreSQL
- IA : API LLM

## Règles
- Toujours expliquer les changements avant modification importante
- Garder une architecture propre
- Ne pas supprimer de fichiers sans confirmation
- Écrire du code production-ready
- Ajouter des commentaires seulement si nécessaires

## Commandes
Frontend:
npm run dev

Backend:
uvicorn main:app --reload

## Structure
frontend/ = interface
backend/ = API
database/ = modèles et migrations

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
