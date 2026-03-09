"""Unit tests for CSV vs requirements.json validation (Step 1 only)."""

from pathlib import Path

from parser import ValidationResult, validate_csv_against_requirements

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_csv_rank_header_matches_json_rank_no_errors():
    """CSV rank headers (Lion, Lion v2024) match rank in JSON -> no errors."""
    csv_path = FIXTURES_DIR / "minimal_csv_valid.csv"
    json_path = FIXTURES_DIR / "minimal_requirements.json"
    result = validate_csv_against_requirements(csv_path, json_path)
    assert result.is_ok, result.errors
    assert len(result.errors) == 0


def test_csv_rank_header_missing_in_json_logs_error():
    """CSV has rank section (UnknownRank, UnknownRank v2030) not in JSON -> errors."""
    csv_path = FIXTURES_DIR / "csv_unknown_rank.csv"
    json_path = FIXTURES_DIR / "minimal_requirements.json"
    result = validate_csv_against_requirements(csv_path, json_path)
    assert not result.is_ok
    assert len(result.errors) >= 1
    assert any("UnknownRank" in e for e in result.errors)


def test_json_rank_not_in_csv_logs_warning():
    """JSON has rank Lion but CSV has no Lion section header -> warning."""
    csv_path = FIXTURES_DIR / "csv_no_lion_section.csv"
    json_path = FIXTURES_DIR / "minimal_requirements.json"
    result = validate_csv_against_requirements(csv_path, json_path)
    assert len(result.warnings) >= 1
    assert any("Lion" in w for w in result.warnings)


def test_validation_result_is_ok():
    """ValidationResult.is_ok is True when no errors."""
    assert ValidationResult(errors=[], warnings=[]).is_ok
    assert ValidationResult(errors=[], warnings=["foo"]).is_ok
    assert not ValidationResult(errors=["bar"], warnings=[]).is_ok
