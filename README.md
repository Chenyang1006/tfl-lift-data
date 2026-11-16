# TfL lift disruption collector

Collects a snapshot of TfL's open lift disruption data
(`https://api.tfl.gov.uk/Disruptions/Lifts/v2/`) every 10 minutes,
using GitHub Actions, for a student research project on wheelchair
users and lift breakdowns on the London Underground.

## What is saved

| File | What it holds |
|---|---|
| `data/log.csv` | One row per run: time (UTC), HTTP status, success, number of disruptions, content hash, whether it changed, error |
| `data/snapshots/*.json` | The full API response, saved only when it changed since the last snapshot |
| `data/last_hash.txt` | Internal: the hash of the last saved snapshot |

All times are UTC. The data is TfL open data
(Powered by TfL Open Data, contains OS data © Crown copyright and database rights).

## Run it by hand

```
python3 collect_lifts.py
```
