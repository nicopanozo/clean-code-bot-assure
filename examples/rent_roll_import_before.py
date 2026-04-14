# import_rentroll.py — used by property onboarding, frank built this in a hurry

import csv
import datetime


def proc(fn, propid):
    f = open(fn, "r")
    r = csv.DictReader(f)
    rows = []
    for x in r:
        rows.append(x)
    f.close()
    out = []
    errs = []
    for i in range(len(rows)):
        row = rows[i]
        try:
            unit = row["Unit"].strip().upper()
        except:
            errs.append({"line": i + 2, "msg": "no unit"})
            continue
        try:
            rent = float(row["Rent"].replace("$", "").replace(",", ""))
        except:
            errs.append({"line": i + 2, "msg": "bad rent"})
            continue
        sd = row.get("Start") or row.get("LeaseStart")
        if not sd:
            errs.append({"line": i + 2, "msg": "no start"})
            continue
        try:
            dt = datetime.datetime.strptime(sd, "%m/%d/%Y")
        except:
            try:
                dt = datetime.datetime.strptime(sd, "%Y-%m-%d")
            except:
                errs.append({"line": i + 2, "msg": "bad date"})
                continue
        nm = (row.get("Tenant") or "").strip()
        out.append(
            {
                "property_id": propid,
                "unit_code": unit,
                "monthly_rent_cents": int(rent * 100),
                "lease_start": dt.date().isoformat(),
                "tenant_display_name": nm or None,
            }
        )
    return {"ok": out, "errors": errs}


def validate_only(fn):
    return proc(fn, 0)
