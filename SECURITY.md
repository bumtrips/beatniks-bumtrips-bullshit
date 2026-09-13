# Security

This is the source repository for the [bumtrips.com](https://bumtrips.com)
marketing site. It is a static page served from GitHub Pages — there is
no server-side code, no database, no API, and no authentication.

## What this site does NOT do

- It does not run application code on a server.
- It does not store cookies, sessions, or user data.
- It does not handle authentication, payments, or PII.
- It does not accept file uploads or user-submitted content directly.

The only forms on the site are links to external podcast platforms
(Apple, Spotify, Anchor) and a static contact form that opens the user's
mail client.

## What can still be reported

If you spot any of the following, please report it:

- A broken link or a URL that points to a malicious destination.
- A leaked token, password, or private key in the repository history.
- A typo in the page that creates a misleading impression about the show.
- A misconfigured GitHub Actions workflow (e.g. one that prints secrets
  to logs, or runs on `pull_request_target` from forks without proper
  hardening).
- Anything else that affects the integrity of the site.

## How to report

Please **do not** open a public GitHub issue for anything sensitive.

Preferred channels:

1. **Open a regular issue** at
   <https://github.com/bumtrips/beatniks-bumtrips-bullshit/issues/new/choose>
   for non-sensitive reports (broken link, typo, suspicious URL).
2. **Use the contact form** at <https://bumtrips.com/#contact> for
   everything else. The form opens your mail client and emails the
   maintainer directly.

If the issue is urgent and you cannot reach us through the above,
GitHub also lets you report repository-level security issues via
<https://github.com/bumtrips/beatniks-bumtrips-bullshit/security/advisories/new>.

## Response

We are a small team (effectively one maintainer plus bots). Expect a
first reply within a few days. We'll either fix in the repo and push a
patch release, or close out as not-applicable with a short reason.

## Supported versions

Only the live site at <https://bumtrips.com> is supported. We do not
maintain old releases; every release is a snapshot of the deployed site
at that point in time.
