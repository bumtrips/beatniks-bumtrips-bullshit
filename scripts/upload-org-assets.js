#!/usr/bin/env node
/**
 * Upload bumtrips org assets via a headless browser session.
 *
 * Why this exists: GitHub's REST API does not expose
 *   - org avatar upload (`PATCH /orgs/{org}` doesn't accept `avatar`)
 *   - repo social-preview upload (no endpoint at all)
 * Both require a CSRF-gated multipart POST to a web endpoint, behind
 * an authenticated browser session. This script drives that flow with
 * Playwright.
 *
 * One-time setup (run on your laptop, not in CI):
 *
 *   # 1. Install Playwright locally (once)
 *   npm install --no-save playwright
 *   npx playwright install --with-deps chromium
 *
 *   # 2. Launch a Chromium that you will log into GitHub in.
 *   #    The session cookies get saved to ./auth-state.json.
 *   node -e "require('playwright').chromium.launchPersistentContext(
 *     '/tmp/bb-profile',
 *     { headless: false }
 *   ).then(async c => {
 *     const page = await c.newPage();
 *     await page.goto('https://github.com/login');
 *     console.log('Log into GitHub in the browser window that just opened.');
 *     console.log('When you reach https://github.com, press ENTER here.');
 *     await new Promise(r => process.stdin.once('data', r));
 *     await c.storageState({ path: 'auth-state.json' });
 *     await c.close();
 *     console.log('Saved ./auth-state.json');
 *   })"
 *
 *   # 3. Encode and add as a repo secret.
 *   base64 -w0 auth-state.json > auth-state.b64
 *   gh secret set AUTH_STATE_B64 < auth-state.b64 \
 *     --repo bumtrips/beatniks-bumtrips-bullshit
 *
 * After that:
 *   - Re-run the workflow from the Actions tab.
 *   - It also re-runs automatically on any push that touches
 *     assets/org/** (so a future tweak to the avatar / social preview
 *     gets uploaded on the same commit).
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const ORG = 'bumtrips';
const REPO = 'beatniks-bumtrips-bullshit';
const ROOT = path.resolve(__dirname, '..');
const ORG_AVATAR = path.join(ROOT, 'assets', 'org', 'bumtrips-avatar.png');
const SOCIAL_PREVIEW = path.join(ROOT, 'assets', 'org', 'bumtrips-social-preview.png');

const DRY_RUN = process.env.DRY_RUN === 'true' || process.env.DRY_RUN === '1';
const WANT_AVATAR = process.env.UPLOAD_ORG_AVATAR !== 'false';
const WANT_PREVIEW = process.env.UPLOAD_SOCIAL_PREVIEW !== 'false';

function log(...args) {
  console.log('[upload-org-assets]', ...args);
}

async function loadStorageState() {
  const b64 = process.env.AUTH_STATE_B64;
  if (!b64) {
    throw new Error('AUTH_STATE_B64 secret is missing. See the one-time setup steps at the top of this file.');
  }
  const json = Buffer.from(b64, 'base64').toString('utf8');
  return JSON.parse(json);
}

async function uploadOne(label, url, filePath) {
  if (!fs.existsSync(filePath)) {
    log(`SKIP ${label} — file not found: ${filePath}`);
    return;
  }
  const storageState = await loadStorageState();
  const browser = await chromium.launch({ headless: true });
  try {
    const context = await browser.newContext({
      storageState,
      userAgent: 'bumtrips-org-assets-bot (+https://bumtrips.com)',
    });
    const page = await context.newPage();
    log(`opening ${url}`);
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
    // Sanity check: make sure we are still authenticated.
    const title = await page.title();
    if (/sign in to github/i.test(title)) {
      throw new Error(`Landed on the GitHub sign-in page for ${url} — the auth-state.json is stale or the cookie was rotated. Re-capture it.`);
    }
    log(`page title: ${title}`);
    if (DRY_RUN) {
      log(`DRY: would upload ${path.basename(filePath)} (${fs.statSync(filePath).size} bytes) to ${label}`);
      return;
    }
    // Find the first file input on the page. GitHub's settings pages
    // wrap the avatar / social-preview upload in a hidden <input type=file>.
    const fileInput = await page.$('input[type="file"]');
    if (!fileInput) {
      throw new Error(`No file input found on ${url}.`);
    }
    await fileInput.setInputFiles(filePath);
    // GitHub's upload UI is JS-driven — wait for either a success toast
    // or a network-idle moment after the multipart POST completes.
    await page.waitForLoadState('networkidle', { timeout: 30000 });
    log(`uploaded ${label}`);
  } finally {
    await browser.close();
  }
}

(async () => {
  if (WANT_AVATAR) {
    await uploadOne(
      'org avatar',
      `https://github.com/organizations/${ORG}/settings/profile`,
      ORG_AVATAR,
    );
  }
  if (WANT_PREVIEW) {
    await uploadOne(
      'repo social preview',
      `https://github.com/${ORG}/${REPO}/settings`,
      SOCIAL_PREVIEW,
    );
  }
  log('done');
})().catch(err => {
  console.error('[upload-org-assets] FATAL:', err && err.message || err);
  process.exit(1);
});
