# Padstow Rotary — Online Sales & Donation Platform

Django + Firebase Firestore + Stripe Checkout, deployed on Render.

## Run locally
1. `python -m venv .venv` then activate it (PowerShell: `Set-ExecutionPolicy -Scope Process Bypass; .venv\Scripts\Activate.ps1`)
2. `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and fill it in (keep `DJANGO_DEBUG=1`). Keep `firebase-service-account.json` next to `manage.py`.
4. `python manage.py seed_products` (once) then `python manage.py runserver`
5. Optional, to test webhooks locally: install the Stripe CLI, run `stripe listen --forward-to localhost:8000/stripe/webhook/` and put the `whsec_...` it prints in `.env`.
   (Without it the site still works: the redirect back from Stripe records the payment.)

Tests: `python manage.py test donations`

## Deploy (Render)
1. Push to GitHub (never commit `.env` or the Firebase key — `.gitignore` covers both).
2. Render → New → Blueprint → pick the repo (uses `render.yaml`), or New Web Service with:
   build `pip install -r requirements.txt && python manage.py collectstatic --noinput`, start `gunicorn config.wsgi:application`.
3. Set environment variables (see `.env.example`): `FIREBASE_PROJECT_ID`, `FIREBASE_CREDENTIALS_JSON` (paste the whole key file), `STRIPE_SECRET_KEY`, `STAFF_USERNAME`, `STAFF_PASSWORD`, `BREVO_API_KEY`, `EMAIL_FROM_ADDRESS`. `DJANGO_SECRET_KEY` is generated for you. Leave `DJANGO_DEBUG` unset.
4. Stripe Dashboard → Developers → Webhooks → Add endpoint `https://<your-app>.onrender.com/stripe/webhook/`, event `checkout.session.completed`. Copy its signing secret into `STRIPE_WEBHOOK_SECRET` on Render and redeploy.
5. Brevo: create an account, verify a sender address, create an API key (Render's free tier blocks SMTP, so Brevo's HTTPS API is used).

## Going live with real money
Use the club's own activated Stripe account and swap in its `sk_live_...` key and a new webhook secret. Move off Render's free tier (it sleeps when idle).
