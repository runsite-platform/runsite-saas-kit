# Runsite SaaS Kit

A free, open-source (MIT) SaaS starter built with FastAPI and React. Auth, organizations and teams, subscriptions
with Stripe, Lemon Squeezy or Creem, a dashboard, file uploads, a platform admin panel and an example module are
already built, so you can spend your time on the part your customers pay for.

[![Deploy on Runsite](https://img.shields.io/badge/Deploy%20on-Runsite-0f172a?style=for-the-badge)](https://dashboard.runsite.app/templates/ff27d3cf-54c2-4ce3-9359-07be4bc08725)

Deploying from the [Runsite template](https://dashboard.runsite.app/templates/ff27d3cf-54c2-4ce3-9359-07be4bc08725) creates the
web service, a PostgreSQL database, an object storage bucket and an email service, and wires every environment
variable. You get a working app (register, log in, create a project, invite a member, upload and delete files)
without touching any configuration.

- Runsite: https://runsite.app
- Dashboard: https://dashboard.runsite.app
- Docs: https://docs.runsite.app
- Template gallery: https://dashboard.runsite.app/templates

## What's inside

- **Authentication:** email and password, Google login, email verification, password reset, short-lived access
  tokens and rotating refresh tokens with reuse detection, rate limiting on auth endpoints.
- **Organizations and teams:** a personal workspace on sign-up, more organizations on demand, owner / admin /
  member roles, invitations by email or copyable link, ownership transfer, organization switcher.
- **Billing:** Free and Pro plans defined in code, limits (members, projects, storage) and feature gating, trials,
  checkout, customer portal, cancel at period end, payment history, upgrade prompts at plan limits and Pro features. One
  provider per deployment: Stripe, Lemon Squeezy or Creem, chosen by an environment variable.
- **Dashboard:** stat cards (projects, members, storage used against the plan limit) and charts (projects created
  per day) on the Pro plan.
- **Files:** uploads to S3-compatible storage (25 MB per file) with per-plan storage limits, presigned downloads,
  avatars and organization logos.
- **Platform admin:** users and organizations, block / unblock, manual plan overrides, MRR and trial metrics,
  impersonation, a setup checklist that shows which integrations are configured.
- **Example module:** `projects`, a complete CRUD feature across every layer, to copy for your own modules.
- **Frontend:** React 19, TypeScript, Tailwind CSS v4, shadcn/ui, light and dark themes, every string in i18n
  files, a placeholder landing page with pricing and FAQ.
- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0 async, Alembic, Pydantic v2, pytest.

## Deploy on Runsite

1. Click **Deploy on Runsite** above (or open the template from the
   [template gallery](https://dashboard.runsite.app/templates)) and sign in.
2. Pick a project name and repository name, then click **Deploy**. Runsite copies this repository into your
   GitHub account, creates the services and starts the first build.
3. When the build finishes, open the web service URL and register. To make yourself the platform admin, see
   [First superadmin](#first-superadmin).

What the template sets for you:

| Variable | Value |
|---|---|
| `DATABASE_URL` | Internal URL of the new PostgreSQL database |
| `JWT_SECRET` | 64 random characters |
| `APP_URL` | Public URL of the web service |
| `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_ENDPOINT_URL`, `S3_BUCKET`, `S3_REGION` | The new bucket and its key (the key can read, write and delete) |
| `EMAIL_API_KEY` | Key of the new email service (starts in sandbox mode) |
| `EMAIL_FROM` | `My SaaS <noreply@example.com>`, change it after verifying your domain |
| `BRAND_NAME` | `My SaaS`, change it to your product name |

Everything else (billing, Google login, email verification, superadmin) is switched on later by adding
environment variables in the [Runsite dashboard](https://dashboard.runsite.app): web service → **Environment**.
Saving redeploys the service.

## Local development

Requirements: Docker, Python 3.12 with [uv](https://docs.astral.sh/uv/), Node.js 22.

```bash
make run
```

`make run` creates `.env` from `.env.example` if it is missing, starts the containers, installs dependencies on the
first run, applies migrations and starts the backend and the frontend together (Ctrl+C stops both). Open
http://localhost:5173.

To run the steps by hand: `make db-up`, `make install`, `make migrate`, then `make dev-backend` and, in a second
terminal, `make dev-frontend`. The Vite dev server proxies `/api` to the backend on port 8000.

`make db-up` starts PostgreSQL (port 5432, user, password and database `saaskit`, plus `saaskit_test` for tests),
Mailpit (http://localhost:8025) and MinIO (S3 API on port 9000, console on http://localhost:9001, user `saaskit`,
password `saaskit-secret`, bucket `saaskit`). `.env.example` already points the S3 variables at MinIO. The app
sends email through the Runsite Email API only; without `EMAIL_API_KEY` (and with `DEBUG=true`, the
`.env.example` default) emails are written to the backend log, so you can copy verification and reset links from
there.

Ports already taken? Set them in `.env` (the app ignores these; docker compose and the Makefile read them):

| Variable | Default | Used by |
|---|---|---|
| `POSTGRES_PORT` | `5432` | Host port of PostgreSQL. Change the port in `DATABASE_URL` too. |
| `MAILPIT_SMTP_PORT`, `MAILPIT_UI_PORT` | `1025`, `8025` | Host ports of Mailpit. |
| `MINIO_API_PORT`, `MINIO_CONSOLE_PORT` | `9000`, `9001` | Host ports of MinIO. Change `S3_ENDPOINT_URL` too. |
| `BACKEND_PORT` | `8000` | `make dev-backend`; `make dev-frontend` points the Vite proxy at it. |
| `VITE_API_PROXY_TARGET` | `http://localhost:8000` | Vite proxy target when you run `npm run dev` directly (shell variable). |
| `TEST_DATABASE_URL` | derived from `POSTGRES_PORT` | Test database. The Makefile sets it; export it yourself for direct `pytest` runs. |

Other targets: `make test` runs all tests, `make check` runs lint, the type check and all tests, `make lint`
runs ruff, ESLint and the format check, `make makemigration name="..."` autogenerates an Alembic revision, `make db-down` stops the
containers, `make docker-build` builds the production image.

Production image: `make docker-build` (or `docker build .`) builds the frontend and the backend into one image
that serves the API and the SPA on `$PORT` (default 8080). On start, `deploy/entrypoint.sh` waits for PostgreSQL
(`DB_WAIT_TIMEOUT`, default 180s), runs `alembic upgrade head` (retried `MIGRATION_ATTEMPTS` times, default 3; skip
with `RUN_MIGRATIONS=false`) and starts uvicorn with `UVICORN_WORKERS` workers (default 1).

Demo data: `cd backend && uv run python -m app.cli seed-demo` creates `demo@example.com` /
`demo-password-123` with an organization and a few projects (safe to run twice).

## Configuration

Settings are read from environment variables (and `.env` locally) by `backend/app/config/settings.py`. Missing
required variables stop the app with one message that names all of them. Every optional variable switches on one
feature; nothing needs a code change.

| Variable | Default | Enables / purpose |
|---|---|---|
| `DATABASE_URL` | required | PostgreSQL connection. `postgres://` and `postgresql://` are rewritten to `postgresql+asyncpg://`. |
| `JWT_SECRET` | required | Signs access tokens. Use 64+ random characters. |
| `APP_URL` | required | Public URL for email links, OAuth redirects and billing return URLs. `https://` turns on secure cookies. |
| `DEBUG` | `false` | Verbose logs; logs email text when email is not configured. |
| `BRAND_NAME` | `Acme` | Product name in emails and the UI (returned by `/api/config/public`). |
| `FRONTEND_DIST_DIR` | `<project>/frontend/dist` | Where the built SPA is served from. |
| `TRUSTED_PROXY_HOPS` | `1` | Proxies that append to `X-Forwarded-For`; the auth rate limit takes the client IP from that hop. `0` ignores the header. |
| `EMAIL_API_KEY` | empty | Sending email through the Runsite Email API. Empty: emails are logged. |
| `EMAIL_API_URL` | `https://api.runsite.app/emails` | Email API endpoint. |
| `EMAIL_FROM` | `Acme <noreply@example.com>` | Sender address. |
| `EMAIL_REPLY_TO` | empty | Reply-To address for every email, e.g. a support inbox. |
| `REQUIRE_EMAIL_VERIFICATION` | `false` | Requires a verified email to invite members and start checkout; shows a "verify your email" banner. |
| `S3_ACCESS_KEY_ID` | empty | File storage (with the next three). Also deletes objects unless `S3_DELETE_*` is set. |
| `S3_SECRET_ACCESS_KEY` | empty | File storage. |
| `S3_ENDPOINT_URL` | empty | File storage, e.g. `https://s3.runsite.app`. |
| `S3_BUCKET` | empty | File storage. Empty: the Files page and uploads are hidden. |
| `S3_REGION` | `auto` | S3 region. |
| `S3_DELETE_ACCESS_KEY_ID` | empty | Optional separate key for deleting objects (with the secret below). Empty: the main key deletes. |
| `S3_DELETE_SECRET_ACCESS_KEY` | empty | Secret of the optional delete key. |
| `GOOGLE_CLIENT_ID` | empty | "Continue with Google" (with the secret). |
| `GOOGLE_CLIENT_SECRET` | empty | "Continue with Google". |
| `BILLING_PROVIDER` | empty | Billing: `stripe`, `lemonsqueezy` or `creem`. Empty: everyone stays on Free. |
| `STRIPE_SECRET_KEY` | empty | Stripe API calls. |
| `STRIPE_WEBHOOK_SECRET` | empty | Stripe webhook signature check. |
| `STRIPE_PRICE_PRO_MONTHLY` | empty | Stripe price for Pro monthly. |
| `STRIPE_PRICE_PRO_YEARLY` | empty | Stripe price for Pro yearly. |
| `LEMONSQUEEZY_API_KEY` | empty | Lemon Squeezy API calls. |
| `LEMONSQUEEZY_STORE_ID` | empty | Lemon Squeezy store for checkouts. |
| `LEMONSQUEEZY_WEBHOOK_SECRET` | empty | Lemon Squeezy webhook signature check. |
| `LEMONSQUEEZY_VARIANT_PRO_MONTHLY` | empty | Lemon Squeezy variant for Pro monthly. |
| `LEMONSQUEEZY_VARIANT_PRO_YEARLY` | empty | Lemon Squeezy variant for Pro yearly. |
| `CREEM_API_KEY` | empty | Creem API calls. |
| `CREEM_API_URL` | `https://api.creem.io` | Creem API; use `https://test-api.creem.io` in test mode. |
| `CREEM_WEBHOOK_SECRET` | empty | Creem webhook signature check. |
| `CREEM_PRODUCT_PRO_MONTHLY` | empty | Creem product for Pro monthly. |
| `CREEM_PRODUCT_PRO_YEARLY` | empty | Creem product for Pro yearly. |
| `SUPERADMIN_EMAIL` | empty | Makes this email a superadmin on registration and at startup. |

`.env.example` lists the same variables with comments, plus the local-development variables above. A paid plan
without a price or product ID for the active provider is shown as not available.

## Email

A new Runsite email service starts in **sandbox mode**: it only delivers to recipients you verified in the
service, and it rewrites `From` to the shared Runsite sandbox sender (your `EMAIL_FROM` becomes `Reply-To`).
In sandbox mode `EMAIL_REPLY_TO` may be overridden the same way.
See [Sandbox mode](https://docs.runsite.app/services/email/sandbox/).

That is why `REQUIRE_EMAIL_VERIFICATION` is `false` by default: new users are marked verified at registration and no
verification email is sent, so sign-up works for everyone from the first minute. Invitations still work in
sandbox: after you create an invitation, the Members page shows its link once with a **Copy** button. Email
failures are logged and never fail a request.

To go to production:

1. In the [Runsite dashboard](https://dashboard.runsite.app) open the email service and add your sending domain
   ([Domains](https://docs.runsite.app/services/email/domains/)). Add the DNS records it shows and wait until the
   domain is verified; the service then leaves sandbox mode.
2. Set `EMAIL_FROM` to an address on that domain, for example `My SaaS <hello@mysaas.com>`.
3. Set `REQUIRE_EMAIL_VERIFICATION=true`. Unverified users can still log in, but they must verify their email
   before inviting members or starting a checkout.

The admin **Setup** page shows whether email and a verified sender domain are configured.

## File storage

Files, avatars and logos go to the bucket in `S3_BUCKET`. Downloads use presigned URLs valid for 15 minutes.

Deleting a file also deletes the stored object. The kit deletes with the main key (`S3_ACCESS_KEY_ID` /
`S3_SECRET_ACCESS_KEY`), or with `S3_DELETE_ACCESS_KEY_ID` / `S3_DELETE_SECRET_ACCESS_KEY` when both are set. If
the key is refused, the file record is still deleted, the object stays in the bucket and a warning is logged.

- **Template deploys and local MinIO:** nothing to do. The key the template creates can read, write and delete.
- **Bucket attached through a dashboard connection:** the credentials a connection injects are read & write only,
  so deletes are refused. Only in this case set `S3_DELETE_ACCESS_KEY_ID` / `S3_DELETE_SECRET_ACCESS_KEY` to a
  delete-capable key, created in one of two ways:
  - [Dashboard](https://dashboard.runsite.app): **Storage** → **Create API Key**, enable `read`, `write` and
    `delete` (leave `admin` off). This is a workspace-wide key, so keep it only in this app's environment.
  - Public API, scoped to one bucket (needs a Runsite API key with the `write` scope; the bucket `id` comes from
    `GET /api/v1/storage/buckets/{name}`):

    ```bash
    curl -X POST https://api.runsite.app/api/v1/storage/keys \
      -H "Authorization: Bearer $RUNSITE_API_KEY" \
      -H "Content-Type: application/json" \
      -d '{"name": "saas-kit delete", "bucket_id": "BUCKET_ID", "permissions": {"read": true, "write": true, "delete": true}}'
    ```

  Put the returned `access_key` and `secret_key` into `S3_DELETE_ACCESS_KEY_ID` and
  `S3_DELETE_SECRET_ACCESS_KEY`. See [Access keys](https://docs.runsite.app/services/object-storage/access-keys/).

## Billing

Pick one provider, set `BILLING_PROVIDER` and its variables, and register the webhook URL
`{APP_URL}/api/webhooks/billing/{provider}` in the provider's dashboard. Webhooks are verified by signature and
processed idempotently; a failed event returns an error so the provider retries it. Without `BILLING_PROVIDER`,
billing pages explain how to enable it and everyone stays on Free.

Plans, prices, limits and trial length live in `backend/app/services/billing/plans.py`. Prices there are used for
display and MRR; the amount charged comes from the provider's price, variant or product.

### Stripe

1. Create a product "Pro" with two recurring prices (monthly and yearly).
2. Developers → Webhooks → add endpoint `{APP_URL}/api/webhooks/billing/stripe`.
   Events to send: `customer.subscription.created`, `customer.subscription.updated`,
   `customer.subscription.deleted`, `invoice.paid`, `invoice.payment_failed`.
3. Turn on the customer portal (Settings → Billing → Customer portal).
4. Set:

```dotenv
BILLING_PROVIDER=stripe
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_PRO_MONTHLY=price_...
STRIPE_PRICE_PRO_YEARLY=price_...
```

Trials: the kit passes the plan's `trial_days` (14 for Pro) to Stripe Checkout as `trial_period_days`; nothing to
configure.

### Lemon Squeezy

1. Create a subscription product "Pro" with a monthly and a yearly variant.
2. Settings → Webhooks → add `{APP_URL}/api/webhooks/billing/lemonsqueezy` with a signing secret.
   Events to send: `subscription_created`, `subscription_updated`, `subscription_cancelled`,
   `subscription_resumed`, `subscription_expired`, `subscription_paused`, `subscription_unpaused`,
   `subscription_payment_success`, `subscription_payment_failed`, `subscription_payment_recovered`.
3. Set:

```dotenv
BILLING_PROVIDER=lemonsqueezy
LEMONSQUEEZY_API_KEY=...
LEMONSQUEEZY_STORE_ID=12345
LEMONSQUEEZY_WEBHOOK_SECRET=the-signing-secret
LEMONSQUEEZY_VARIANT_PRO_MONTHLY=111111
LEMONSQUEEZY_VARIANT_PRO_YEARLY=222222
```

Trials: configure the free trial on each variant in the Lemon Squeezy dashboard and keep its length equal to
`trial_days` in `plans.py`, so the pricing page shows the right number. A test-mode API key creates test-mode
checkouts.

### Creem

1. Create two subscription products (Pro monthly and Pro yearly).
2. Developers → Webhooks → add `{APP_URL}/api/webhooks/billing/creem` and copy the signing secret.
   Events to send: `checkout.completed`, `subscription.active`, `subscription.trialing`, `subscription.paid`,
   `subscription.update`, `subscription.past_due`, `subscription.unpaid`, `subscription.paused`,
   `subscription.scheduled_cancel`, `subscription.canceled`, `subscription.expired`.
3. Set:

```dotenv
BILLING_PROVIDER=creem
CREEM_API_KEY=creem_...
CREEM_WEBHOOK_SECRET=whsec_...
CREEM_PRODUCT_PRO_MONTHLY=prod_...
CREEM_PRODUCT_PRO_YEARLY=prod_...
# Test mode (test keys only work with the test API URL):
# CREEM_API_URL=https://test-api.creem.io
```

Trials: configure the trial on each product in the Creem dashboard and keep its length equal to `trial_days` in
`plans.py`.

Admins can give any organization a plan without payment from **Admin → Organizations → Plan override**.

## Google login

1. In Google Cloud Console create an OAuth client of type "Web application".
2. Authorized redirect URI: `{APP_URL}/api/auth/google/callback` (locally
   `http://localhost:5173/api/auth/google/callback`).
3. Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`. The "Continue with Google" button appears on the login and
   register pages; existing users are linked by verified email.

## First superadmin

Either:

- Set `SUPERADMIN_EMAIL=you@example.com`. That user becomes superadmin when they register, and at every startup
  if they already exist. On Runsite, add the variable in the web service environment; the redeploy promotes you.
- Or run the CLI against the database. It promotes an existing user, or creates one (it asks for a password, or
  takes `--password`; `--name` sets the full name). Locally:

```bash
cd backend && uv run python -m app.cli create-superadmin --email you@example.com
```

On Runsite, run `python -m app.cli create-superadmin --email you@example.com` in the web service
[shell](https://docs.runsite.app/platform/shell/).

Superadmins see the full admin panel at `/admin`: metrics, granting `admin` to other users, impersonation. Admins
see users, organizations and the setup checklist.

## Branding

| What | Where |
|---|---|
| Product name in the UI (fallback), logo text, support email, Runsite link | `frontend/src/config/brand.ts` |
| Product name in emails and the UI | `BRAND_NAME` environment variable (returned by `/api/config/public`) |
| Colours, radius, light and dark palettes | CSS variables in `frontend/src/index.css` (`:root` and `.dark`), shadcn/ui tokens |
| Page title and favicon | `frontend/index.html`, `frontend/public/` |
| Landing page copy | `frontend/src/i18n/locales/en/landing.json` |
| All other UI text | `frontend/src/i18n/locales/en/` |
| Email templates | `backend/app/emails/templates/` (`layout.html` holds the header and footer of every email) |

To remove the "Deployed on Runsite" link, delete `<RunsiteCredit />` from
`frontend/src/components/landing/LandingFooter.tsx` (and the link in `frontend/src/components/layout/PublicLayout.tsx`).
The landing at `/` is a placeholder; replace `frontend/src/pages/LandingPage.tsx` with your own marketing page
whenever you like.

## Add your own module

Coding agents (Claude Code, Cursor, Codex) read the rules in `AGENTS.md` (`CLAUDE.md` imports it). The `projects`
module is the reference. Copy it layer by layer and rename `project` to your entity. A request
flows route → dependencies (current user, membership, role, plan feature) → service → repository → model.

| Layer | Projects example | What to do |
|---|---|---|
| Model | `backend/app/models/project.py` | Add your model with `organization_id`; inherit `Base, UUIDPrimaryKeyMixin, TimestampMixin`. |
| Model registry | `backend/app/models/__init__.py` | Import your model so Alembic sees it. |
| Migration | `backend/alembic/versions/` | `make makemigration name="add invoices"`, review the file, then `make migrate`. |
| Repository | `backend/app/repositories/project_repository.py` | Every query takes `organization_id` first and filters by it. |
| Schemas | `backend/app/schemas/projects.py` | Request and response models. |
| Service | `backend/app/services/project_service.py` | Business rules, plan limits, one `commit()` per write. |
| Routes | `backend/app/routers/routes/projects.py` | Routes under `/orgs/{org_id}/...` with `CurrentMembership`. |
| Router registry | `backend/app/routers/api.py` | Include your router. |
| Tests | `backend/tests/test_projects.py` | Copy the organization isolation and role tests. |
| API types | `frontend/src/types/api.ts` | Mirror the response schema (snake_case). |
| Service client | `frontend/src/services/projectService.ts` | Functions over `fetchApi`. |
| Page and components | `frontend/src/pages/app/ProjectsPage.tsx`, `frontend/src/components/projects/ProjectFormDialog.tsx` | List, create, edit. |
| Strings | `frontend/src/i18n/locales/en/projects.json`, `frontend/src/i18n/index.ts` | Add a namespace and register it in `resources.en`. |
| Route and menu | `frontend/src/router/routes.tsx`, `frontend/src/components/layout/AppLayout.tsx` | Add the page under `/app/:orgSlug` and an entry in `APP_NAVIGATION_ITEMS`. |

To limit it per plan, add a field to `Limits` in `backend/app/services/billing/plans.py` and a check in
`backend/app/services/plan_limits.py`. To make it a paid feature, add it to a plan's `features` and protect the
routes with `require_feature("your_feature")`.

## Tests

```bash
make test     # backend and frontend
make check    # lint, type check and tests
```

`make test-backend` and `make test-frontend` run one side. Tests run memory-capped (systemd on Linux) and
time-limited where the tools are available. Backend tests use the `saaskit_test` database from docker-compose and
roll back every test. Frontend tests run with Vitest. `backend/tests/test_project_docs.py` checks that this README
and `.env.example` list every setting, and `frontend/src/i18n/translationKeys.test.ts` checks that every
translation key used in the code exists.

## License

MIT. See `LICENSE`.
