#!/bin/bash
set -e

# Fix ownership on mounted volumes (they may be owned by root on host)
chown darwin:darwin /backup 2>/dev/null || true

# Drop to darwin user and exec the CMD
exec gosu darwin "$@"
