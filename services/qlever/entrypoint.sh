#!/bin/sh
set -eu

RESTART_FLAG="/index/.restart-qlever"
INDEX_READY_FILE="/index/hwgw.meta-data.json"
STARTING_FLAG="/tmp/qlever-starting"
DATASET_NAME="hwgw"
PORT="7001"
START_ARGS="
  --name ${DATASET_NAME}
  --description \"HWGW Qlever instance\"
  --system native
  --persist-updates
  --port ${PORT}
  --access-token ${QLEVER_ACCESS_TOKEN}
"

is_index_ready() {
  [ -f "$INDEX_READY_FILE" ]
}

is_server_running() {
  pgrep -f "qlever-server -i ${DATASET_NAME}( |$)" >/dev/null 2>&1
}

start_server() {
  if ! is_index_ready; then
    return 0
  fi

  if is_server_running || [ -f "$STARTING_FLAG" ]; then
    return 0
  fi

  touch "$STARTING_FLAG"
  (
    qlever start $START_ARGS --no-warmup || true
    rm -f "$STARTING_FLAG"
  ) &
}

stop_server() {
  rm -f "$STARTING_FLAG"
  qlever stop --name "$DATASET_NAME" --port "$PORT" --no-containers || true
}

restart_server() {
  stop_server

  for _ in 1 2 3 4 5 6 7 8 9 10; do
    if ! is_server_running; then
      break
    fi
    sleep 1
  done

  start_server
}

handle_term() {
  stop_server
  exit 0
}

trap handle_term INT TERM

rm -f "$RESTART_FLAG"
rm -f "$STARTING_FLAG"

while true; do
  if [ -f "$RESTART_FLAG" ]; then
    echo "Restart flag detected, restarting QLever server..."
    rm -f "$RESTART_FLAG"
    restart_server
  else
    start_server
  fi

  sleep 2
done
