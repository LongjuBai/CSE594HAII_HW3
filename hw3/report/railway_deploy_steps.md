# Railway Deployment Steps

## What is already configured in the repo
- Root config file: `railway.toml`
- Start command: `python hw3/app.py --host 0.0.0.0`
- Health check path: `/health`
- App reads Railway's `PORT` automatically
- App can store SQLite on a mounted volume via `STUDY_DB_PATH`

## Recommended Railway setup
1. Push this repo to GitHub.
2. Create a new Railway project from the GitHub repo.
3. Let Railway build the repo root.
4. After the service exists, add a volume and mount it at `/data`.
5. Add environment variable:
   `STUDY_DB_PATH=/data/study.db`
6. Open the deployed service logs and confirm the app starts.
7. In `Settings -> Networking -> Public Networking`, click `Generate Domain`.
8. Open `https://YOUR_DOMAIN/health` and confirm it returns JSON.
9. Reset any pilot data after first deployment if needed:
   `railway shell` then `python hw3/scripts/reset_study_state.py --yes`
10. Generate final MTurk links locally with:
   `conda run -n counseling python hw3/scripts/mturk_link_helper.py --base-url https://YOUR_DOMAIN`

## Notes
- This app stores participant data in SQLite, so the volume is important.
- Without a volume, deploys/restarts may wipe collected study data.
- You should create two MTurk studies: one for `baseline`, one for `ai`.

## After data collection
Export the data either from Railway shell or by copying the database locally and running:
`python hw3/scripts/export_study_data.py`
