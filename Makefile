DC = docker compose

.PHONY: start stop restart logs train test migrate migration stamp

start:
	$(DC) up -d

stop:
	$(DC) down

restart:
	$(DC) restart backend

logs:
	$(DC) logs -f backend

train:
	$(DC) exec backend python /app/corpus/train.py

test:
	$(DC) exec backend sh -c "pip install -q pytest httpx && pytest tests/ -v"

# Apply all pending migrations
migrate:
	$(DC) exec backend alembic upgrade head

# Generate a new migration: make migration name="add notes column"
migration:
	$(DC) exec backend alembic revision --autogenerate -m "$(name)"

# One-time: mark existing DB as current (use when first introducing Alembic to a live DB)
stamp:
	$(DC) exec backend alembic stamp head
