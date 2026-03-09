"""Main entry: load CSV + JSON via parser, validate, print dens/scouts, and generate PDFs."""

import sys
from pathlib import Path

from loguru import logger

from parser import parse_advancement_report, validate_csv_against_requirements
from scout_report_pdf import build_scout_report_pdf, safe_filename

OUTPUT_DIR = Path("output")
LOGOS_DIR = Path("logos")


def main() -> None:
    # So loguru messages show up when stderr is not visible (e.g. IDE output panel)
    logger.remove()
    logger.add(sys.stdout, level="WARNING", format="<level>{level: <8}</level> | {message}")
    csv_path = Path("reportbuilder.csv")
    json_path = Path("requirements.json")

    if not csv_path.exists():
        raise SystemExit(f"CSV not found: {csv_path}")
    if not json_path.exists():
        raise SystemExit(f"JSON not found: {json_path}")

    # Validate first; abort on any validation error and show mismatches
    result = validate_csv_against_requirements(csv_path, json_path)
    if result.errors:
        print("Validation failed (CSV vs requirements.json mismatch):")
        for e in result.errors:
            print(f"  ERROR: {e}")
        sys.exit(1)
    if result.warnings:
        for w in result.warnings:
            print(f"WARNING: {w}")

    # Parse and build model
    dens = parse_advancement_report(csv_path, json_path, skip_validation=True)

    print("\n--- Dens ---\n")
    for den in dens:
        print(f"{den.name} Den ({len(den.scouts)} scouts)")
        for scout in den.scouts:
            finished_names = [a.name for a in scout.finished_adventures]
            print(f"  • {scout.name}")
            if finished_names:
                print(f"    Finished: {', '.join(finished_names)}")
            else:
                print("    Finished: (none)")
        print()

    # Generate PDF report per scout in output/{den_name}/{scout_name}.pdf
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for den in dens:
        den_dir = OUTPUT_DIR / den.name
        den_dir.mkdir(parents=True, exist_ok=True)
        for scout in den.scouts:
            pdf_path = den_dir / f"{safe_filename(scout.name)}.pdf"
            build_scout_report_pdf(scout, den.name, pdf_path, logos_dir=LOGOS_DIR)
            print(f"Wrote {pdf_path}")
    print(f"\nPDFs written to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
