"""Generate deterministic simulated manufacturing data in PostgreSQL."""

from __future__ import annotations

import argparse
import os
import random
import sys
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

import psycopg
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = PROJECT_ROOT / "database" / "schema.sql"
DEFAULT_SEED = 42
PLANNED_PRODUCTION_MINUTES = 450
SHIFT_START_HOUR_UTC = 6
SHIFT_LENGTH_MINUTES = 480
BREAK_START_MINUTE = 210
BREAK_END_MINUTE = 240
INSPECTION_TYPES = ("visual", "dimensional", "functional")
DOWNTIME_CAUSES = (
    "equipment_failure",
    "material_shortage",
    "changeover",
    "maintenance",
    "quality_hold",
)

FACTORIES = (
    ("FAC-US-01", "Riverside Works", "Cleveland", "United States"),
    ("FAC-DE-01", "Bavaria Works", "Augsburg", "Germany"),
    ("FAC-IN-01", "Western Works", "Pune", "India"),
)

LINE_LAYOUT = (
    (
        "FAC-US-01",
        "LINE-US-01",
        "Assembly Line A",
        (
            ("M-US-001", "Assembly Robot 1", "robotic_assembler", 78),
            ("M-US-002", "Press 1", "hydraulic_press", 64),
            ("M-US-003", "Packaging Cell 1", "packaging_cell", 92),
        ),
    ),
    (
        "FAC-US-01",
        "LINE-US-02",
        "Packaging Line B",
        (
            ("M-US-004", "Filler 1", "filling_machine", 86),
            ("M-US-005", "Labeler 1", "labeling_machine", 74),
            ("M-US-006", "Case Packer 1", "case_packer", 68),
        ),
    ),
    (
        "FAC-DE-01",
        "LINE-DE-01",
        "Precision Line A",
        (
            ("M-DE-001", "CNC Cell 1", "cnc_machine", 58),
            ("M-DE-002", "CNC Cell 2", "cnc_machine", 62),
            ("M-DE-003", "Inspection Cell 1", "inspection_cell", 72),
        ),
    ),
    (
        "FAC-DE-01",
        "LINE-DE-02",
        "Assembly Line B",
        (
            ("M-DE-004", "Assembly Robot 2", "robotic_assembler", 82),
            ("M-DE-005", "Press 2", "hydraulic_press", 66),
            ("M-DE-006", "Packaging Cell 2", "packaging_cell", 88),
        ),
    ),
    (
        "FAC-IN-01",
        "LINE-IN-01",
        "Components Line A",
        (
            ("M-IN-001", "Molding Machine 1", "injection_molder", 94),
            ("M-IN-002", "Trimmer 1", "trimming_machine", 76),
            ("M-IN-003", "Inspection Cell 2", "inspection_cell", 70),
        ),
    ),
    (
        "FAC-IN-01",
        "LINE-IN-02",
        "Packaging Line B",
        (
            ("M-IN-004", "Filler 2", "filling_machine", 90),
            ("M-IN-005", "Labeler 2", "labeling_machine", 72),
            ("M-IN-006", "Case Packer 2", "case_packer", 80),
        ),
    ),
)


@dataclass(frozen=True)
class DowntimeSample:
    started_at: datetime
    ended_at: datetime
    cause: str
    description: str


@dataclass(frozen=True)
class ProductionSample:
    machine_code: str
    production_date: date
    shift_start: datetime
    shift_end: datetime
    target_units: int
    total_units: int
    good_units: int
    inspected_units: int
    defective_units: int
    inspection_type: str
    inspected_at: datetime
    downtime_events: tuple[DowntimeSample, ...]


def parse_iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("Use a date in YYYY-MM-DD format.") from error


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate deterministic simulated factory, production, downtime, "
            "and quality data."
        )
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of inclusive calendar days to generate (default: 30).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"Random seed for reproducible data (default: {DEFAULT_SEED}).",
    )
    parser.add_argument(
        "--end-date",
        type=parse_iso_date,
        default=date.today(),
        help="Last date to generate, in YYYY-MM-DD format (default: today).",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Replace existing data in the six PlantPulse tables.",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Check deterministic generated data without connecting to PostgreSQL.",
    )
    args = parser.parse_args()
    if not 1 <= args.days <= 3660:
        parser.error("--days must be between 1 and 3660.")
    return args


def build_samples(days: int, seed: int, end_date: date) -> list[ProductionSample]:
    rng = random.Random(seed)
    samples: list[ProductionSample] = []
    first_date = end_date - timedelta(days=days - 1)

    for day_offset in range(days):
        production_date = first_date + timedelta(days=day_offset)
        shift_start = datetime.combine(
            production_date,
            time(SHIFT_START_HOUR_UTC),
            tzinfo=timezone.utc,
        )
        shift_end = shift_start + timedelta(minutes=SHIFT_LENGTH_MINUTES)
        for _, _, _, machines in LINE_LAYOUT:
            for machine_code, _, _, rated_capacity in machines:
                downtime_count = rng.choices((0, 1, 2), weights=(0.42, 0.46, 0.12))[0]
                intervals: list[tuple[int, int]] = []
                downtime_events: list[DowntimeSample] = []

                for _ in range(downtime_count):
                    duration = rng.randint(10, 45)
                    candidate_starts = [
                        minute
                        for window_start, window_end in (
                            (0, BREAK_START_MINUTE),
                            (BREAK_END_MINUTE, SHIFT_LENGTH_MINUTES),
                        )
                        for minute in range(window_start, window_end - duration + 1)
                        if all(
                            minute + duration <= existing_start
                            or minute >= existing_end
                            for existing_start, existing_end in intervals
                        )
                    ]
                    if not candidate_starts:
                        break
                    start_minute = rng.choice(candidate_starts)
                    end_minute = start_minute + duration
                    intervals.append((start_minute, end_minute))
                    downtime_events.append(
                        DowntimeSample(
                            started_at=shift_start + timedelta(minutes=start_minute),
                            ended_at=shift_start + timedelta(minutes=end_minute),
                            cause=rng.choice(DOWNTIME_CAUSES),
                            description=(
                                "Simulated "
                                + rng.choice(
                                    (
                                        "sensor fault",
                                        "material replenishment",
                                        "routine adjustment",
                                        "line stoppage",
                                        "component replacement",
                                    )
                                )
                            ),
                        )
                    )

                downtime_minutes = sum(
                    end - start for start, end in intervals
                )
                run_minutes = PLANNED_PRODUCTION_MINUTES - downtime_minutes
                target_units = round(
                    rated_capacity * PLANNED_PRODUCTION_MINUTES / 60
                )
                theoretical_run_units = rated_capacity * run_minutes / 60
                total_units = min(
                    round(target_units * rng.uniform(0.76, 0.99)),
                    int(theoretical_run_units),
                )
                good_units = total_units - round(
                    total_units * rng.uniform(0.01, 0.04)
                )
                inspected_units = max(
                    1, round(total_units * rng.uniform(0.05, 0.15))
                )
                defect_probability = rng.uniform(0.01, 0.06)
                defective_units = sum(
                    rng.random() < defect_probability
                    for _ in range(inspected_units)
                )

                samples.append(
                    ProductionSample(
                        machine_code=machine_code,
                        production_date=production_date,
                        shift_start=shift_start,
                        shift_end=shift_end,
                        target_units=target_units,
                        total_units=total_units,
                        good_units=good_units,
                        inspected_units=inspected_units,
                        defective_units=defective_units,
                        inspection_type=rng.choice(INSPECTION_TYPES),
                        inspected_at=shift_start + timedelta(hours=6),
                        downtime_events=tuple(downtime_events),
                    )
                )

    return samples


def validate_samples(samples: list[ProductionSample], days: int) -> None:
    known_machine_codes = {
        machine[0] for _, _, _, machines in LINE_LAYOUT for machine in machines
    }
    expected_production_records = len(known_machine_codes) * days
    if len(samples) != expected_production_records:
        raise ValueError(
            f"Expected {expected_production_records} production records; "
            f"generated {len(samples)}."
        )

    seen_shifts: set[tuple[str, datetime]] = set()
    for sample in samples:
        if sample.machine_code not in known_machine_codes:
            raise ValueError(f"Unknown machine code: {sample.machine_code}")
        shift_key = (sample.machine_code, sample.shift_start)
        if shift_key in seen_shifts:
            raise ValueError(f"Duplicate machine shift: {shift_key}")
        seen_shifts.add(shift_key)
        if sample.shift_end <= sample.shift_start:
            raise ValueError(f"Invalid shift for {sample.machine_code}")
        if not (
            0 <= sample.good_units <= sample.total_units <= sample.target_units
        ):
            raise ValueError(f"Invalid production quantities for {shift_key}")
        if not (
            sample.inspected_units > 0
            and sample.inspected_units <= sample.total_units
            and 0 <= sample.defective_units <= sample.inspected_units
        ):
            raise ValueError(f"Invalid quality inspection for {shift_key}")

        intervals = sorted(
            (event.started_at, event.ended_at)
            for event in sample.downtime_events
        )
        for index, (started_at, ended_at) in enumerate(intervals):
            if not sample.shift_start <= started_at < ended_at <= sample.shift_end:
                raise ValueError(f"Downtime outside shift for {shift_key}")
            if index and started_at < intervals[index - 1][1]:
                raise ValueError(f"Overlapping downtime for {shift_key}")


def expected_row_counts(
    samples: list[ProductionSample],
) -> dict[str, int]:
    return {
        "factories": len(FACTORIES),
        "production_lines": len(LINE_LAYOUT),
        "machines": sum(len(line[3]) for line in LINE_LAYOUT),
        "production_records": len(samples),
        "downtime_events": sum(len(sample.downtime_events) for sample in samples),
        "quality_inspections": len(samples),
    }


def load_database_connection() -> psycopg.Connection:
    load_dotenv(PROJECT_ROOT / ".env")
    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        return psycopg.connect(database_url)

    required = ("POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD")
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        missing_names = ", ".join(missing)
        raise ValueError(
            f"Set DATABASE_URL or configure {missing_names} in the environment "
            "or the project .env file."
        )

    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )


def insert_reference_data(
    cursor: psycopg.Cursor,
) -> dict[str, int]:
    factory_ids: dict[str, int] = {}
    line_ids: dict[str, int] = {}
    machine_ids: dict[str, int] = {}

    for factory_code, name, city, country in FACTORIES:
        cursor.execute(
            """
            INSERT INTO factories (factory_code, name, city, country)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (factory_code, name, city, country),
        )
        factory_ids[factory_code] = cursor.fetchone()[0]

    for factory_code, line_code, name, machines in LINE_LAYOUT:
        target_units_per_hour = sum(machine[3] for machine in machines)
        cursor.execute(
            """
            INSERT INTO production_lines
                (factory_id, line_code, name, target_units_per_hour)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (
                factory_ids[factory_code],
                line_code,
                name,
                target_units_per_hour,
            ),
        )
        line_ids[line_code] = cursor.fetchone()[0]

        for machine_code, machine_name, machine_type, capacity in machines:
            cursor.execute(
                """
                INSERT INTO machines
                    (production_line_id, machine_code, name, machine_type,
                     rated_capacity_per_hour)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    line_ids[line_code],
                    machine_code,
                    machine_name,
                    machine_type,
                    capacity,
                ),
            )
            machine_ids[machine_code] = cursor.fetchone()[0]

    return machine_ids


def seed_production_data(
    cursor: psycopg.Cursor,
    machine_ids: dict[str, int],
    samples: list[ProductionSample],
) -> None:
    for sample in samples:
        cursor.execute(
            """
            INSERT INTO production_records
                (machine_id, production_date, shift_start, shift_end,
                 planned_production_minutes, target_units, total_units, good_units)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                machine_ids[sample.machine_code],
                sample.production_date,
                sample.shift_start,
                sample.shift_end,
                PLANNED_PRODUCTION_MINUTES,
                sample.target_units,
                sample.total_units,
                sample.good_units,
            ),
        )
        production_record_id = cursor.fetchone()[0]

        cursor.execute(
            """
            INSERT INTO quality_inspections
                (production_record_id, inspected_at, inspection_type,
                 inspected_units, defective_units)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                production_record_id,
                sample.inspected_at,
                sample.inspection_type,
                sample.inspected_units,
                sample.defective_units,
            ),
        )

        for event in sample.downtime_events:
            cursor.execute(
                """
                INSERT INTO downtime_events
                    (production_record_id, started_at, ended_at, cause,
                     description, is_planned)
                VALUES (%s, %s, %s, %s, %s, FALSE)
                """,
                (
                    production_record_id,
                    event.started_at,
                    event.ended_at,
                    event.cause,
                    event.description,
                ),
            )


def validate_database(
    cursor: psycopg.Cursor,
    expected_counts: dict[str, int],
) -> None:
    for table_name, expected_count in expected_counts.items():
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        actual_count = cursor.fetchone()[0]
        if actual_count != expected_count:
            raise ValueError(
                f"Validation failed for {table_name}: expected "
                f"{expected_count}, found {actual_count}."
            )

    orphan_checks = (
        (
            "production_records",
            "SELECT COUNT(*) FROM production_records pr "
            "LEFT JOIN machines m ON m.id = pr.machine_id "
            "WHERE m.id IS NULL",
        ),
        (
            "downtime_events",
            "SELECT COUNT(*) FROM downtime_events de "
            "LEFT JOIN production_records pr "
            "ON pr.id = de.production_record_id "
            "WHERE pr.id IS NULL",
        ),
        (
            "quality_inspections",
            "SELECT COUNT(*) FROM quality_inspections qi "
            "LEFT JOIN production_records pr "
            "ON pr.id = qi.production_record_id "
            "WHERE pr.id IS NULL",
        ),
    )
    for table_name, query in orphan_checks:
        cursor.execute(query)
        orphan_count = cursor.fetchone()[0]
        if orphan_count:
            raise ValueError(
                f"Validation found {orphan_count} orphaned rows in {table_name}."
            )


def run() -> int:
    args = parse_args()
    samples = build_samples(args.days, args.seed, args.end_date)
    validate_samples(samples, args.days)

    if args.validate_only:
        repeated_samples = build_samples(args.days, args.seed, args.end_date)
        if samples != repeated_samples:
            raise ValueError("Generated data is not reproducible for this seed.")
        print(f"Validated {len(samples)} deterministic production records.")
        for table_name, count in expected_row_counts(samples).items():
            print(f"{table_name}: {count}")
        print("No database connection made (--validate-only).")
        return 0

    if not SCHEMA_PATH.is_file():
        raise FileNotFoundError(f"Database schema not found: {SCHEMA_PATH}")

    expected_counts = expected_row_counts(samples)
    with load_database_connection() as connection:
        with connection.cursor() as cursor:
            if args.reset:
                cursor.execute(
                    """
                    TRUNCATE TABLE
                        quality_inspections,
                        downtime_events,
                        production_records,
                        machines,
                        production_lines,
                        factories
                    RESTART IDENTITY
                    """
                )
            else:
                for table_name in expected_counts:
                    cursor.execute(f"SELECT EXISTS (SELECT 1 FROM {table_name})")
                    if cursor.fetchone()[0]:
                        raise ValueError(
                            f"{table_name} already contains data. Use --reset "
                            "only if you intend to replace all six table contents."
                        )

            machine_ids = insert_reference_data(cursor)
            seed_production_data(cursor, machine_ids, samples)
            validate_database(cursor, expected_counts)

    print("Database records inserted and validated:")
    for table_name, count in expected_counts.items():
        print(f"{table_name}: {count}")
    print("Foreign-key validation: passed (no orphaned rows).")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    except (OSError, ValueError, psycopg.Error) as error:
        print(f"Data generation failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
