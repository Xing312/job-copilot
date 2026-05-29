DC = docker compose

.PHONY: start stop restart logs train

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
