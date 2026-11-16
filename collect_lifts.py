#!/usr/bin/env python3
"""
Collect snapshots of TfL lift disruptions for later analysis.

Every run:
  1. calls TfL's open API (Disruptions/Lifts/v2), retrying on failure
  2. appends one row to data/log.csv (time, status, number of items, ...)
  3. saves the full response to data/snapshots/ ONLY when it has changed
     since the last saved snapshot (so the repository stays small)

The raw response is saved exactly as received, so no information is lost
even if we don't yet know every field in TfL's format.

Optional: set the environment variable TFL_APP_KEY to use a TfL API key.
For testing without internet: python3 collect_lifts.py --from-file sample.json
"""

import csv
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

API_URL = "https://api.tfl.gov.uk/Disruptions/Lifts/v2/"
DATA_DIR = "data"
SNAPSHOT_DIR = os.path.join(DATA_DIR, "snapshots")
LOG_FILE = os.path.join(DATA_DIR, "log.csv")
LAST_HASH_FILE = os.path.join(DATA_DIR, "last_hash.txt")
LOG_HEADER = ["retrieved_at_utc", "http_status", "ok", "n_items",
              "content_hash", "changed", "error"]


def fetch(url, retries=2, timeout=30):
    """Return (http_status, parsed_json_or_None, error_message)."""
    key = os.environ.get("TFL_APP_KEY", "").strip()
    if key:
        url += ("&" if "?" in url else "?") + "app_key=" + key

    status, error = 0, ""
    for attempt in range(retries + 1):
        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": "lift-status-research/1.0",
                         "Accept": "application/json"},
            )
            with urllib.request.urlopen(request, timeout=timeout) as response:
                status = response.status
                body = response.read().decode("utf-8")
            return status, json.loads(body), ""
        except urllib.error.HTTPError as e:
            status, error = e.code, f"HTTP {e.code}"
        except Exception as e:  # timeouts, bad JSON, network errors
            status, error = 0, f"{type(e).__name__}: {e}"
        if attempt < retries:
            time.sleep(5 * (attempt + 1))
    return status, None, error


def count_items(data):
    """Number of disruptions if the response is a list; otherwise blank."""
    return len(data) if isinstance(data, list) else ""


def append_log(row):
    new_file = not os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(LOG_HEADER)
        writer.writerow(row)


def main():
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    now_iso = now.isoformat().replace("+00:00", "Z")

    if len(sys.argv) == 3 and sys.argv[1] == "--from-file":
        with open(sys.argv[2], encoding="utf-8") as f:
            status, data, error = 200, json.load(f), ""
    else:
        status, data, error = fetch(API_URL)

    if data is None:
        append_log([now_iso, status, False, "", "", False, error])
        print(f"{now_iso}  FAILED  {error}")
        return

    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
    content_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]

    last_hash = ""
    if os.path.exists(LAST_HASH_FILE):
        with open(LAST_HASH_FILE, encoding="utf-8") as f:
            last_hash = f.read().strip()
    changed = content_hash != last_hash

    if changed:
        filename = now.strftime("%Y-%m-%dT%H-%M-%SZ") + f"_{content_hash[:8]}.json"
        with open(os.path.join(SNAPSHOT_DIR, filename), "w", encoding="utf-8") as f:
            json.dump({"retrieved_at_utc": now_iso, "data": data}, f,
                      ensure_ascii=False, indent=1)
        with open(LAST_HASH_FILE, "w", encoding="utf-8") as f:
            f.write(content_hash)

    n_items = count_items(data)
    append_log([now_iso, status, True, n_items, content_hash, changed, ""])
    print(f"{now_iso}  OK  items={n_items}  changed={changed}")


if __name__ == "__main__":
    main()
