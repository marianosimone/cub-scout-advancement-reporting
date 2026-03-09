"""Tests for full advancement report parser (Dens, Scouts, finished/pending adventures)."""

from pathlib import Path

from parser import parse_advancement_report

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_parse_minimal_returns_dens_with_scouts():
    """Full parse on minimal CSV/JSON returns one Den (Lion) with two Scouts."""
    csv_path = FIXTURES_DIR / "minimal_csv_valid.csv"
    json_path = FIXTURES_DIR / "minimal_requirements.json"
    dens = parse_advancement_report(csv_path, json_path, skip_validation=True)
    assert len(dens) == 1
    assert dens[0].name == "Lion"
    assert len(dens[0].scouts) == 2
    names = {s.name for s in dens[0].scouts}
    assert "Scout One" in names and "Scout Two" in names


def test_parse_minimal_scout_has_finished_pending():
    """Scout Two has one requirement Approved in CSV -> Bobcat (Lion) may be finished or pending."""
    csv_path = FIXTURES_DIR / "minimal_csv_valid.csv"
    json_path = FIXTURES_DIR / "minimal_requirements.json"
    dens = parse_advancement_report(csv_path, json_path, skip_validation=True)
    lion_den = dens[0]
    scout_two = next(s for s in lion_den.scouts if s.name == "Scout Two")
    # Bobcat (Lion) has 2 requirements; only req 1 is Approved, so adventure is pending
    assert len(scout_two.pending_adventures) >= 1
    assert any(a.name == "Bobcat (Lion)" for a in scout_two.pending_adventures)
