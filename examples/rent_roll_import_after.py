"""
Rent-roll CSV normalization for property onboarding.

Vendor files vary by column naming and date formatting; this module normalizes rows into a
stable structure suitable for downstream validation and bulk insert into the leasing schema.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RentRollRow:
    """Canonical representation of one imported rent-roll line."""

    property_id: int
    unit_code: str
    monthly_rent_cents: int
    lease_start: date
    tenant_display_name: str | None


@dataclass(frozen=True)
class ImportIssue:
    """Non-fatal parse problem tied to a human-readable spreadsheet line number (1-based header)."""

    line_number: int
    message: str


def _parse_money_to_cents(raw: str) -> int:
    cleaned = raw.replace("$", "").replace(",", "").strip()
    amount = float(cleaned)
    return int(round(amount * 100))


def _parse_start_date(raw: str) -> date:
    raw = raw.strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unsupported date format: {raw!r}")


def parse_rent_roll_csv(file_path: str | Path, property_id: int) -> dict[str, Any]:
    """
    Read a CSV rent roll and return normalized rows plus a sidecar list of row-level issues.

    Parameters
    ----------
    file_path:
        Path or string path to the vendor CSV on disk.
    property_id:
        Internal property identifier all rows should be stamped with.

    Returns
    -------
    dict
        ``{"ok": list[RentRollRow], "errors": list[ImportIssue]}`` where ``ok`` contains only
        fully valid rows.
    """
    issues: list[ImportIssue] = []
    normalized: list[RentRollRow] = []

    path = Path(file_path)
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for idx, row in enumerate(reader):
            spreadsheet_line = idx + 2  # account for header row

            try:
                unit_code = row["Unit"].strip().upper()
            except (KeyError, AttributeError):
                issues.append(ImportIssue(spreadsheet_line, "no unit"))
                continue

            try:
                monthly_rent_cents = _parse_money_to_cents(row["Rent"])
            except (KeyError, ValueError, AttributeError):
                issues.append(ImportIssue(spreadsheet_line, "bad rent"))
                continue

            start_raw = row.get("Start") or row.get("LeaseStart")
            if not start_raw or not str(start_raw).strip():
                issues.append(ImportIssue(spreadsheet_line, "no start"))
                continue

            try:
                lease_start = _parse_start_date(str(start_raw))
            except ValueError:
                issues.append(ImportIssue(spreadsheet_line, "bad date"))
                continue

            tenant = (row.get("Tenant") or "").strip() or None

            normalized.append(
                RentRollRow(
                    property_id=property_id,
                    unit_code=unit_code,
                    monthly_rent_cents=monthly_rent_cents,
                    lease_start=lease_start,
                    tenant_display_name=tenant,
                )
            )

    return {
        "ok": [
            {
                "property_id": r.property_id,
                "unit_code": r.unit_code,
                "monthly_rent_cents": r.monthly_rent_cents,
                "lease_start": r.lease_start.isoformat(),
                "tenant_display_name": r.tenant_display_name,
            }
            for r in normalized
        ],
        "errors": [{"line": i.line_number, "msg": i.message} for i in issues],
    }


def validate_only(file_path: str | Path) -> dict[str, Any]:
    """Parse pass with ``property_id=0`` reserved for dry-run UI workflows."""
    return parse_rent_roll_csv(file_path, 0)
