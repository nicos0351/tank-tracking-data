"""Checks fuel_prices.json before it is published.

    python validate.py fuel_prices.json [--base previous.json]

Prints every problem. ERRORs stop publishing (exit code 1); WARNINGs are
for the reviewer to look at. With --base (the version now live), it also
checks that dataVersion went up and that no month was deleted.
"""

import json
import sys
from datetime import date

GRADES = ("93", "95")
REGIONS = ("inland", "coastal")
DIESEL = ("50ppm", "500ppm")

# Plausible rand per litre for petrol, and the largest believable change
# from one month to the next (the biggest so far was about R2.60 in 2022).
MIN_PRICE, MAX_PRICE = 10.0, 60.0
MAX_MONTHLY_CHANGE = 5.0


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    path = argv[1]
    base_path = argv[argv.index("--base") + 1] if "--base" in argv else None

    errors, warnings = [], []

    def err(msg):
        errors.append(msg)

    def warn(msg):
        warnings.append(msg)

    try:
        data = json.load(open(path, encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: {path} is not valid JSON: {e}")
        return 1

    if data.get("format") != 1:
        err('"format" must be 1 (only an app release can change the layout).')
    version = data.get("dataVersion")
    if not isinstance(version, int) or version < 1:
        err('"dataVersion" must be a whole number of 1 or more.')
    updated = _date(data.get("updated"))
    if updated is None:
        err('"updated" must be a date like "2026-11-04".')

    changes = data.get("changes")
    if not isinstance(changes, list) or not changes:
        err('"changes" must list at least one {version, date, summary}.')
    else:
        for c in changes:
            if not (isinstance(c, dict) and isinstance(c.get("version"), int)
                    and _date(c.get("date")) and c.get("summary")):
                err(f"Change entry is incomplete: {c}")
        if isinstance(version, int) and not any(
                isinstance(c, dict) and c.get("version") == version
                for c in changes):
            err(f'Add a "changes" entry for dataVersion {version}.')

    tables = data.get("tables")
    if not isinstance(tables, list) or not tables:
        err('"tables" must list at least one month.')
        tables = []

    previous = None
    for t in tables:
        label = t.get("effectiveFrom", "?")
        when = _date(t.get("effectiveFrom"))
        if when is None:
            err(f'{label}: "effectiveFrom" must be a date like "2026-11-04".')
            continue
        if when.weekday() != 2:
            warn(f"{label}: is not a Wednesday. Prices normally change on "
                 "the first Wednesday of the month; check the date.")
        elif when.day > 7:
            warn(f"{label}: is not the first Wednesday of the month; check "
                 "the date.")
        if previous and when <= previous[0]:
            err(f"{label}: months must be in date order, oldest first.")

        petrol = t.get("petrol")
        prices = {}
        if not isinstance(petrol, dict):
            err(f'{label}: "petrol" is missing.')
        else:
            for g in GRADES:
                for r in REGIONS:
                    p = (petrol.get(g) or {}).get(r)
                    if not isinstance(p, (int, float)):
                        err(f"{label}: petrol {g} {r} price is missing.")
                        continue
                    if not MIN_PRICE <= p <= MAX_PRICE:
                        err(f"{label}: petrol {g} {r} R{p} is outside "
                            f"R{MIN_PRICE:.0f} to R{MAX_PRICE:.0f}.")
                    if round(p, 2) != p:
                        err(f"{label}: petrol {g} {r} R{p} has more than 2 "
                            "decimals.")
                    prices[(g, r)] = p
            for r in REGIONS:
                if (("93", r) in prices and ("95", r) in prices
                        and prices[("93", r)] > prices[("95", r)]):
                    err(f"{label}: 93 {r} costs more than 95 {r}; are they "
                        "swapped?")
            for g in GRADES:
                if ((g, "inland") in prices and (g, "coastal") in prices
                        and prices[(g, "coastal")] > prices[(g, "inland")]):
                    err(f"{label}: {g} coastal costs more than inland; are "
                        "they swapped?")
            if previous:
                for key, p in prices.items():
                    before = previous[1].get(key)
                    if before is not None and abs(p - before) > MAX_MONTHLY_CHANGE:
                        err(f"{label}: petrol {key[0]} {key[1]} changed by "
                            f"R{p - before:+.2f} in one month; check it.")

        diesel = t.get("dieselWholesaleChange")
        if diesel is not None:
            if not isinstance(diesel, dict):
                err(f'{label}: "dieselWholesaleChange" must be like '
                    '{"50ppm": -1.2, "500ppm": -1.1}.')
            else:
                for k, v in diesel.items():
                    if k not in DIESEL:
                        err(f'{label}: unknown diesel grade "{k}" (use '
                            '"50ppm" or "500ppm").')
                    elif not isinstance(v, (int, float)) or abs(v) > MAX_MONTHLY_CHANGE:
                        err(f"{label}: diesel {k} change {v} is not a "
                            "believable rand-per-litre change.")

        sources = t.get("sources")
        if (not isinstance(sources, list) or not sources
                or not all(isinstance(s, str) and s.startswith("https://")
                           for s in sources)):
            err(f'{label}: "sources" must list the https links the prices '
                "came from.")
        previous = (when, prices)

    if base_path:
        try:
            base = json.load(open(base_path, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            base = {}
        if base and base != data:
            if isinstance(version, int) and version <= (base.get("dataVersion") or 0):
                err(f'"dataVersion" must go up: it is {version}, the live file '
                    f'has {base.get("dataVersion")}.')
            old = {t.get("effectiveFrom"): t for t in base.get("tables", [])}
            new = {t.get("effectiveFrom"): t for t in tables}
            for when in old:
                if when not in new:
                    err(f"Month {when} was deleted; months are never removed.")
                elif old[when].get("petrol") != new[when].get("petrol"):
                    warn(f"Month {when}: petrol prices were changed. Fine for "
                         "a correction; check the source.")

    for w in warnings:
        print(f"WARNING: {w}")
    for e in errors:
        print(f"ERROR: {e}")
    if not errors:
        print(f"OK: {path} has {len(tables)} months, dataVersion {version}.")
    return 1 if errors else 0


def _date(text):
    try:
        return date.fromisoformat(text)
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    sys.exit(main(sys.argv))
