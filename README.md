# Padstow Rotary — Online Sales & Donation Platform

A runnable Django project: prototype frontend (green/white, matching
padstowrotary.org.au) wired to real Django views, models and URLs.

## Run it in VS Code

1. **Open the folder** `rotary_project/` in VS Code (File → Open Folder).

2. **Create and activate a virtual environment** (VS Code will usually
   prompt you to select it as the interpreter — accept that prompt).

   macOS / Linux:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

   Windows:

   ```powershell
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up the database**

   ```bash
   python manage.py migrate
   python manage.py seed_products
   ```

5. **(Optional) create an admin user**, to use Django's built-in admin
   at `/admin/` — separate from the site's own staff dashboard:

   ```bash
   python manage.py createsuperuser
   ```

6. **Run the dev server**
   ```bash
   python manage.py runserver
   ```
   Then open **http://127.0.0.1:8000/** in your browser.

## What you can click through

- `/` — Home
- `/donate/` — Donate (posts to a real `DonationForm`)
- `/shop/` — Buy Christmas trees (posts real quantities per product)
- `/payment/` — Placeholder payment form → creates a real `Transaction` row
- `/confirmation/?ref=...` — Digital receipt, pulled from the database
- `/dashboard/login/` — Staff portal (any username/password works — see note below)
- `/dashboard/`, `/dashboard/transactions/`, `/dashboard/reports/` — Committee dashboard, reading real `Transaction` data
- `/admin/` — Django's built-in admin (needs the superuser from step 5)

## Project layout

```
rotary_project/
├── manage.py
├── requirements.txt
├── config/                    ← project settings, root urls.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
└── donations/                 ← the app — all the actual functionality
    ├── models.py              ← Product, Transaction, OrderItem
    ├── forms.py                ← DonationForm, StaffLoginForm
    ├── views.py                ← one view per page
    ├── urls.py                 ← named URLs the templates call via {% url %}
    ├── admin.py                ← registers models with /admin/
    ├── management/commands/seed_products.py
    ├── migrations/
    ├── templates/donations/    ← all HTML templates
    └── static/donations/       ← style.css, donate.js, shop.js
```

## Before this goes anywhere near production

These are flagged inline in the code (search for `TODO`) as well as here:

- **`SECRET_KEY`** in `config/settings.py` is a placeholder — move it to
  an environment variable and use a real generated key.
- **`DEBUG = True`** and empty `ALLOWED_HOSTS` are fine for local dev
  only. Set `DEBUG = False` and configure `ALLOWED_HOSTS` before deploying.
- **Payment form** (`payment.html`) does not process real cards. Replace
  it with a real gateway's hosted checkout (Stripe Checkout, PayPal,
  Square) — never collect raw card numbers on your own server.
- **Staff login** is a toy session flag (`request.session["staff_user"]`),
  not real authentication. Swap it for Django's built-in
  `django.contrib.auth` (`LoginView`, `@login_required`) so passwords are
  hashed and access is properly protected — the built-in `/admin/` already
  shows the pattern to follow.
- **SQLite** (`db.sqlite3`) is fine for development; move to Postgres (or
  similar) for anything beyond a local demo.

## Design notes

- Colour palette matches padstowrotary.org.au's green-and-white look —
  change `--green` in `donations/static/donations/css/style.css` (top of
  the file) to retheme everything in one place.
- Large tap targets, high-contrast text, and short forms throughout,
  reflecting the accessibility goals in the project plan for older
  members and donors.
