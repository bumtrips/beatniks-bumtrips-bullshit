# assets/org/

Brand assets that are referenced by other systems, not by the site itself.

| File | Used by | Status |
|---|---|---|
| `bumtrips-avatar.png` | bumtrips org avatar (1024×1024) | upload via [workflow](../../.github/workflows/upload-org-assets.yml) |
| `bumtrips-avatar-256.png` | preview / fallback | not uploaded anywhere |
| `bumtrips-social-preview.png` | repo social preview (1280×640) | upload via [workflow](../../.github/workflows/upload-org-assets.yml) |

## Uploading these assets

The GitHub REST API does not expose upload of either:

- `PATCH /orgs/{org}` does not accept an `avatar` field.
- No documented endpoint exists for repo social-preview upload.

Both require an authenticated browser session. The
[`.github/workflows/upload-org-assets.yml`](../../.github/workflows/upload-org-assets.yml)
workflow drives that flow with Playwright using a captured session
state, and runs automatically on any push that touches this directory.

### One-time setup

1. **Install Playwright locally.**

   ```bash
   cd ~/Projects/studio2201/beatniks-bumtrips-bullshit
   npm install --no-save playwright
   npx playwright install --with-deps chromium
   ```

2. **Capture the GitHub session.**

   A `headed` browser opens; you log into GitHub normally (handle 2FA);
   the session cookies are saved to `./auth-state.json`.

   ```bash
   node -e "require('playwright').chromium.launchPersistentContext(
     '/tmp/bb-profile',
     { headless: false }
   ).then(async c => {
     const page = await c.newPage();
     await page.goto('https://github.com/login');
     console.log('Log into GitHub in the browser window that just opened.');
     console.log('When you reach https://github.com, press ENTER here.');
     await new Promise(r => process.stdin.once('data', r));
     await c.storageState({ path: 'auth-state.json' });
     await c.close();
     console.log('Saved ./auth-state.json');
   })"
   ```

3. **Add the session as a repo secret.**

   ```bash
   base64 -w0 auth-state.json | gh secret set AUTH_STATE_B64 \
     --repo bumtrips/beatniks-bumtrips-bullshit
   ```

4. **Trigger the workflow.**

   - Manual: Actions tab → "Upload org assets" → Run workflow.
     Tick "Dry run" first to validate, then untick to actually upload.
   - Automatic: any push to `assets/org/**` re-triggers the workflow.

### Re-capture cadence

GitHub rotates session cookies periodically. If a workflow run fails with
"Landed on the GitHub sign-in page", the cookie is stale — re-capture it
with the same one-time setup flow and re-add the secret.

### What does NOT happen

- The script never logs your password or 2FA code anywhere; the session
  state contains only the post-login cookie.
- The script does not commit `auth-state.json` to the repo; it stays
  local and is uploaded only as a base64-encoded secret.
