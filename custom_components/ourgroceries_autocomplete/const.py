"""Constants for the OurGroceries Autocomplete integration."""

DOMAIN = "ourgroceries_autocomplete"

# Config entry keys
CONF_USERNAME = "username"
CONF_PASSWORD = "password"

# Cache TTL for the master-list suggestions service. OurGroceries' own
# developer has asked integrations not to hammer their API (see
# home-assistant/core#105700) — the master list changes rarely, so a long
# cache is both correct and polite. Do not lower this without a real reason.
SUGGESTIONS_CACHE_SECONDS = 900  # 15 minutes

# Service
SERVICE_GET_SUGGESTIONS = "get_suggestions"
