# Deploying ToothWise (free, no payment card)

| Part | Host | Free tier |
|---|---|---|
| Frontend (React + `/api/chatbot` function) | Vercel (Hobby) | Yes, no card |
| Backend (FastAPI + YOLOv8/YOLOv12 + KNN) | Render (Free web service) | Yes, no card, 512 MB |
| Database (PostgreSQL) | Neon | Yes, no card |

**How the backend fits in 512 MB.** On Render it runs with `YOLO_BACKEND=onnx`:
both YOLO models run through onnxruntime instead of PyTorch, loaded one at a
time per screening. Detections are identical to the `.pt` models (verified on
22 images: same boxes, labels and confidences). Measured: ~210 MB at rest,
~400 MB peak, ~3–4 s per screening with both models. Screening photos are also
copied into the database (`STORE_IMAGES_IN_DB=true`) because Render's disk is
wiped when the service sleeps or restarts.

> **Before you start**
> - `backend/.env` was committed to GitHub in the past. **Do not reuse any
>   value from it.** Create a new Gemini key and delete the old one in
>   [Google AI Studio](https://aistudio.google.com/apikey), and use a new admin
>   password in step 3. Render generates `SECRET_KEY` for you.
> - Use test accounts and sample photos until the clinic approves real patient
>   data online (Data Privacy Act of 2012).
> - Your Render service, Vercel project and Neon database can be private to
>   your account; only the website and API URLs are public (everything
>   patient-related needs a login).

---

## 1. Database (Neon)

1. Sign up at [neon.tech](https://neon.tech) (GitHub or Google sign-in, no card)
   and create a project. Region: **AWS Asia Pacific (Singapore)**.
2. On the project dashboard choose **Connect**, copy the connection string, and
   change its start from `postgresql://` to `postgresql+psycopg://`:

   ```
   postgresql+psycopg://USER:PASSWORD@HOST/neondb?sslmode=require
   ```

   This is your `DATABASE_URL`. The backend creates the tables on first start.

## 2. Backend (Render)

1. Sign up at [render.com](https://render.com) with **GitHub** (no card) and
   allow access to the `toothwise` repository.
2. **New → Blueprint**, pick the `toothwise` repo. Render reads `render.yaml`
   from the repo and shows a service called **toothwise-api** (Free plan).
3. It asks for the three values marked secret:

   | Name | Value |
   |---|---|
   | `DATABASE_URL` | from step 1 |
   | `GEMINI_API_KEY` | your **new** Gemini key |
   | `CORS_ORIGINS` | `https://toothwise.vercel.app` for now (fix in step 5) |

4. **Apply**. The first build takes about 5–10 minutes (installs packages, then
   rebuilds the ONNX models from the `.part` files with
   `python -m app.ml.prepare_onnx`). When it shows **Live**, open:

   ```
   https://toothwise-api.onrender.com/api/health
   ```

   (Use the URL Render shows if the name was taken.) It should return
   `"status":"ok"` and `"database":"connected"`.

Every push to `master` redeploys automatically.

## 3. Create the first staff account

From the `backend` folder on your computer, point the seed script at Neon with
a **new** password (Git Bash):

```bash
cd backend
DATABASE_URL="postgresql+psycopg://...neon...?sslmode=require" \
SEED_ADMIN_EMAIL="admin@codismile.com" \
SEED_ADMIN_PASSWORD="a-new-strong-password" \
SEED_ADMIN_NAME="Clinic Administrator" \
SEED_ADMIN_LICENSE="PRC-0000000" \
.venv/Scripts/python.exe seed_accounts.py
```

Values on the command line override `backend/.env`. Use a real-looking email
domain; reserved ones such as `.test` or `.local` are rejected at login.

## 4. Frontend (Vercel)

1. Sign up at [vercel.com](https://vercel.com) with **GitHub** (Hobby, no card)
   and **Add New → Project → Import** the `toothwise` repository.
2. **Root Directory:** `frontend`. Framework preset: **Create React App**.
3. **Environment Variables:**

   | Name | Value |
   |---|---|
   | `REACT_APP_API_URL` | `https://toothwise-api.onrender.com` (your Render URL) |
   | `GEMINI_API_KEY` | your new Gemini key (used by `frontend/api/chatbot.js`) |
   | `GEMINI_MODEL` | `gemini-3.6-flash` |

4. **Deploy.** Pushes to `master` redeploy automatically afterwards.

## 5. Connect the two

Copy your Vercel production URL (for example `https://toothwise.vercel.app`).
In Render, open **toothwise-api → Environment**, set `CORS_ORIGINS` to that URL
and save (the service restarts).

`CORS_ORIGIN_REGEX` in `render.yaml` also allows Vercel preview URLs whose name
starts with `toothwise`. If your Vercel project has a different name, change it
in Render's Environment tab.

## 6. Check it works

- [ ] Landing page loads, services carousel swipes, map shows.
- [ ] Chatbot answers "What are your clinic hours?".
- [ ] Staff login with the seeded account.
- [ ] Register a test patient, upload a sample photo, see detections and the
      prevention plan.
- [ ] Download the PDF report.
- [ ] In Render, **Manual Deploy → Restart service**, then open the same
      screening again: the photo still shows (restored from the database).
- [ ] Patient portal: sign up, sign in.

## Good to know

- **Sleep:** the free service sleeps after 15 minutes without requests. The
  next request wakes it, which takes about a minute, so the first login or
  page load after a quiet period is slow. Open the health URL a minute before
  a demo to wake it.
- **Monthly hours:** Render gives 750 free hours a month, enough for one
  service running all month. Without a payment method, Render pauses free
  services if a workspace runs out, until the next month.
- **Clinician tier confirmations** (`labeled_cases.jsonl`, used to retrain the
  KNN) are written to the service's disk and reset on restart. The KNN model
  itself retrains from its built-in data on every start.
- **Gemini free quota** is shared by the website chatbot. When it runs out,
  clinic questions (hours, location, services, prices) are still answered from
  verified facts; other questions show a "temporarily unavailable" message.
- **Retraining the YOLO models:** after replacing the `.pt` files, run
  `deploy/export_onnx.py` (see its header) and commit the new `.onnx.part*`
  and `.onnx.sha256` files.
- **Other hosts:** `backend/Dockerfile` runs the PyTorch build (about 1.5 GB of
  memory) on hosts with more RAM, such as a Hugging Face Docker Space (needs
  PRO) or a paid Render or Railway plan. `deploy/push_backend_to_hf.py`
  uploads the backend to a Space.
