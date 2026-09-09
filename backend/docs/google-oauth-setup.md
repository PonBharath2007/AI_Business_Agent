# Google OAuth 2.0 & OpenID Connect Setup Guide

This guide provides step-by-step instructions for configuring **Google OAuth 2.0 / OpenID Connect** authentication for the **AI Business Operations Agent** application across local development and production deployments (Vercel + Render).

---

## Architecture Overview

- **Frontend**: React + Vite (Local: `http://localhost:5173`, Production: `https://ai-business-agent-ten.vercel.app`)
- **Backend**: FastAPI + SQLAlchemy (Local: `http://localhost:8000`, Production: `https://ai-business-agent-ui7z.onrender.com`)
- **OAuth Protocol**: OpenID Connect (OIDC) / OAuth 2.0 Authorization Code Grant with CSRF state validation.
- **Security Rule**: `GOOGLE_CLIENT_SECRET` remains strictly on the FastAPI backend. It is never shared with or exposed to the client-side React frontend.

---

## Step 1: Open Google Cloud Console

1. Navigate to the [Google Cloud Console](https://console.cloud.google.com/).
2. Log in with your Google account.
3. In the top project selector bar, click **Select a project** -> **New Project** (or select an existing project).
4. Enter a Project Name (e.g., `ai-business-agent`) and click **Create**.

---

## Step 2: Configure the OAuth Consent Screen

1. In the left navigation menu, go to **APIs & Services** > **OAuth consent screen**.
2. Under **User Type**, choose:
   - **External** (standard for SaaS/public applications or multi-tenant business accounts).
3. Click **Create**.
4. Fill in the **App Information**:
   - **App name**: `AI Business Operations Agent`
   - **User support email**: Select your email address.
   - **Developer contact information**: Enter your email address.
5. Click **Save and Continue**.

---

## Step 3: Add Required OpenID Connect Scopes

1. On the **Scopes** page, click **Add or Remove Scopes**.
2. Select the three core OpenID Connect identity scopes:
   - `openid` (Associate you with your personal info on Google)
   - `.../auth/userinfo.email` (See your primary Google Account email address)
   - `.../auth/userinfo.profile` (See your personal info, including any personal info you've made publicly available)
3. Click **Update**, then click **Save and Continue**.
4. *(Optional for testing)*: Under **Test users**, add the email addresses of the Google accounts you intend to use for testing while the app is in "Testing" mode.
5. Click **Save and Continue**.

---

## Step 4: Create OAuth 2.0 Client ID Credentials

1. In the left menu, navigate to **APIs & Services** > **Credentials**.
2. Click **+ Create Credentials** at the top and select **OAuth client ID**.
3. In the **Application type** dropdown, select **Web application**.
4. Enter a descriptive Name: `AI Business Operations Agent Web Client`.

### Authorized JavaScript Origins:
Add the origins where your frontend application runs:
- **Local Development**: `http://localhost:5173`
- **Local Alternative**: `http://localhost:3000`
- **Production (Vercel)**: `https://ai-business-agent-ten.vercel.app` (or your production Vercel domain)

### Authorized Redirect URIs:
Add the FastAPI backend OAuth callback endpoints:
- **Local Development**: `http://localhost:8000/api/auth/google/callback`
- **Production (Render)**: `https://ai-business-agent-ui7z.onrender.com/api/auth/google/callback` (or your deployed Render backend domain)

5. Click **Create**.
6. A dialog box will display:
   - **Client ID** (e.g., `1234567890-abcdefg.apps.googleusercontent.com`)
   - **Client Secret** (e.g., `GOCSPX-xxxxxxxxxxxxxxxxxxxxxxxx`)
7. Copy both values. Keep the Client Secret secure.

---

## Step 5: Configure Backend Environment Variables

### Local Development (`backend/.env`)
Add the following configuration to your `backend/.env` file:

```env
# Google OAuth 2.0 Credentials (Backend Only)
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/google/callback
FRONTEND_URL=http://localhost:5173
```

### Production Deployment (Render Dashboard)
1. Go to your [Render Dashboard](https://dashboard.render.com/).
2. Select your FastAPI web service (`ai-business-agent-ui7z` or similar).
3. Navigate to **Environment** > **Add Environment Variable**:
   - `GOOGLE_CLIENT_ID`: `your-google-client-id.apps.googleusercontent.com`
   - `GOOGLE_CLIENT_SECRET`: `your-google-client-secret`
   - `GOOGLE_REDIRECT_URI`: `https://ai-business-agent-ui7z.onrender.com/api/auth/google/callback`
   - `FRONTEND_URL`: `https://ai-business-agent-ten.vercel.app`
4. Click **Save Changes** (Render will redeploy automatically).

---

## Step 6: Test Authentication Flow

### Local Testing:
1. Start the FastAPI backend:
   ```bash
   python backend/run.py
   ```
2. Start the Vite frontend:
   ```bash
   cd frontend && npm run dev
   ```
3. Open `http://localhost:5173/` in your browser.
4. On the Login page:
   - Verify layout: Email and Password inputs, followed by `[ Sign In to Dashboard ]`, then `──────── OR ────────`, followed by `[ Continue with Google ]`.
   - Click `[ Continue with Google ]`.
   - The button shows `Connecting to Google...` and disables duplicate clicks while redirecting.
   - You are redirected to Google's consent screen.
   - Select your Google account.
   - Google redirects back to `http://localhost:8000/api/auth/google/callback`.
   - Backend verifies CSRF state token, exchanges code for Google identity, finds/creates user and business, issues application JWT, and redirects to `http://localhost:5173/`.
   - You are logged in directly to the Dashboard.

### Testing Account Linking:
1. Register an account with email/password (e.g. `test@example.com`).
2. Log out.
3. Click `Continue with Google` using a Google account with email `test@example.com`.
4. Backend links the Google account with the existing user without duplicating accounts or changing existing business records/roles.

### Error Cases Handled:
- **User cancels login**: Redirects to frontend with friendly notice: `"Google sign-in was cancelled."`
- **Invalid / expired CSRF state**: Redirects with `"Google sign-in session expired or invalid state. Please try again."`
- **Invalid code / exchange failure**: Redirects with `"Unable to sign in with Google. Please try again."`
- **Unconfigured backend**: Displays `"Google authentication is not configured correctly on the server."` without crashing.
