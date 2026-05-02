#!/bin/sh
mkdir -p /app/.next /app/node_modules
chown -R node:node /app/.next /app/node_modules
exec su-exec node "$@"