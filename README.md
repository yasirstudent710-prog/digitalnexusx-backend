# DigitalNexusX — Backend + Admin Dashboard

Yasir, ye aap ki website https://digitalnexusx.com ka backend hai. Website ka form ab leads save karega, aur dashboard se aap leads, stats, services aur settings control kar sakte hain — website foran update ho jayegi.

**Contact seeded:** digitalnexusxpk@gmail.com, +92 322 1526000, DHA Phase 1, Lahore, Pakistan

## Local Run — Windows (IMPORTANT: hamesha `python -m` form)

Aap ke PC par Scripts folder PATH par nahi hai, is liye bare `uvicorn` / `pip` nahi chalega. Hamesha ye form use karein:

```powershell
cd digitalnexusx-backend
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

- API Docs: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health
- **Dashboard: http://127.0.0.1:8000/admin**

## Default Admin Login — WARNING

- Username: `admin`
- Password: `admin123`

**Ye default password lazmi change karein.** Production me env vars set karein: `ADMIN_USERNAME` aur `ADMIN_PASSWORD` apna strong password rakhein. Default kabhi live par na rakhein.

## Live Website Form Connect Karna

1. Backend deploy karein (neeche Railway steps), us ka URL copy karein.
2. `website-integration.js` me `API_BASE` me wo URL dalen.
3. Us file ka code apni website ke contact form wali page me paste karein, form ko `id="contactForm"` dein.
4. Homepage stats ke numbers par ids dein: `statLeads`, `statSales`, `statCPL`, `statRoas` — phir 0+ placeholders dashboard wale numbers se auto replace ho jayenge.

## Deploy — Railway + Neon (Free)

1. **Neon:** neon.tech par free PostgreSQL database banayein, connection string copy karein.
2. **GitHub:** is folder ko ek naye repo `digitalnexusx-backend` me push karein (login aap ka apna step hai).
3. **Railway:** New Project → Deploy from GitHub repo → is repo ko select karein. Dockerfile auto use hoga.
4. Railway → Variables me ye set karein:
   - `DATABASE_URL` = Neon connection string
   - `SECRET_KEY` = lambi random string
   - `ADMIN_USERNAME` = admin
   - `ADMIN_PASSWORD` = strong password (admin123 NAHI)
   - `ALLOWED_ORIGINS` = https://digitalnexusx.com,https://www.digitalnexusx.com
5. Railway domain generate karein, phir `https://your-domain/health` khol kar check karein aur dashboard usi domain par `/admin` par milega.

## Features

- Public: POST /api/leads, POST /api/consultations, GET /api/stats, /api/services, /api/faqs, /api/settings
- Admin (login required): dashboard totals, leads search/filter/status/CSV export/delete, consultations, services & FAQs CRUD, stats edit, settings edit
- Database: local SQLite default, production me Neon PostgreSQL sirf `DATABASE_URL` change karne se.

## Test

Server chala kar dusri PowerShell window me:
```powershell
python test_api.py
```
Success par: `ALL TESTS PASSED`
