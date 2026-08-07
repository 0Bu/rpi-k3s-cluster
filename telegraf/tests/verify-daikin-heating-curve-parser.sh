#!/bin/sh
set -eu

tests_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
output=$(docker run --rm -v "$tests_dir:/tests:ro" telegraf:1.39.2-alpine \
  telegraf --config /tests/heating-curve-parser.conf --test 2>&1)
printf '%s\n' "$output"

printf '%s\n' "$output" | grep -q 'daikin_heating_curve,device=daikin-altherma-esp32'
printf '%s\n' "$output" | grep -q 'schema_version=1'
printf '%s\n' "$output" | grep -q 'room_temperature_c=22.6'
printf '%s\n' "$output" | grep -q 'room_control_eligible=1'
printf '%s\n' "$output" | grep -q 'room_counters_rejections=1'
printf '%s\n' "$output" | grep -q 'diagnosis_gates_plant_active=0'
printf '%s\n' "$output" | grep -q 'diagnosis_last_sample_sequence=0'
printf '%s\n' "$output" | grep -q 'diagnosis_counters_evaluations=75'

if printf '%s\n' "$output" | grep -qE \
  'source_id|diagnosis_room_evidence_current_error_k|diagnosis_last_sample_(room_error_k|unix_s)'; then
  echo 'unexpected text or null-valued field in numeric metric' >&2
  exit 1
fi
