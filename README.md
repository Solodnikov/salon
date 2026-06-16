# salon
приложение для записи к парикмахеру

## Запуск

```bash
cp .env.example .env
docker compose up --build
```

Приложение будет доступно на `http://localhost:8000/`, админка на `http://localhost:8000/admin/`.

Для создания администратора:

```bash
docker compose run --rm web python manage.py createsuperuser
```

После входа в админку нужно создать парикмахера, привязать его к staff-пользователю, назначить услуги и рабочие дни. Стартовые услуги создаются автоматически командой `seed_services` при запуске контейнера `web`.

## Локальная проверка без Docker

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_services
.venv/bin/python manage.py runserver
```
