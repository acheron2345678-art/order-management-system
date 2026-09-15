# Prototype B — Nova Order Management

This folder is an **independent comparison prototype** added beside the existing Order Management project. The original project files are intentionally left intact. Run this prototype separately when you want to compare its UI/workflow with the current implementation.

## What is included

- FastAPI + SQLAlchemy backend with MySQL-compatible models.
- Users with `CUSTOMER`, `MERCHANT`, and `ADMIN` roles.
- Merchant profiles, stores, menu items, orders, and immutable order-item snapshots.
- `/api/v1/stores` and `/api/v1/stores/{id}/menu` catalog/search APIs.
- Server-authoritative order creation and price/tax calculation.
- Order state machine: `PENDING → CONFIRMED → PREPARING → OUT_FOR_DELIVERY → DELIVERED`, with cancellation rules.
- Customer order WebSocket: `/ws/orders/{order_id}`.
- Merchant store WebSocket: `/ws/merchants/{store_id}`.
- Storefront with category filters, search, localStorage cart, checkout modal, mobile drawer, and theme toggle.
- Live tracking page with WebSocket-driven status timeline.
- Merchant dashboard with live queue, one-click status actions, Chart.js revenue/status charts, and top-item analytics.
- Optional Next.js UI reference in `nextjs-ui/`.

> This is a production-shaped **prototype**, not a finished production deployment. Authentication/authorization, payment processing, Redis-backed WebSocket fan-out, migrations, background jobs, audit logging, observability, CSRF strategy, and deployment secrets should be added before public deployment.

## Directory layout

```text
prototype_v2/
├── app/
│   ├── core/config.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── main.py
│   ├── seed.py
│   ├── realtime/manager.py
│   ├── routes/
│   │   ├── stores.py
│   │   ├── orders.py
│   │   ├── dashboard.py
│   │   ├── websocket.py
│   │   └── pages.py
│   ├── services/
│   │   ├── order_service.py
│   │   └── analytics_service.py
│   ├── templates/
│   │   ├── store.html
│   │   ├── track.html
│   │   └── dashboard.html
│   └── static/
│       ├── css/
│       │   ├── store.css
│       │   ├── track.css
│       │   └── dashboard.css
│       └── js/
│           ├── store.js
│           ├── track.js
│           └── dashboard.js
├── nextjs-ui/
├── tests/
├── requirements.txt
└── .env.example
```

## Quick start (zero-config SQLite)

From `prototype_v2`:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8100
```

Open:

- Storefront: `http://127.0.0.1:8100/`
- Merchant dashboard: `http://127.0.0.1:8100/dashboard`
- API docs: `http://127.0.0.1:8100/docs`

The app auto-creates `prototype.db` and demo menu data on first run.

## MySQL mode

Create a database:

```sql
CREATE DATABASE order_management_prototype
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;
```

PowerShell:

```powershell
$env:PROTOTYPE_DATABASE_URL="mysql+pymysql://root:YOUR_PASSWORD@127.0.0.1:3306/order_management_prototype"
uvicorn app.main:app --reload --port 8100
```

You can also copy `.env.example` to `.env`, but environment variables must be loaded by your shell or deployment environment in this lightweight prototype.

## Workflow to test

1. Open the storefront and add several dishes.
2. Checkout; the backend re-reads menu prices and calculates subtotal, tax, and total.
3. You are redirected to `/track/{order_id}`.
4. In another tab open `/dashboard`.
5. Use `Accept → Start Preparing → Dispatch → Mark Delivered`.
6. Watch the tracking page advance without refreshing.
7. Revenue and status charts refresh through the merchant WebSocket.

## Main API

```text
GET   /api/v1/stores
GET   /api/v1/stores/{store_id}/menu?q=&category=
POST  /api/v1/orders
GET   /api/v1/orders/{order_id}
PATCH /api/v1/orders/{order_id}/status
GET   /api/v1/dashboard/orders?store_id=1
GET   /api/v1/dashboard/analytics?store_id=1
WS    /ws/orders/{order_id}
WS    /ws/merchants/{store_id}
```

## Comparing with the existing project

Keep the existing app running on its current port and run this prototype on `8100`. That lets you compare both versions side-by-side without replacing routes, templates, database tables, or CSS in the current project.
