"""
Parse reportbuilder.csv and requirements.json in tandem.
Validates that CSV and JSON align; builds in-memory Den/Scout/Adventure model.
"""

import csv
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from loguru import logger

from models import Adventure, Den, Requirement, Scout


@dataclass
class ValidationResult:
    """Result of validate_csv_against_requirements: errors and warnings for tests and callers."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_ok(self) -> bool:
        return len(self.errors) == 0


# --- Validation ---

# Rank header pattern: "Lion", "Lion v2024", "Lion v2018" -> strip version to get canonical rank
RANK_VERSION_RE = re.compile(r"^(.+?)\s+v(\d{4})$", re.IGNORECASE)

# Adventure row: optional prefix like "1a. " or "2b. "
ADVENTURE_PREFIX_RE = re.compile(r"^\s*\d+[a-z]?\.\s*", re.IGNORECASE)

# Requirement row: starts with a number
REQUIREMENT_NUM_RE = re.compile(r"^\s*(\d+)\s*[\.\)]?\s*")

COMPLETED_MARKERS = {"completed", "Approved", "ApprovedAwarded"}
INCOMPLETE_MARKERS = {"In Progress", "Not Started", "Awarded"}
# At the adventure header row, these cell values mean the whole adventure is awarded to the scout
ADVENTURE_AWARDED_MARKERS = {"Awarded", "Approved", "Completed", "ApprovedAwarded", "CompletedAwarded"}


def _normalize_rank_header(label: str, json_ranks: set[str]) -> str | None:
    """
    If label is a rank header (exact rank name or 'Rank vYYYY' with rank in json_ranks),
    return the canonical rank name. Otherwise return None (e.g. adventure/requirement rows).
    """
    s = label.strip()
    if not s:
        return None
    if s in json_ranks:
        return s
    m = RANK_VERSION_RE.match(s)
    if m:
        base = m.group(1).strip()
        return base if base in json_ranks else None
    return None


def _get_json_ranks(requirements_data: dict) -> set[str]:
    """Return set of top-level rank keys from loaded requirements.json."""
    return {k for k in requirements_data if isinstance(requirements_data.get(k), dict)}


def _is_rank_header_row(label: str, json_ranks: set[str]) -> bool:
    """True if the row label is a rank section header (exact rank or rank vYYYY)."""
    return _normalize_rank_header(label, json_ranks) is not None


def _csv_row_labels(csv_path: str | Path) -> list[str]:
    """Yield the first column (row label) for each data row, starting at row index 2."""
    with open(csv_path, newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f)
        rows = list(reader)
    if len(rows) < 3:
        return []
    return [str(row[0]).strip() if row else "" for row in rows[2:]]


def validate_csv_against_requirements(
    csv_path: str | Path,
    json_path: str | Path,
    *,
    json_ranks: set[str] | None = None,
) -> ValidationResult:
    """
    Load CSV and requirements.json, walk CSV row labels, and validate alignment.
    - Rank header rows: must match a rank in JSON (canonical name); log error if missing.
    - Optionally: warn if JSON has a rank that never appears as a CSV header.
    Returns ValidationResult(errors=[], warnings=[]) for programmatic use; also logs via loguru.
    """
    # Avoid mutable default
    result = ValidationResult()

    with open(json_path, encoding="utf-8") as f:
        requirements_data = json.load(f)

    ranks = json_ranks if json_ranks is not None else _get_json_ranks(requirements_data)
    labels = _csv_row_labels(csv_path)

    csv_rank_headers_seen: set[str] = set()

    for raw_label in labels:
        label = raw_label.strip()
        if not label or label.startswith("."):
            continue

        canonical = _normalize_rank_header(label, ranks)
        if canonical is not None:
            # Row is a valid rank header (exact rank or "Rank vYYYY" with rank in JSON)
            csv_rank_headers_seen.add(canonical)
            continue

        # Label looks like "X vYYYY" but X is not in JSON -> error
        m = RANK_VERSION_RE.match(label)
        if m and m.group(1).strip() not in ranks:
            msg = f"requirements.json missing rank for CSV section: {label!r}"
            result.errors.append(msg)
            logger.error(msg)

    for rank in ranks:
        if rank not in csv_rank_headers_seen:
            msg = f"requirements.json has rank {rank!r} but CSV has no section header for it"
            result.warnings.append(msg)
            logger.warning(msg)

    return result


# --- Load requirements.json into Adventure definitions ---


def load_requirements_json(json_path: str | Path) -> dict[str, dict[str, object]]:
    """Load raw requirements.json (rank -> adventure name -> {url, type, requirements})."""
    with open(json_path, encoding="utf-8") as f:
        return json.load(f)


def _adventure_from_entry(name: str, entry: dict[str, object]) -> Adventure:
    """Build one Adventure from a requirements.json entry."""
    reqs = entry.get("requirements") or {}
    if isinstance(reqs, dict):
        requirements = [
            Requirement(id=k, text=v)
            for k, v in sorted(reqs.items(), key=lambda x: (int(x[0]) if x[0].isdigit() else 0, x[0]))
        ]
    else:
        requirements = []
    return Adventure(
        name=name,
        type=entry.get("type", "required"),
        url=entry.get("url"),
        requirements=requirements,
    )


def load_adventures_by_rank(json_path: str | Path) -> dict[str, list[Adventure]]:
    """
    Load requirements.json and return rank -> list of Adventure (with Requirement list).
    Single source of truth for adventure metadata and requirement text.
    """
    data = load_requirements_json(json_path)
    out: dict[str, list[Adventure]] = {}
    for rank, adventures_dict in data.items():
        if not isinstance(adventures_dict, dict):
            continue
        out[rank] = [
            _adventure_from_entry(adv_name, adv_entry)
            for adv_name, adv_entry in adventures_dict.items()
            if isinstance(adv_entry, dict)
        ]
    return out


# --- Normalize adventure label for matching ---


def _normalize_adventure_label(label: str) -> str:
    """Strip optional prefix like '1a. ' and return trimmed label."""
    s = label.strip()
    return ADVENTURE_PREFIX_RE.sub("", s).strip()


def _find_adventure_for_label(
    label: str,
    adventures_by_rank: dict[str, list[Adventure]],
) -> tuple[str, Adventure] | None:
    """
    If the (possibly prefixed) label matches an adventure in any rank, return (rank, Adventure).
    Handles exact name and 'Adventure Name (Rank)' form.
    """
    normalized = _normalize_adventure_label(label)
    for rank, adventures in adventures_by_rank.items():
        for adv in adventures:
            if adv.name == normalized:
                return (rank, adv)
            suffix = f" ({rank})"
            if normalized.endswith(suffix) and normalized[: -len(suffix)].strip() == adv.name:
                return (rank, adv)
            if label.strip() == adv.name:
                return (rank, adv)
    return None


# --- Parse CSV: dens, scouts, requirement completion ---


def _read_csv_rows(csv_path: str | Path):
    """Read CSV and return list of rows (list of cells)."""
    with open(csv_path, newline="", encoding="utf-8", errors="replace") as f:
        return list(csv.reader(f))


def _build_dens_from_header(rows: list[list]) -> list[Den]:
    """Row 0 = scout names, Row 1 = Next Rank per scout. Build one Den per rank with Scout list."""
    if len(rows) < 2:
        return []
    scout_names = [str(c).strip() for c in rows[0]]
    next_ranks = [str(c).strip() for c in rows[1]]
    # Column 0 is empty / "Next Rank"; scouts start at index 1
    den_lists: dict[str, list[Scout]] = {}
    for i in range(1, min(len(scout_names), len(next_ranks))):
        name = scout_names[i]
        rank = next_ranks[i]
        if not name or not rank:
            continue
        if rank not in den_lists:
            den_lists[rank] = []
        den_lists[rank].append(Scout(name=name, next_rank=rank))

    return [Den(name=rank, scouts=scouts) for rank, scouts in den_lists.items()]


def _scouts_by_rank(dens: list[Den]) -> dict[str, list[Scout]]:
    """Map rank -> list of Scout for quick lookup."""
    return {d.name: d.scouts for d in dens}


def _scout_requirement_completion(
    csv_path: str | Path,
    adventures_by_rank: dict[str, list[Adventure]],
    scouts_by_rank: dict[str, list[Scout]],
) -> dict[str, dict[str, dict[str, str]]]:
    """
    Parse CSV from row 2 onward; return scout_name -> adventure_name -> req_id -> 'completed'|'incomplete'.
    Only includes scouts that are in scouts_by_rank and adventures that exist in JSON.
    """
    rows = _read_csv_rows(csv_path)
    if len(rows) < 3:
        return {}

    scout_names = [str(c).strip() for c in rows[0]]
    # Initialize: for each scout in each rank, for each adventure in that rank, all requirements incomplete
    result: dict[str, dict[str, dict[str, str]]] = {}
    for rank, scouts in scouts_by_rank.items():
        for scout in scouts:
            result[scout.name] = {}
            for adv in adventures_by_rank.get(rank, []):
                result[scout.name][adv.name] = {req.id: "incomplete" for req in adv.requirements}

    current_rank: str | None = None
    current_adventure: Adventure | None = None

    for row in rows[3:]:
        if not row:
            continue
        first_col = str(row[0]).strip()

        if not first_col or first_col.startswith("."):
            continue

        # Rank header: skip (do not set current_rank from it)
        json_ranks = set(adventures_by_rank.keys())
        if _is_rank_header_row(first_col, json_ranks):
            continue

        # Try to match as adventure
        match = _find_adventure_for_label(first_col, adventures_by_rank)
        if match:
            current_rank, current_adventure = match
            # Adventure row has per-scout status: if "Awarded" (etc.), mark all requirements complete for that scout
            for i in range(1, min(len(row), len(scout_names))):
                scout_name = scout_names[i]
                if scout_name not in result or current_adventure.name not in result[scout_name]:
                    continue
                if scout_name not in (s.name for s in scouts_by_rank.get(current_rank, [])):
                    continue
                cell = str(row[i]).strip()
                if cell in ADVENTURE_AWARDED_MARKERS:
                    for req_id in result[scout_name][current_adventure.name]:
                        result[scout_name][current_adventure.name][req_id] = "completed"
            continue

        # Unrecognized non-requirement row (e.g. adventure name not in JSON like "BB (Bears)")
        # Clear context so following requirement rows are not attributed to the previous adventure
        if not REQUIREMENT_NUM_RE.match(first_col) and first_col:
            current_adventure = None
            continue

        # Requirement row
        num_match = REQUIREMENT_NUM_RE.match(first_col)
        if num_match and current_rank and current_adventure:
            req_id = num_match.group(1)
            for i in range(1, min(len(row), len(scout_names))):
                scout_name = scout_names[i]
                if scout_name not in result or current_adventure.name not in result[scout_name]:
                    continue
                if scout_name not in (s.name for s in scouts_by_rank.get(current_rank, [])):
                    continue
                # CSV may have more requirement rows than JSON (e.g. different program version); only track known ids
                if req_id not in result[scout_name][current_adventure.name]:
                    continue
                cell = str(row[i]).strip()
                if cell in COMPLETED_MARKERS:
                    result[scout_name][current_adventure.name][req_id] = "completed"
                elif (cell in INCOMPLETE_MARKERS or cell == "") and result[scout_name][current_adventure.name][
                    req_id
                ] != "completed":
                    # Don't overwrite completion already set from adventure-level row (e.g. "Awarded"/"Approved")
                    result[scout_name][current_adventure.name][req_id] = "incomplete"

    return result


def _set_finished_pending(
    dens: list[Den],
    adventures_by_rank: dict[str, list[Adventure]],
    completion: dict[str, dict[str, dict[str, str]]],
) -> None:
    """Mutate each Scout: set finished_adventures, pending_adventures, and pending_incomplete_requirements."""
    for den in dens:
        rank = den.name
        adventures = adventures_by_rank.get(rank, [])
        for scout in den.scouts:
            comp = completion.get(scout.name, {})
            finished: list[Adventure] = []
            pending: list[Adventure] = []
            pending_incomplete: dict[str, list[Requirement]] = {}
            for adv in adventures:
                req_status = comp.get(adv.name, {})
                if not adv.requirements:
                    continue
                if all(req_status.get(r.id) == "completed" for r in adv.requirements):
                    finished.append(adv)
                else:
                    pending.append(adv)
                    incomplete = [r for r in adv.requirements if req_status.get(r.id) != "completed"]
                    pending_incomplete[adv.name] = incomplete
            scout.finished_adventures = finished
            scout.pending_adventures = pending
            scout.pending_incomplete_requirements = pending_incomplete


def parse_advancement_report(
    csv_path: Path,
    json_path: Path,
    skip_validation: bool = False,
) -> list[Den]:
    """
    Load requirements.json, optionally run validate_csv_against_requirements, then parse CSV
    and return list of Dens with Scouts and their finished/pending adventures.
    """
    if not skip_validation:
        validate_csv_against_requirements(csv_path, json_path)

    adventures_by_rank = load_adventures_by_rank(json_path)
    rows = _read_csv_rows(csv_path)
    dens = _build_dens_from_header(rows)
    scouts_by_rank = _scouts_by_rank(dens)
    completion = _scout_requirement_completion(csv_path, adventures_by_rank, scouts_by_rank)
    _set_finished_pending(dens, adventures_by_rank, completion)
    return dens
