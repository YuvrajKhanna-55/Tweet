# Tweet

Tweet is a learning project built to understand Django by implementing an
X-style social platform. It combines a Django REST API with 
a React/Vite client and demonstrates how Django components work together in a
real application.

## Preview

![Tweet App Interface](assets/screenshot.png)

## Project demonstrates:

### Django fundamentals

- **Project configuration**: `clone/settings.py` configures installed apps,
  middleware, templates, media files, CORS, REST Framework, and databases.
- **URL routing**: `clone/urls.py` mounts Django admin, authentication routes,
  the original template app, and the REST API. `tweet/api_urls.py` registers
  API routers and authentication endpoints.
- **Models and migrations**: `tweet/models.py` defines users' profiles,
  tweets, follows, likes, replies, reposts, bookmarks, notifications,
  conversations, messages, reactions, hashtags, and communities.
- **Views**: `tweet/views.py` contains the original template-based CRUD views;
  `tweet/api_views.py` contains REST API viewsets and API functions.
- **Forms**: `tweet/forms.py` demonstrates Django `ModelForm` and
  `UserCreationForm` usage for the original server-rendered flow.
- **Serializers**: `tweet/serializers.py` converts Django model data to API
  responses and validates registration, posts, profiles, messages, and media.
- **Authentication and permissions**: Django sessions, CSRF protection,
  `IsAuthenticatedOrReadOnly`, ownership checks, and protected social actions.
- **Admin**: `tweet/admin.py` registers the application's models for inspection
  through Django admin.
- **Testing**: `tweet/tests.py` covers registration, profiles, feeds, social
  actions, messages, communities, post replies, and ownership rules.

### Social functionality

- Public For You feed and authenticated Following feed
- Tweet creation, editing, deletion, replies, reposts, quote posts, likes,
  bookmarks, mentions, and hashtags
- Image, GIF, MP4, WebM, and MOV media attachments
- Profiles with avatar, display name, bio, location, and website
- Follow/unfollow and notifications
- Direct conversations, group conversations, media messages, and reactions
- Communities with search, creation, joining, and leaving
- React/Vite client with an X-style responsive interface

## Architecture

```text
Browser
  |
  | React + Vite (frontend/)
  | - UI, navigation, forms, feed interactions
  | - Vite proxies /api and /media to Django
  |
Django (clone/)
  |
  | URL routing (clone/urls.py, tweet/api_urls.py)
  | REST viewsets and API functions (tweet/api_views.py)
  | Serializers and validation (tweet/serializers.py)
  | Domain models (tweet/models.py)
  | SQLite for local development or PostgreSQL
```

## Directory guide

```text
django_project/
├── clone/                  # Django project directory
│   ├── settings.py         # Environment, database, REST, CORS, media
│   ├── urls.py             # Project-level routes
│   ├── asgi.py             # ASGI entry point
│   └── wsgi.py             # WSGI entry point
├── tweet/                  # Main Django application
│   ├── models.py           # Social domain models
│   ├── forms.py            # Django forms
│   ├── views.py            # Server-rendered views
│   ├── api_views.py        # REST API endpoints
│   ├── serializers.py      # REST serializers
│   ├── api_urls.py         # API router and endpoints
│   ├── urls.py             # Original template routes
│   ├── admin.py            # Admin registrations
│   ├── tests.py            # Automated tests
│   └── migrations/         # Database migrations
├── frontend/               # React + Vite client
│   ├── src/main.jsx        # Application components and UI behavior
│   ├── src/api.js          # Session/CSRF-aware API client
│   ├── src/styles.css      # Responsive dark interface
│   └── vite.config.js      # Dev server and Django proxy
├── templates/              # Original Django templates
├── media/                  # Local uploads; ignored by Git
├── manage.py               # Django management entry point
├── pyproject.toml          # Python project metadata and dependencies
├── requirements.txt        # pip-compatible dependency export
└── .env.example            # Environment variable reference
```

## Requirements

- Python 3.10 or newer
- Node.js and npm
- PostgreSQL 18 is supported
- SQLite is used automatically when PostgreSQL variables are not configured

## Local setup

From the repository root:

```powershell
cd clone
python -m venv .venv
.\.venv\Scripts\Activate.ps1
cd ..
python -m pip install -e .
cd clone
python manage.py migrate
python manage.py runserver
```

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173/`.

The frontend expects Django at `http://127.0.0.1:8000/`. Vite proxies API
requests and media requests during development.

## PostgreSQL configuration

Use `.env.example` as a reference and set the variables in your shell or
deployment environment. Django does not load `.env` files automatically.

Set `POSTGRES_DB` to enable PostgreSQL; otherwise the project uses local
SQLite:

```powershell
$env:POSTGRES_DB = "tweet"
$env:POSTGRES_USER = "postgres"
$env:POSTGRES_PASSWORD = "your-password"
$env:POSTGRES_HOST = "localhost"
$env:POSTGRES_PORT = "5432"
python manage.py migrate
```

## Verification

```powershell
cd clone
python manage.py check
python manage.py test
cd frontend
npm run build
```

## GitHub

The repository intentionally excludes:

- Uploaded media under `clone/media/`
- Local SQLite database
- Environment files and secrets
- Python caches and virtual environments
- `frontend/node_modules/`
- Frontend production output
- IDE and operating-system files

Only `.env.example` should be committed as configuration documentation.
Replace all development secrets and configure production values through the
deployment environment.
