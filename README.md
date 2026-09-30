# Padstow Rotary — Online Sales & Donation Platform

Django frontend, data stored in Firebase Firestore (switched from SQLite
for scalability — see "Why Firestore" below).

## 1. Create a Firebase project (skip if you already have one)

1. Go to **console.firebase.google.com** → **Add project** → give it a
   name (e.g. `padstow-rotary`) → you can decline Google Analytics for
   this → **Create project**.
2. In the left sidebar: **Build → Firestore Database → Create database**.
   - Choose **Start in production mode** (default-deny rules — safer;
     see the Firestore rules note below).
   - Pick a location close to you (e.g. `australia-southeast1` for
     Sydney) — **this can't be changed later**, but for a uni project
     any region is fine.
3. **Get a service account key** (this is how your Django app
   authenticates as an admin to Firestore):
   - ⚙️ **Project settings → Service accounts** tab
   - **Generate new private key** → confirms → downloads a `.json` file
   - Rename it to `firebase-service-account.json` and put it in the
     **project root** (next to `manage.py`) — `.gitignore` already
     excludes this file, **never commit it**.
4. Note your **Project ID**, shown at the top of Project settings
   (looks like `padstow-rotary-a1b2c`, not the display name).

## 2. Configure the project

Either:
- Drop the key at `firebase-service-account.json` in the project root
  (matches the default in `config/settings.py`), **or**
- Set an environment variable pointing wherever you saved it:
  ```bash
  export FIREBASE_CREDENTIALS_PATH=/absolute/path/to/your-key.json
  ```

Either way, also set your project ID:
```bash
export FIREBASE_PROJECT_ID=padstow-rotary-a1b2c
```
(On Windows PowerShell: `$env:FIREBASE_PROJECT_ID = "padstow-rotary-a1b2c"`.
For VS Code, you can instead put both in a `.env` file and load it with
the Python extension's `envFile` setting, or just `export` them in the
integrated terminal before running `manage.py`.)

## 3. Run it in VS Code

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python manage.py seed_products   # writes 3 demo trees into Firestore
python manage.py runserver
```

Then open **http://127.0.0.1:8000/**. There's no `migrate` step —
there's no SQL database left to migrate (see below).

## What you can click through

- `/` — Home
- `/donate/` — Donate → writes a `transactions` doc to Firestore
- `/shop/` — Buy Christmas trees → reads `products` from Firestore
- `/payment/` — Placeholder payment form → creates the real transaction
- `/confirmation/?ref=...` — Digital receipt, read back from Firestore
- `/dashboard/login/` — Staff portal (any username/password works — see note below)
- `/dashboard/`, `/dashboard/transactions/`, `/dashboard/reports/` — reads real Firestore data

There is **no `/admin/`** any more — per your call, Django's built-in
admin has been dropped along with the SQL database it depended on. The
app's own dashboard is now the only management view.

## Why Firestore (and what changed)

Firestore is a managed, horizontally-scaling document database — it
scales by adding more distributed capacity rather than needing to
resize a single server, which is the usual reason a project outgrows
SQLite/Postgres on one box. Concretely, this swap changed:

| Before | Now |
|---|---|
| `donations/models.py` — Django ORM models | `donations/firestore_data.py` — Firestore reads/writes |
| SQLite (`db.sqlite3`), `migrate` | No SQL database at all |
| DB-backed sessions | Signed-cookie sessions (`SESSION_ENGINE`, no table needed) |
| `/admin/` (`django.contrib.admin`) | Dropped, per your requirement — dashboard views only |
| `Product.objects.filter(...)` etc. | `firestore_data.list_active_products()` etc. |

### Data layout

- **`products`** collection — one doc per tree, `active: true/false`.
- **`transactions`** collection — one doc per donation/order, **doc id
  is the reference** (e.g. `RCP-2026-A1B2C3D4`), so looking a receipt
  up by reference is a single direct document read, not a query — the
  cheap, scalable way to do it in Firestore. Order line items are
  embedded as an `items` array field on the same document (Firestore
  has no joins, so a small list like this is embedded rather than put
  in yet another collection).

### A genuine scaling caveat, so it doesn't bite you later

`get_summary_stats()` in `donations/firestore_data.py` currently reads
*every* transaction document and sums them in Python — fine at
club-fundraiser scale (dozens to low-thousands of rows), but it's the
one place that would need revisiting before real scale: replace it
with [Firestore aggregation queries](https://firebase.google.com/docs/firestore/query-data/aggregation-queries)
(`collection.count()`, `collection.sum('amount')`) or a counters
document updated by a Cloud Function on each write, so the dashboard
stops needing to read every row to show a total.

## Firestore security rules

"Production mode" (step 1 above) denies all client access by default,
which is what you want here — this Django app talks to Firestore only
through the **Admin SDK** using your service account key, which
bypasses security rules entirely (it's trusted server-side access).
Rules only matter if you later add a mobile/web app that talks to
Firestore *directly* — not the case here.

## Before this goes anywhere near production

- **`SECRET_KEY`** in `config/settings.py` is a placeholder — move it
  to an environment variable and use a real generated key.
- **`DEBUG = True`** and empty `ALLOWED_HOSTS` are fine for local dev
  only.
- **Payment form** (`payment.html`) does not process real cards. Replace
  it with a real gateway's hosted checkout (Stripe Checkout, PayPal,
  Square) — never collect raw card numbers on your own server.
- **Staff login** is still a toy session flag
  (`request.session["staff_user"]`), unrelated to the database swap.
  The natural next step, since you're already on Firebase, is
  [Firebase Authentication](https://firebase.google.com/docs/auth)
  rather than Django's own auth system — ask if you want that wired up.
- **Service account key**: keep `firebase-service-account.json` out of
  git (already in `.gitignore`) and out of any deployed container image
  — inject it as a secret at deploy time instead.

## Project layout

```
rotary_project/
├── manage.py
├── requirements.txt
├── firebase-service-account.json   ← you add this (gitignored)
├── config/
│   ├── settings.py                 ← no DATABASES, Firebase config
│   ├── urls.py                     ← no /admin/
│   ├── wsgi.py
│   └── asgi.py
└── donations/
    ├── firestore_client.py         ← Firebase Admin SDK connection
    ├── firestore_data.py           ← ALL Firestore reads/writes
    ├── models.py                   ← empty stub, points here instead
    ├── forms.py                     ← DonationForm, StaffLoginForm
    ├── views.py                     ← one view per page
    ├── urls.py                      ← named URLs the templates call via {% url %}
    ├── management/commands/seed_products.py
    ├── templates/donations/         ← all HTML templates
    └── static/donations/            ← style.css, donate.js, shop.js
```

## Design notes

- Colour palette matches padstowrotary.org.au's green-and-white look —
  change `--green` in `donations/static/donations/css/style.css` (top
  of the file) to retheme everything in one place.
- Large tap targets, high-contrast text, and short forms throughout,
  reflecting the accessibility goals in the project plan for older
  members and donors.
