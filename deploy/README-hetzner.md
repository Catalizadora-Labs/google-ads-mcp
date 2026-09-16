# Lo que corre en Hetzner (rama `hetzner`)

`/opt/google-ads-mcp` en `catalizadora-prod` (5.78.223.64) · `google-ads-mcp.service` · streamable-http en
`100.103.115.33:5071` (Tailscale) · `uv run main.py --groups all` · credenciales en `env/google-ads.yaml`
(ignorado por git; nunca en el repo).

Diferencias con upstream (`promobase/google-ads-mcp`, rama `main`):
- **API v24** (upstream sigue en v20, que Google bloqueó en jun-2026; v21 en ago; v22 caerá). `sed googleads.vN`
  en `src/**.py` + `src/sdk_client.py`. v23 importa los 191 módulos limpio; **v24 NO**: quita `InsightsAudienceAttributeGroup` y rompe `audience_insights_service` (medido 16-sep-2026 con import REAL desde fuera del checkout).
- `main.py` honra `MCP_TRANSPORT` / `MCP_HOST` / `MCP_PORT` (upstream hardcodea stdio).
- `search_execute_query` ya **no manda `page_size`** (la API lo rechaza desde v22: «Setting the page size is not supported»).
- `audience_insights_service.py`: `BasicInsightsAudience → InsightsAudience` (rename de la API).
- `funnel_check.py`: reemplazado por `elhilar-nurture/scripts/embudo_ads.py`; queda por historia.

Aplicar en el host: `ssh root@5.78.223.64 'bash -s' < deploy/aplicar-en-hetzner.sh`.
Cuando Google bloquee v23: subir la lib (`uv lock --upgrade-package google-ads`), mirar qué versiones trae
(`ls .venv/lib/python*/site-packages/google/ads/googleads/`), `sed` a la nueva, probar imports, commit, aplicar.
El candado `~/.claude/skills/google-ads/gates/check.sh` detecta `UNSUPPORTED_VERSION` con una GAQL real.
