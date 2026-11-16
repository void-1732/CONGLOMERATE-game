#!/bin/sh
cd "$(dirname "$0")" || exit 1
echo "CONGLOMERATE v0.4: open http://127.0.0.1:8765/index.html"
exec python3 -m http.server 8765 --bind 127.0.0.1
