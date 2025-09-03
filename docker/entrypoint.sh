#!/bin/bash
set -e
umask 002

if [ "${1:0:1}" = '-' ]; then
    set -- python -u -m network-monitor "$@"
fi

echo "RUN: $@"
exec "$@"
