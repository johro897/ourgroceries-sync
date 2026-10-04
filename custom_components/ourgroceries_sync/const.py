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

# Cache TTL for the categoryId -> name lookup used by get_categories.
# Category names change about as rarely as the master list, so reuse the
# same on-demand + long-cache approach — no background polling for this
# either.
CATEGORY_CACHE_SECONDS = 900  # 15 minutes

# Services
SERVICE_GET_SUGGESTIONS = "get_suggestions"
SERVICE_GET_CATEGORIES = "get_categories"
SERVICE_ADD_ITEM = "add_item"
