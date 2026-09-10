#!/bin/sh
set -eu

# Rebuild the QLever index from the DTS pipeline output and (re)start the QLever server.
# Run this on the HOST from the repository root:
#
#   ./scripts/reindex-qlever.sh [OUTPUT_PREFIX]
#
# OUTPUT_PREFIX defaults to local_hwgw, matching DTS_OUTPUT_PREFIX in scripts/Taskfile.yml.

PREFIX="${1:-local_hwgw}"

FILES=""
for name in "${PREFIX}_combined.ttl" "${PREFIX}_rds_links.ttl"; do
  if docker compose exec -T qlever sh -c "[ -f /data/$name ]"; then
    FILES="$FILES -f /data/$name"
  else
    echo "Skipping missing /data/$name" >&2
  fi
done

# x3ml-mapped register data
for name in persons/persons.ttl organizations/organizations.ttl places/places.ttl objects/objects.ttl; do
  if docker compose exec -T qlever sh -c "[ -f /mapping-output/$name ]"; then
    FILES="$FILES -f /mapping-output/$name"
  else
    echo "Skipping missing /mapping-output/$name" >&2
  fi
done

if [ -z "$FILES" ]; then
  echo "No input files found under external/hwgw-dts/data/output for prefix '$PREFIX'." >&2
  exit 1
fi

echo "Building QLever index from:$FILES"
# shellcheck disable=SC2086
docker compose exec -T qlever sh -c "cd /index && qlever-index $FILES -F ttl --index-basename hwgw -m 4G --parallel-parsing true | tee hwgw.index-log.txt"

echo "Requesting QLever server restart..."
docker compose exec -T qlever touch /index/.restart-qlever
sleep 3
echo "Done. Query the SPARQL endpoint at http://localhost:<PORT_QLEVER> (see .env, default 7011)."
