"""Constants for the OurGroceries Sync integration."""

DOMAIN = "ourgroceries_sync"

# Config entry keys
CONF_USERNAME = "username"
CONF_PASSWORD = "password"

# Cache TTL for the master-list suggestions service. OurGroceries' own
# developer has asked integrations not to hammer their API (see
# home-assistant/core#105700) — the master list changes rarely, so a long
# cache is both correct and polite. Do not lower this without a real reason.
SUGGESTIONS_CACHE_SECONDS = 900  # 15 minutes

# Poll interval for the todo.* list sync coordinator. Unlike the master
# list, shopping lists change often (people add/check off items live), so
# this needs real polling — kept cheap via versionId-based skip-if-unchanged
# in coordinator.py rather than by polling less often.
LIST_SCAN_INTERVAL_SECONDS = 60

# Cap on concurrent delete requests OurGroceries' API will accept per user
# before returning 429 (see home-assistant/core#179603 — HA core's official
# integration ignores this cap entirely and floods their servers on bulk
# deletes). Keep comfortably under their stated limit of 15. Do not raise
# this without confirming OurGroceries' actual cap hasn't changed.
DELETE_CONCURRENCY = 10

# Service
SERVICE_GET_SUGGESTIONS = "get_suggestions"
