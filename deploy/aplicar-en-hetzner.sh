#!/usr/bin/env bash
# aplicar-en-hetzner.sh — trae la rama `hetzner` de Catalizadora-Labs/google-ads-mcp al checkout vivo
# (/opt/google-ads-mcp), reinicia el servicio y VERIFICA con una GAQL real. Idempotente.
#   ssh root@5.78.223.64 'bash -s' < deploy/aplicar-en-hetzner.sh
# Por qué existe: /opt/google-ads-mcp llevaba 91 archivos modificados sin commit (v20→v21→v22 a mano).
# Lo que corre tiene que estar en un repo; la rama `hetzner` del fork ES lo que corre.
set -euo pipefail
cd /opt/google-ads-mcp
git remote get-url labs >/dev/null 2>&1 || git remote add labs https://github.com/Catalizadora-Labs/google-ads-mcp.git
git fetch -q labs
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then git stash push -q -m "pre-hetzner-$(date +%Y%m%d-%H%M%S)"; fi
git checkout -q -B hetzner labs/hetzner
find src -name __pycache__ -type d -prune -exec rm -rf {} +
systemctl restart google-ads-mcp.service; sleep 8
systemctl is-active google-ads-mcp.service
journalctl -u google-ads-mcp.service --since '-40 sec' --no-pager | grep -iE 'error|traceback|Registered tools' | tail -3 || true
H=$(mktemp); curl -s --max-time 15 -D "$H" -o /dev/null -X POST http://100.103.115.33:5071/mcp -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"aplicar","version":"0"}}}'
SID=$(grep -i '^mcp-session-id' "$H" | awk '{print $2}' | tr -d '\r'); rm -f "$H"
curl -s --max-time 10 -X POST http://100.103.115.33:5071/mcp -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' -H "mcp-session-id: $SID" -d '{"jsonrpc":"2.0","method":"notifications/initialized"}' >/dev/null
R=$(curl -s --max-time 30 -X POST http://100.103.115.33:5071/mcp -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' -H "mcp-session-id: $SID" -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"search_execute_query","arguments":{"customer_id":"8813881007","query":"SELECT customer.id FROM customer LIMIT 1"}}}')
if echo "$R" | grep -q '8813881007' && ! echo "$R" | grep -q '"isError":true'; then echo "✓ search_execute_query contesta (page_size ya no se manda, API v23)"; else echo "✗ la GAQL falló: $(echo "$R" | cut -c1-300)"; exit 1; fi
