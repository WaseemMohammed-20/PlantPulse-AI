CREATE TABLE IF NOT EXISTS factories (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    factory_code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    city TEXT NOT NULL,
    country TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT factories_code_not_blank CHECK (btrim(factory_code) <> ''),
    CONSTRAINT factories_name_not_blank CHECK (btrim(name) <> '')
);

CREATE TABLE IF NOT EXISTS production_lines (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    factory_id BIGINT NOT NULL REFERENCES factories (id),
    line_code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    target_units_per_hour NUMERIC(10, 2) NOT NULL,
    CONSTRAINT production_lines_target_positive
        CHECK (target_units_per_hour > 0),
    CONSTRAINT production_lines_name_not_blank CHECK (btrim(name) <> '')
);

CREATE TABLE IF NOT EXISTS machines (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    production_line_id BIGINT NOT NULL REFERENCES production_lines (id),
    machine_code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    machine_type TEXT NOT NULL,
    rated_capacity_per_hour NUMERIC(10, 2) NOT NULL,
    CONSTRAINT machines_capacity_positive
        CHECK (rated_capacity_per_hour > 0),
    CONSTRAINT machines_name_not_blank CHECK (btrim(name) <> ''),
    CONSTRAINT machines_type_not_blank CHECK (btrim(machine_type) <> '')
);

CREATE TABLE IF NOT EXISTS production_records (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    machine_id BIGINT NOT NULL REFERENCES machines (id),
    production_date DATE NOT NULL,
    shift_start TIMESTAMPTZ NOT NULL,
    shift_end TIMESTAMPTZ NOT NULL,
    planned_production_minutes INTEGER NOT NULL,
    target_units INTEGER NOT NULL,
    total_units INTEGER NOT NULL,
    good_units INTEGER NOT NULL,
    CONSTRAINT production_records_shift_valid CHECK (shift_end > shift_start),
    CONSTRAINT production_records_planned_time_positive
        CHECK (
            planned_production_minutes > 0
            AND planned_production_minutes
                <= EXTRACT(EPOCH FROM (shift_end - shift_start)) / 60
        ),
    CONSTRAINT production_records_target_positive CHECK (target_units > 0),
    CONSTRAINT production_records_total_nonnegative CHECK (total_units >= 0),
    CONSTRAINT production_records_good_valid
        CHECK (good_units >= 0 AND good_units <= total_units),
    CONSTRAINT production_records_machine_shift_unique
        UNIQUE (machine_id, shift_start)
);

CREATE TABLE IF NOT EXISTS downtime_events (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    production_record_id BIGINT NOT NULL
        REFERENCES production_records (id) ON DELETE CASCADE,
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ NOT NULL,
    cause TEXT NOT NULL,
    description TEXT NOT NULL,
    is_planned BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT downtime_events_time_valid CHECK (ended_at > started_at),
    CONSTRAINT downtime_events_cause_not_blank CHECK (btrim(cause) <> '')
);

CREATE TABLE IF NOT EXISTS quality_inspections (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    production_record_id BIGINT NOT NULL
        REFERENCES production_records (id) ON DELETE CASCADE,
    inspected_at TIMESTAMPTZ NOT NULL,
    inspection_type TEXT NOT NULL,
    inspected_units INTEGER NOT NULL,
    defective_units INTEGER NOT NULL,
    CONSTRAINT quality_inspections_type_not_blank
        CHECK (btrim(inspection_type) <> ''),
    CONSTRAINT quality_inspections_inspected_positive
        CHECK (inspected_units > 0),
    CONSTRAINT quality_inspections_defective_valid
        CHECK (defective_units >= 0 AND defective_units <= inspected_units)
);

CREATE INDEX IF NOT EXISTS production_lines_factory_id_idx
    ON production_lines (factory_id);
CREATE INDEX IF NOT EXISTS machines_production_line_id_idx
    ON machines (production_line_id);
CREATE INDEX IF NOT EXISTS production_records_machine_date_idx
    ON production_records (machine_id, production_date);
CREATE INDEX IF NOT EXISTS production_records_date_idx
    ON production_records (production_date);
CREATE INDEX IF NOT EXISTS downtime_events_record_started_idx
    ON downtime_events (production_record_id, started_at);
CREATE INDEX IF NOT EXISTS downtime_events_cause_idx
    ON downtime_events (cause);
CREATE INDEX IF NOT EXISTS quality_inspections_record_inspected_idx
    ON quality_inspections (production_record_id, inspected_at);
