# Tank & Tracking: fuel prices

This repository holds the monthly South African fuel prices for the
**Tank & Tracking** app. GitHub Pages publishes them at:

**https://nicos0351.github.io/tank-tracking-data/fuel_prices.json**

The app checks that address in the background when it opens (at most every
few hours, more often in the week before a price day). When the file has a
month the phone doesn't know yet, the app starts using it: the price day
alert appears on the home screen, and fill-ups use the new price from the
day it starts. No app update is needed.

## What's in `fuel_prices.json`

| Field | What it is |
|---|---|
| `format` | File layout version. Leave at `1`; only an app release can change it. |
| `dataVersion` | **Raise by 1 every time you change anything.** |
| `updated` | Date of this version, e.g. `"2026-11-04"`. |
| `changes` | List of `{version, date, summary}`, one per version. |
| `tables` | One entry per month, oldest first. |

A month looks like this:

```json
{
  "effectiveFrom": "2026-11-04",
  "petrol": {
    "93": {"inland": 29.87, "coastal": 29.08},
    "95": {"inland": 30.24, "coastal": 29.37}
  },
  "dieselWholesaleChange": {"50ppm": -1.20, "500ppm": -1.10},
  "sources": ["https://..."]
}
```

- `effectiveFrom`: the day the prices start (00:01, normally the first
  Wednesday of the month).
- `petrol`: the regulated pump prices in rand per litre, Gauteng (inland)
  and coastal.
- `dieselWholesaleChange`: the change in the diesel wholesale price in rand
  per litre (negative is cheaper). Diesel pump prices are not regulated, so
  the app only shows this as a guide. Leave it out if unknown.
- `sources`: the pages the figures came from. Use the official
  announcement where possible, and a second source to cross-check.
- Never delete a month. To correct a figure, change it, raise
  `dataVersion` and say so in `changes`.

## How updates happen

1. **Automatic check.** Around each price day (from the 25th of the month
   to the 6th of the next) a scheduled Claude task looks for the official
   announcement. When it finds a new month, it opens a **pull request** with
   the figures and two sources. It never publishes anything by itself.
2. **You review.** Open the pull request, compare the figures with the
   sources, and check the **"Check fuel_prices.json"** result: green means
   the file is valid.
3. **Merge to publish.** Click *Merge*. The **"Publish fuel_prices.json"**
   step checks the file again and publishes it within a few minutes. If the
   check fails, nothing is published and the previous prices stay live.

Merge on the day the pull request appears, so the price day alert reaches
phones before the Wednesday.

You can also edit `fuel_prices.json` in GitHub's web editor (pencil icon):
add the month, raise `dataVersion`, add a `changes` entry and commit. The
same check runs.

## Safety checks

`validate.py` runs on every pull request and push, and again before
publishing. It rejects:

- missing prices, prices outside R10 to R60, more than 2 decimals;
- 93 dearer than 95, or coastal dearer than inland (swapped figures);
- a change of more than R5 a litre in one month (a typing slip);
- months out of date order, missing sources, a deleted month;
- a `dataVersion` that didn't go up.

It warns when a date is not the first Wednesday of the month, or when an
earlier month's prices were changed.

The app checks the file too: if the download fails or the file looks
wrong, it keeps the prices it has.

Run the check yourself with `python validate.py fuel_prices.json`.
