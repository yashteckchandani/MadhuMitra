# MadhuMitra

A local hackathon prototype for synthetic diabetes-care records. **Not for real patient data or clinical decisions.** All people, units, contact details and measurements are fictional. The assistant retrieves history and is not a medical decision system.

## Start locally

Requirements: Node.js 20+ and Python 3.9+.

```sh
python3 -m venv backend/.venv
source backend/.venv/bin/activate
pip install -r backend/requirements.txt
python backend/scripts/seed_data.py
uvicorn backend.app.main:app --reload --port 8000
```

In another terminal:

```sh
cd frontend
npm install
npm run dev
```

Open http://localhost:3000. API documentation: http://localhost:8000/docs. Both frontend and backend must use the same hostname (use `localhost`, not a mixture of `localhost` and `127.0.0.1`) for the session cookie.

## Test credentials

Run the seed script above to create these accounts on a fresh checkout:

| Role | User ID | Password | Available in |
| --- | --- | --- | --- |
| Healthcare provider | `doctor001` | `Doctor@123` | Web and Android |
| Administrator | `admin001` | `Admin@123` | Web |
| ASHA worker | `asha001` | `Asha@123` | Android |

On Android, choose your own numeric offline PIN of at least six digits when signing in online (for example, `123456` for local testing). There is no preset PIN; use the one you chose to unlock the account offline.

These credentials and the authentication mechanism are for local testing only. Web sessions are held in backend memory and expire on restart; cookies are HTTP-only. This is not production authentication.

## Storage and reset

The API reads JSON in `backend/data`, which is excluded from Git to keep locally entered patient records out of the repository. Run `python backend/scripts/seed_data.py` on a fresh checkout to generate fictional starting data; visits are appended using a process lock and atomic replacement. Run only one backend process: the lock does not coordinate multiple processes or machines. Records are never edited or deleted by the clinical API. Run `python backend/scripts/seed_data.py --reset` to overwrite all demo data; without `--reset` it will not overwrite existing data. Back up any changes first.

Priority is manually recorded, never inferred from measurements. Patients are ordered RED, PURPLE, YELLOW, GREEN, then by oldest latest visit. A unit with active workers cannot be deactivated; a worker with assigned patients cannot be deactivated. The current prototype has no patient reassignment UI, so those assignments must be managed outside this UI.

## Tests

From the repository root, with the backend environment active: `python -m unittest backend.tests.test_api -v`. Tests copy the data into a temporary directory.

## Configuration and limitations

`frontend/.env.example` documents the API URL. `backend/.env.example` documents CORS and cookie settings; export the values before starting the services. The patient chat can use Gemini to interpret questions, while the backend calculates and formats answers from the selected patient's local records. To enable it, copy `backend/.env.example` to `backend/.env`, set `GEMINI_API_KEY`, and restart the backend. `GEMINI_MODEL` selects a supported Gemini model (default `gemini-3.1-flash-lite-preview`); change it if necessary. The question is sent to Google, so do not include personal or sensitive information in it. Full patient histories are not sent to Gemini. Without a key, or if Gemini fails, chat explicitly falls back to deterministic local retrieval. The separate summary card remains deterministic and includes a history version and stale indicator.

This is an incomplete MVP: full response schemas, cross-process file locking, full administration detail views and reassignment, all requested filters/charts, mobile-specific table cards, React Hook Form/Zod, Tailwind/shadcn, and comprehensive automated/browser tests remain to be implemented. Inputs and safety controls require further hardening before any real deployment. A single local backend instance is required. If ports are occupied, change the server port and `NEXT_PUBLIC_API_URL` together; CORS must match the frontend origin.

## Enrollment and Sehat records

Healthcare providers can enroll fictional patients from the patient directory. The date of birth determines age; medical unit and active worker assignments are validated. Aadhaar and ABHA are optional, stored in local JSON, and omitted from directory and patient API responses. They are **not encrypted or verified**. Never enter real identifiers or health data in this prototype.

Patients without a recorded Sehat baseline use the baseline form; subsequent Sehat visits use the follow-up form. Every visit requires the opening check; if any response is Yes, the form stops and cannot be submitted. Questionnaire answers are optional unless otherwise indicated and remain attached to the append-only visit. Older visits remain intact and do not prevent a baseline screening. Photo and voice capture, OCR, automatic clinical calculations and triage are not implemented. Priority remains a manual entry.

## Android app (work in progress)

The Expo client lives in `mobile/` and shares the FastAPI JSON data. It uses the existing logo and the MadhuMitra — Connected Diabetes Care identity. Install Node 24.3 or later (Node 23 is not supported by Expo SDK 58), Android Studio with Android SDK platform-tools, an Android virtual device, and a compatible Java/Android build environment.

1. Start the backend as described above, using one backend instance. The Android emulator reaches the host through `10.0.2.2:8000`.
2. Create and start an Android virtual device from Android Studio’s Device Manager. Confirm that `adb devices` lists it.
3. In another terminal, run:

   ```sh
   cd mobile
   cp .env.example .env
   npm install
   npx expo start
   ```

4. Press `a` to open the Android emulator using Expo Go. For a local native development build instead, run `npx expo run:android` after installing the required Android SDK and Java tools. When changing native plugins or app configuration, rebuild that native app. Cleartext HTTP is configured for this local development prototype; use HTTPS for any real deployment.

Online sign-in creates a PIN-protected offline unlock for up to seven days. Doctor mobile access is deliberately limited to demo unit MU001; ASHA access is limited to assigned patients. Backend-issued mobile tokens currently expire after eight hours and are held in memory by the server; sign in again after expiry or backend restart. Explicit logout removes the saved offline unlock.

The app caches assigned patients and histories in SQLite, queues new patients and visits locally, and sends pending operations to the same backend. Operation IDs are recorded with JSON entities for retry deduplication; only one backend instance may write. Pulls are full scoped snapshots, not incremental cursors. A patient whose access is revoked is hidden on the next successful pull; pending edits remain in the outbox for resolution. The server cannot revoke an already cached offline copy until the device reconnects.

**Important limitations:** this is unfinished demo software, not ready for clinical or personal data. SQLite patient data is not encrypted; local PIN verification is prototype-grade; mobile refresh tokens, background sync, complete Sehat questionnaire, visit scheduling, complete chart features, full navigation, and automated mobile/offline/emulator testing are not complete. Photo and voice capture are not yet available on mobile. The mobile app has not been verified on an Android emulator. Do not use real Aadhaar numbers or patient records. Existing web functionality remains available.

If the app cannot reach the backend, check that the API is running, the emulator is using `http://10.0.2.2:8000` (not `localhost`), and the device has network access. The Sync screen shows pending operations and errors; do not clear app data while changes are pending.

The Sehat screens use a baseline questionnaire when a patient has no recorded Sehat baseline, including patients with older pre-Sehat visits; subsequent Sehat records use the follow-up questionnaire. Legacy patients can still accept older follow-up submissions. Both apps preserve structured questionnaire answers alongside the existing glucose, pressure, symptoms, and visit fields. Photo/voice capture, OCR, BMI/BP classifications and automated triage are not implemented; the questionnaire does not provide a complete, validated set of classification rules. Priority remains a manual clinical entry.
