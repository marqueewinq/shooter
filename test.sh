#!/bin/bash

HOST=${1:-web}
PORT=${2:-8000}
OUTPUT_DIR=${3:-"./output"}

# -- Run the query ---
GROUP_RESULT_ID=$(curl -f -s -XPOST "http://$HOST:$PORT/take_screenshots/" \
     -H "Content-Type: application/json" \
     -d '
{
    "default_config": {
        "browser": "chrome",
        "device": "IPHONE_X",
        "wait_after_load": 10,
        "wait_for_selector_timeout": 10,
        "scroll_pause_time": 0.1,
        "full_page_screenshot": true
    },
    "sites": [
        "https://www.iana.org/domains/reserved",
        {
            "url": "https://www.iana.org/domains/reserved",
            "actions": [
                {
                    "kind": "scroll_down",
                    "how_much": 500
                }
            ]
        }
    ]
}
' | jq -r '.group_result_id')

# --- Fetching the result ---

echo "Scheduled tasks with Group Result ID: $GROUP_RESULT_ID"
if [ "$GROUP_RESULT_ID" == "" ]; then
  exit 1
fi

READY=false
while [ "$READY" != "true" ]; do
  echo "Checking progress for Group Result ID: $GROUP_RESULT_ID"
  RESULT=$(curl -s "http://$HOST:$PORT/take_screenshots/$GROUP_RESULT_ID")
  echo "$RESULT"
  echo ""
  READY=$(echo "$RESULT" | jq -r '.ready')
  sleep 3
done

# --- Download the zip ---

ZIP_PATH="${OUTPUT_DIR}/${GROUP_RESULT_ID}.zip"
touch "${ZIP_PATH}"
curl -f -o "${ZIP_PATH}"  "http://$HOST:$PORT/take_screenshots/$GROUP_RESULT_ID/zip"
