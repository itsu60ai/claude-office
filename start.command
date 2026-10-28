#!/bin/bash
# Opens the office. Keep this window open while you use it; close it to stop.
cd "$(dirname "$0")"
PORT=8765
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 was not found. Install it from https://www.python.org/downloads/ and run this again."
  echo "לא נמצא Python 3. אפשר להתקין מ-https://www.python.org/downloads/ ולהריץ שוב."
  read -r -p "Press Enter to close"
  exit 1
fi
(sleep 1; open "http://127.0.0.1:$PORT") &
python3 server.py "$PORT"
