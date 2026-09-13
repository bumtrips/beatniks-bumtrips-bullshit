# assets/org/

Brand assets that are referenced by other systems, not by the site itself.

| File | Used by | Status |
|---|---|---|
| `bumtrips-avatar.png` | bumtrips org avatar (1024×1024) | uploaded to GitHub org settings |
| `bumtrips-avatar-256.png` | preview / fallback | not uploaded anywhere |
| `bumtrips-social-preview.png` | repo social preview (1280×640) | uploaded to repo settings |

## Updating these assets

GitHub exposes no API for either upload, so they're manual:

- **Org avatar**: github.com → organization → Settings → Profile picture.
- **Social preview**: repo → Settings → General → Social preview → Edit.

Regenerate the PNGs with `scripts/build_assets.py`.
