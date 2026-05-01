#!/bin/sh
mkdir -p /app/.next
chown -R node:node /app/.next
exec su-exec node "$@"