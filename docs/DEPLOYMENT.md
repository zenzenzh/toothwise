# Deploying ToothWise

| Part | Host | Cost |
|---|---|---|
| Frontend (React + `/api/chatbot` function) | Vercel | Free (Hobby) |
| Backend (FastAPI + YOLOv8/YOLOv12 + KNN) | Hugging Face Space, Docker | Free (CPU basic, 16 GB RAM) |
| Database (PostgreSQL) | Neon | Free |

Screening photos are copied into the database (`STORE_IMAGES_IN_DB=true`)
because a free Space wipes its disk on every restart.

> **Before you start**
> - A free Space must be **public**, so its source code and the two YOLO
>   weight files can be browsed and downloaded. Patient data is not in the
>   Space (it lives in Neon, behind login). If the code or weights must stay
>   private, use a paid host instead (Railway, Render, ~$7–25/month). The same
>   `backend/Dockerfile` works there; skip step 3 and point that host at it.
> - Use test accounts and sample photos until the clinic approves real patient
>   data online (Data Privacy Act of 2012).
> - `backend/.env` was committed to GitHub in the past. **Do not reuse any
>   value from it.** Create a new Gemini key and delete the old one in
>   [Google AI Studio](https://aistudio.google.com/apikey), and generate a new
>   `SECRET_KEY` and admin password below.

Generate a secret key (copy the output):

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 1. Database (Neon)

1. Sign in at [neon.tech](https://neon.tech) and create a project (region:
   Singapore is closest to Manila).
2. Copy the connection string and change the start to `postgresql+psycopg://`:

   ```
   postgresql+psycopg://USER:PASSWORD@HOST/neondb?sslmode=require
   ```

   This is your `DATABASE_URL`. The backend creates the tables on first start.

## 2. Backend Space (Hugging Face)

1. Sign in at [huggingface.co](https://huggingface.co) and choose
   **New Space**: name `toothwise-api`, SDK **Docker**, template **Blank**,
   hardware **CPU basic (free)**, visibility **Public**.
2. In the Space, open **Settings → Variables and secrets** and add these as
   **Secrets**:

   | Name | Value |
   |---|---|
   | `ENV` | `production` |
   | `SECRET_KEY` | the value you generated |
   | `DATABASE_URL` | from step 1 |
   | `GEMINI_API_KEY` | your **new** Gemini key |
   | `STORE_IMAGES_IN_DB` | `true` |
   | `CORS_ORIGINS` | `https://YOUR-APP.vercel.app` (fill in after step 5) |
   | `CORS_ORIGIN_REGEX` | `^https://toothwise[a-z0-9-]*\.vercel\.app$` |

   `CORS_ORIGIN_REGEX` replaces the development default (any localhost port)
   and also allows Vercel preview URLs. Adjust it if your Vercel project name
   doesn't start with `toothwise`.

## 3. Upload the backend

From the repository root, once:

```bash
backend/.venv/Scripts/python.exe -m pip install huggingface_hub
backend/.venv/Scripts/huggingface-cli.exe login
```

`login` asks for an access token: create one at
[huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
with **Write** access and paste it there (it is stored on your computer, not
in the repo).

Check what will be uploaded (no secrets, uploads, backups or test data):

```bash
backend/.venv/Scripts/python.exe deploy/push_backend_to_hf.py YOUR-HF-USERNAME/toothwise-api --dry-run
```

Then upload:

```bash
backend/.venv/Scripts/python.exe deploy/push_backend_to_hf.py YOUR-HF-USERNAME/toothwise-api
```

The Space builds the image (about 5–10 minutes the first time). When it shows
**Running**, open:

```
https://YOUR-HF-USERNAME-toothwise-api.hf.space/api/health
```

It should return `"status":"ok"` and `"database":"connected"`.

Run the same upload command again whenever the backend changes.

## 4. Create the first staff account

From the `backend` folder, point the seed script at Neon with a **new**
password (Git Bash):

```bash
cd backend
DATABASE_URL="postgresql+psycopg://...neon...?sslmode=require" \
SEED_ADMIN_EMAIL="admin@codismile.example" \
SEED_ADMIN_PASSWORD="a-new-strong-password" \
SEED_ADMIN_NAME="Clinic Administrator" \
SEED_ADMIN_LICENSE="PRC-0000000" \
.venv/Scripts/python.exe seed_accounts.py
```

Values set on the command line override `backend/.env`.

## 5. Frontend (Vercel)

1. Sign in at [vercel.com](https://vercel.com) with GitHub and
   **Add New → Project → Import** the `toothwise` repository.
2. **Root Directory:** `frontend`. Framework preset: **Create React App**
   (detected automatically).
3. **Environment Variables:**

   | Name | Value |
   |---|---|
   | `REACT_APP_API_URL` | `https://YOUR-HF-USERNAME-toothwise-api.hf.space` |
   | `GEMINI_API_KEY` | your new Gemini key (used by `frontend/api/chatbot.js`) |
   | `GEMINI_MODEL` | `gemini-3.6-flash` |

4. **Deploy.** Every push to `master` redeploys automatically afterwards.
5. Copy the production URL (e.g. `https://toothwise.vercel.app`) into the
   Space secret `CORS_ORIGINS`, then **Restart** the Space.

## 6. Check it works

- [ ] Landing page loads, services carousel swipes, map shows.
- [ ] Chatbot answers "What are your clinic hours?".
- [ ] Staff login with the seeded account.
- [ ] Register a test patient, upload a sample photo, see detections and the
      prevention plan.
- [ ] Download the PDF report.
- [ ] Restart the Space (Settings → Restart), then open the same screening:
      the photo still shows (restored from the database).
- [ ] Patient portal: sign up, sign in.

## Good to know

- **Sleep:** a free Space sleeps after 48 hours without visits. The next
  visit wakes it, which takes 1–2 minutes (the first request may time out;
  refresh).
- **Clinician tier confirmations** (`labeled_cases.jsonl`, used to retrain the
  KNN) are written to the Space's disk and reset on restart. The model itself
  retrains from its built-in data on every start, so screenings keep working.
- **Gemini free quota** is shared by the website chatbot. When it runs out,
  clinic questions (hours, location, services, prices) are still answered from
  verified facts; other questions show a "temporarily unavailable" message.
