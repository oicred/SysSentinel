# Secure GitHub And Google Cloud Deployment

This guide prepares `codex/submission-ready` for a public GitHub repository and a
cost-controlled Cloud Run demo. Run commands only after replacing every placeholder.

## 1. Audit Before Publishing

Confirm the correct branch and a clean worktree:

```bash
git branch --show-current
git status --short --ignored
git ls-files
git log --all --oneline -- .env
git grep -n -I -E "AIza|BEGIN PRIVATE KEY|ELASTICSEARCH_API_KEY=.+"
```

Expected results:

- Branch is `codex/submission-ready`.
- `.env`, `_private_submission/`, virtual environments, caches, and bytecode are ignored.
- No real credentials appear in tracked files or Git history.
- Root `README.md`, `DEMO.md`, and `SUBMISSION.md` are the public canonical documents.

Create a public GitHub repository without generated starter files, then add and push the
remote only after the audit:

```bash
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
git push -u origin codex/submission-ready
```

## 2. Create A Dedicated Google Cloud Project

Use a project created only for the hackathon. Set a region and project:

```bash
gcloud config set project YOUR_PROJECT_ID
gcloud config set run/region us-central1
```

Enable only the required APIs:

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  generativelanguage.googleapis.com
```

Create the Artifact Registry repository:

```bash
gcloud artifacts repositories create hackathon \
  --repository-format=docker \
  --location=us-central1
```

## 3. Create A Least-Privilege Runtime Identity

Create a dedicated Cloud Run runtime service account:

```bash
gcloud iam service-accounts create syssentinel-runtime \
  --display-name="SysSentinel Cloud Run runtime"
```

Do not grant broad project roles such as Owner, Editor, or Viewer. Secret access is
granted on the individual secrets after they are created.

## 4. Create And Pin Secrets

Generate a long random demo key locally and keep it out of Git:

```powershell
$demoKey = -join ((48..57)+(65..90)+(97..122) | Get-Random -Count 48 | ForEach-Object {[char]$_})
$demoKey
```

Create the secrets and their first versions:

```bash
printf "YOUR_GEMINI_API_KEY" | gcloud secrets create gemini-api-key --data-file=-
printf "YOUR_LONG_RANDOM_DEMO_KEY" | gcloud secrets create demo-api-key --data-file=-
```

Grant the runtime identity access only to these two secrets:

```bash
gcloud secrets add-iam-policy-binding gemini-api-key \
  --member="serviceAccount:syssentinel-runtime@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding demo-api-key \
  --member="serviceAccount:syssentinel-runtime@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

The included Cloud Build configuration pins both secrets to version `1`. When rotating a
secret, add a new version and update `cloudbuild.yaml` to the new explicit version.

## 5. Configure Cloud Build Permissions

Find the Cloud Build service account:

```bash
PROJECT_NUMBER=$(gcloud projects describe YOUR_PROJECT_ID --format="value(projectNumber)")
BUILD_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"
```

Grant only the roles needed to build, deploy, and attach the runtime identity:

```bash
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:${BUILD_SA}" \
  --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:${BUILD_SA}" \
  --role="roles/run.admin"

gcloud iam service-accounts add-iam-policy-binding \
  syssentinel-runtime@YOUR_PROJECT_ID.iam.gserviceaccount.com \
  --member="serviceAccount:${BUILD_SA}" \
  --role="roles/iam.serviceAccountUser"
```

## 6. Deploy The Cost-Controlled Demo

Submit the pinned configuration:

```bash
gcloud builds submit --config cloudbuild.yaml
```

Cloud Run remains publicly reachable so judges can view `/`, `/docs`, and
`/resolve/examples`. Calls to `POST /resolve` require the private `X-Demo-Key` header.
The deployment limits concurrency to `2`, maximum instances to `1`, and request timeout
to `60s`.

Test the deployed service:

```bash
curl https://YOUR_SERVICE_URL/

curl -X POST https://YOUR_SERVICE_URL/resolve \
  -H "Content-Type: application/json" \
  -H "X-Demo-Key: YOUR_LONG_RANDOM_DEMO_KEY" \
  -d '{"alert":"Database connection pool timeout in prod-db-01"}'
```

Share the demo key privately with judges. Never place it in Devpost public text, GitHub,
screenshots, recordings, or browser history visible during recording.

## 7. Budget, Quota, And Shutdown Checklist

- Create a small Cloud Billing budget with email alerts before deployment.
- Review Gemini API quotas and lower them where available.
- Confirm Cloud Run has `max-instances=1`.
- Monitor Cloud Run request counts and Gemini usage during judging.
- Rotate `demo-api-key` immediately if it leaks.
- After judging, delete the service or remove public access:

```bash
gcloud run services delete syssentinel --region us-central1
```

For complete isolation after the event, disable billing or delete the dedicated project.

## Security References

- [Cloud Run secrets](https://docs.cloud.google.com/run/docs/configuring/services/secrets)
- [Cloud Run service identity](https://docs.cloud.google.com/run/docs/securing/service-identity)
- [Cloud Run maximum instances](https://docs.cloud.google.com/run/docs/configuring/max-instances-limits)
- [Google Cloud budgets](https://docs.cloud.google.com/billing/docs/how-to/budgets)
