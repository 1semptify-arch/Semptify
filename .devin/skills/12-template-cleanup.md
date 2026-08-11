---
description: Checklist for removing dead templates and routes
---

# Template Cleanup Checklist

Before deleting templates or routes, verify each item:

1. **Identify the dead files** — stubs, duplicates, abandoned concepts, empty pages.
2. **Check route registry** — remove routes from `main.py` and any router that served the deleted pages.
3. **Remove includes** — search templates for `{% include "path/to/deleted_partial.html" %}` and remove them.
4. **Update aliases** — remove any alias entries in admin subpage dictionaries or page manifests.
5. **Verify surviving templates** — confirm canonical templates still cover the removed functionality.
6. **Leave page manifest data declarations** if they do not cause runtime errors; clean them separately.

Do not delete static assets referenced by active templates until the replacement is verified live.
