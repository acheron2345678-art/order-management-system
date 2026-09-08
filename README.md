# Order Management

FastAPI + MySQL order management application for Swiggy and Insights orders.

## Stack

- FastAPI
- SQLAlchemy + MySQL (PyMySQL)
- Jinja2 server-side templates
- Bootstrap 5.3.8
- DataTables 2.3.8 with Bootstrap 5 integration
- D3.js 7.9.0

Frontend libraries are loaded by CDN from `templates/base.html`, so they do not need `pip install`.

## Install

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```powershell
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

## Backend structure

```text
app/
├── core/
│   ├── config.py
│   └── templates.py
├── database/
│   ├── base.py
│   └── connection.py
├── orders/
│   ├── dependencies.py
│   ├── models.py
│   ├── repository.py
│   ├── router.py
│   ├── schemas.py
│   └── service.py
├── dashboard/
│   ├── repository.py
│   ├── router.py
│   ├── schemas.py
│   └── service.py
├── search/
│   ├── repository.py
│   ├── router.py
│   ├── schemas.py
│   └── service.py
└── main.py
```

### Layer responsibilities

- `router.py`: HTTP routes, forms, responses, dependency injection
- `service.py`: business logic and validation
- `repository.py`: SQLAlchemy database queries and persistence
- `schemas.py`: Pydantic request/response structures
- `models.py`: SQLAlchemy database models
- `dependencies.py`: feature-specific dependencies such as platform resolution

## Frontend structure

```text
templates/
├── dashboard/
├── orders/
├── partials/
├── search/
├── base.html
└── home.html

static/
├── css/
│   └── style.css
└── js/
    ├── dashboard.js
    ├── datatables.js
    ├── search.js
    └── theme.js
```

Bootstrap handles layout/components and light/dark color mode. DataTables v2 handles order-table searching, sorting, pagination, and page length. D3.js handles dashboard visualizations.

## DataTables v2 sorting and pagination fix

The orders table uses DataTables 2.3.8 with Bootstrap 5 styling. DataTables v2's browser build requires jQuery, so jQuery 3.7.1 is loaded before the DataTables scripts in `templates/base.html`. Sorting, page-length selection, search, info, and pagination are initialized in `static/js/datatables.js`.
