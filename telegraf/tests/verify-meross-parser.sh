#!/bin/sh
set -eu

tests_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
output=$(docker run --rm -v "$tests_dir:/tests:ro" telegraf:1.39.2-alpine \
  telegraf --config /tests/meross-parser.conf --test 2>&1)
printf '%s\n' "$output"

printf '%s\n' "$output" | grep -q 'meross_thermostat,device_id=0123456789abcdef0123456789abcdef'
printf '%s\n' "$output" | grep -q 'model=mts200b'
printf '%s\n' "$output" | grep -q 'current_temperature_c=21.1'
printf '%s\n' "$output" | grep -q 'target_temperature_c=22.5'
printf '%s\n' "$output" | grep -q 'enabled=1i'
printf '%s\n' "$output" | grep -q 'active=0i'
printf '%s\n' "$output" | grep -q '1785844800000000000$'
