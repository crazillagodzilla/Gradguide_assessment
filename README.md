# GradGuide — Education Loan Assessment Tool

A full-stack assessment tool for comparing study costs, funding gaps, financial profiles, collateral value, and relevant loan routes. The application uses React and Tailwind for the user interface, Django REST Framework for the API, and PostgreSQL for persistent storage.

## Features

- Study and course information entry
- Total study-cost and funding-gap calculations
- Income, assets, liabilities, and net-worth assessment
- Collateral-value and route selection
- Route-, co-applicant-employment-, and property-state-specific document checklist
- Document upload and readiness scorecard with missing-document tracking
- Lender filtering using the supplied assignment dataset
- Financial scenario comparison
- Assessment confidence and data-gap warnings
- Responsive interface for desktop and mobile screens

> The application is an assessment and decision-support tool. It does not guarantee loan approval or rejection.

## Technology stack

- React 19
- Vite
- Tailwind CSS 4
- Django 5.2
- Django REST Framework
- PostgreSQL 18
- pytest and pytest-django

## Project structure

```text
.
├── assessments/
│   ├── management/commands/
│   │   └── seed_lenders.py # Loads lender_data.json into PostgreSQL
│   ├── migrations/         # Database schema history
│   ├── admin.py            # Django admin registrations
│   ├── models.py           # Assessment, Document, and Lender models
│   ├── serializers.py      # REST API input/output validation
│   ├── services.py         # Financial calculations, lender matching, document checklist/score
│   ├── tests.py            # Backend service and API tests
│   └── views.py            # Assessment, document, and lender API endpoints
├── backend/
│   ├── asgi.py             # ASGI application entry point
│   ├── settings.py         # Django, PostgreSQL, REST, CORS, and environment settings
│   ├── urls.py             # Admin and REST router registration
│   └── wsgi.py             # WSGI application entry point
├── frontend/
│   ├── public/             # Static files served as-is
│   ├── src/
│   │   ├── assets/         # Images and app assets
│   │   ├── App.jsx         # Assessment form, results, and document readiness UI
│   │   ├── App.css         # Application component styles
│   │   ├── api.js          # Django API client
│   │   ├── index.css       # Global styles and Tailwind imports
│   │   └── main.jsx        # React application entry point
│   ├── eslint.config.js    # Frontend lint rules
│   ├── index.html          # Vite HTML entry point
│   ├── package.json        # Frontend scripts and dependencies
│   └── vite.config.js      # Vite, React, and Tailwind plugins
├── .env.example            # Environment variable template; copy to .env
├── .gitignore              # Local secrets, generated files, and optional Lender_db.md
├── lender_data.json        # Runtime lender records loaded by seed_lenders
├── manage.py               # Django management entry point
├── pytest.ini              # pytest configuration
└── README.md
```

## Local setup

### 1. Install the backend environment

```bash
cd "Education loan app"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install Django djangorestframework psycopg[binary] python-dotenv django-cors-headers pytest pytest-django Pillow
```

### 2. Create PostgreSQL database

The local PostgreSQL server must be available at `localhost:5432`.

```bash
createdb -h localhost -U postgres -O postgres gradguide
```

### 3. Configure environment variables

Copy `.env.example` to `.env` and update the values if required. Generate a new Django secret key with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

Then set it in `.env`:

```env
POSTGRES_DB=gradguide
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
DJANGO_SECRET_KEY=your-generated-secret-key
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

Keep the Django secret key private and do not commit `.env` or the generated key to Git.

### 4. Apply the database schema

```bash
python manage.py migrate
python manage.py seed_lenders
```

`lender_data.json` is required by `seed_lenders` and supplies the lender records stored in PostgreSQL. The dynamic document checklist is defined in `assessments/services.py`.

### 5. Run the backend

```bash
python manage.py runserver 0.0.0.0:8000
```

### 6. Run the frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the local Vite URL printed in the terminal, usually `http://localhost:5173`.

## Testing

Run the backend tests:

```bash
python -m pytest -q
```

Run the frontend checks:

```bash
cd frontend
npm run build
npm run lint
```

## Video Walkthrough

[Watch the GradGuide walkthrough](https://drive.google.com/file/d/1Xjm15cLwOuFRW358j4gO71t5bpVLHQ8t/view?usp=sharing)

## Original features

### 1. Financial scenario planner

Users can change the scholarship amount with a slider and immediately compare the new funding gap. This helps students understand how different contributions affect their final loan requirement.

### 2. Personalized lender requirement checklist

The application reports matching lenders and relevant document categories. It separates the requirement list from the loan decision so the user understands what preparation is still needed.

### 3. Assessment confidence and data-gap indicator

The result explicitly warns when information is missing and explains that a preliminary assessment is not a guarantee. This reduces overconfidence and makes the limits of the supplied lender dataset visible.

## Assignment notes

- The supplied bank and lender data is treated as an assignment reference dataset.
- Lender records are seeded from `lender_data.json`; document checklist rules are defined in the assessment service.
- Missing lender information is displayed as unavailable information rather than assumed eligibility.
- The application does not guarantee approval or rejection.

