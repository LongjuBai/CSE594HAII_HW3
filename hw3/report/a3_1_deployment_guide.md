# A3-1 Deployment Guide

## What is already implemented
- Custom frontend and backend
- Baseline and AI-assisted conditions
- Trial randomization from the HW2 study dataset
- Storage of worker ID, assignment ID, HIT ID, condition, trial order, answers, confidence, time spent, and post-study measures
- Completion code display for MTurk approval
- Optional MTurk auto-submit if the platform appends `turkSubmitTo`

## Recommended deployment choice
Use the **survey link** workflow on MTurk. It is simpler than embedding the app through the MTurk API and still satisfies the assignment requirement because the actual task runs on your own web application with your own backend.

## Step-by-step checklist
1. Initialize the database locally:
   `conda run -n counseling python hw3/app.py --init-db`
2. Test locally using both condition URLs from `hw3/README.md`.
3. Put the project on a machine with a public HTTPS URL.
4. Start the server there with:
   `conda run -n counseling python hw3/app.py --host 0.0.0.0 --port 8000`
5. Confirm the public health check works:
   `https://YOUR_PUBLIC_URL/health`
6. Generate MTurk URLs with:
   `conda run -n counseling python hw3/scripts/mturk_link_helper.py --base-url https://YOUR_PUBLIC_URL`
7. Create two MTurk studies in Requester Sandbox:
   - one with the `baseline` URL
   - one with the `ai` URL
8. Set clear worker instructions telling them to return the completion code after finishing.
9. Pilot both studies yourself in Worker Sandbox.
10. After data collection, export with:
    `conda run -n counseling python hw3/scripts/export_study_data.py`

## Suggested worker instructions
You can adapt this text inside MTurk:

"You will complete a short counselor-response judgment task. Read each client statement and counselor response, then label the response as appropriate or problematic. After finishing all trials, copy the completion code shown on the final page back into MTurk so your work can be approved."

## Suggested MTurk settings
- Estimated completion time: 8 to 10 minutes
- Expiration: set generously so classmates are not blocked
- Separate baseline and AI-assisted studies
- Keep the same payment across conditions

## What to screenshot for A3-1 submission
- Baseline instruction / task page
- AI-assisted page with AI panel visible
- Final completion-code screen
- Proof that rows were recorded in the SQLite export or export CSV
