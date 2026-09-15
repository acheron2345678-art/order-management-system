# Prototype B UI Merge

This build keeps the original Order Management application as the functional source of truth and layers the Prototype B visual system on top of it.

## What remains unchanged

- Existing FastAPI routes and application startup
- MySQL / SQLAlchemy models and services
- Authentication, sessions, roles and authorization
- Admin, client and merchant workflows
- Swiggy restaurant, menu, cart, checkout and order flows
- One-restaurant-per-cart behavior
- Insights services, checkout and project flows
- Product and inventory management
- User and merchant administration
- Existing dashboard data and D3 interactions
- Existing DataTables behavior
- Notification/email code
- Existing validation and security work

## UI layer added

- `static/css/prototype-merge.css`
  - Warm neutral canvas and orange accent inspired by Prototype B
  - Unified light/dark theme tokens
  - Compact rounded navigation and controls
  - Softer cards, borders and operational dashboard surfaces
  - Prototype-style metric cards and chart containers
  - Compact Swiggy menu grid for desktop/tablet/mobile
  - Consistent forms, tables, dropdowns, dialogs and status badges
  - Responsive polish and reduced-motion support

- `static/js/prototype-merge.js`
  - Staggered card/page reveal animations
  - Button press micro-interactions
  - Cart/notification badge pop animation
  - Theme toggle animation
  - Live-status pulse cues
  - Lightweight form loading shimmer
  - Uses progressive enhancement only; existing page logic remains authoritative

## Templates linked to the new layer

- `templates/base.html`
- `templates/swiggy/base.html`
- `templates/insights/base.html`
- `templates/merchant/base.html`
- `templates/auth/login.html`
- `templates/auth/client_register.html`
- `templates/auth/merchant_register.html`
- `templates/auth/session_refresh.html`

## Prototype B reference

The original standalone prototype is still available under `prototype_v2/` for side-by-side comparison. It has not replaced the production application code.
