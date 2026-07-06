-- ===========================================
-- China AI Import Assistant - Initialisation DB
-- ===========================================
-- Ce script est exécuté automatiquement au premier démarrage du
-- conteneur PostgreSQL (docker-entrypoint-initdb.d).
-- Les tables elles-mêmes sont créées par SQLAlchemy/Alembic depuis le backend.

-- Extension UUID (nécessaire pour les colonnes UUID des modèles)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Le reste du schéma est géré par Alembic (voir backend/alembic/).
-- Pour générer la première migration :
--   cd backend
--   alembic revision --autogenerate -m "initial schema"
--   alembic upgrade head
