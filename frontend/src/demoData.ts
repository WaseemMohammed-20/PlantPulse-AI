import type {
  DashboardData,
  DowntimeCause,
  DowntimeMachine,
  Machine,
  ProductionLine,
  ProductionTrend,
  QualityLine,
} from "./types";

const daysToShow = 30;

const lineSeeds = [
  { lineId: 1, code: "LINE-US-01", name: "Assembly Line A", factory: "Riverside Works", factoryId: 1, capacities: [78, 64, 92] },
  { lineId: 2, code: "LINE-US-02", name: "Packaging Line B", factory: "Riverside Works", factoryId: 1, capacities: [86, 74, 68] },
  { lineId: 3, code: "LINE-DE-01", name: "Precision Line A", factory: "Bavaria Works", factoryId: 2, capacities: [58, 62, 72] },
  { lineId: 4, code: "LINE-DE-02", name: "Assembly Line B", factory: "Bavaria Works", factoryId: 2, capacities: [82, 66, 88] },
  { lineId: 5, code: "LINE-IN-01", name: "Components Line A", factory: "Western Works", factoryId: 3, capacities: [94, 76, 70] },
  { lineId: 6, code: "LINE-IN-02", name: "Packaging Line C", factory: "Western Works", factoryId: 3, capacities: [90, 72, 80] },
];

const machineNames = [
  ["Assembly Robot 1", "Press 1", "Packaging Cell 1"],
  ["Filler 1", "Labeler 1", "Case Packer 1"],
  ["CNC Cell 1", "CNC Cell 2", "Inspection Cell 1"],
  ["Assembly Robot 2", "Press 2", "Packaging Cell 2"],
  ["Molding Machine 1", "Trimmer 1", "Inspection Cell 2"],
  ["Filler 2", "Labeler 2", "Case Packer 2"],
];

const machineTypes = [
  ["robotic_assembler", "hydraulic_press", "packaging_cell"],
  ["filling_machine", "labeling_machine", "case_packer"],
  ["cnc_machine", "cnc_machine", "inspection_cell"],
  ["robotic_assembler", "hydraulic_press", "packaging_cell"],
  ["injection_molder", "trimming_machine", "inspection_cell"],
  ["filling_machine", "labeling_machine", "case_packer"],
];

function dailyTrends(): ProductionTrend[] {
  const today = new Date();
  const start = new Date(Date.UTC(
    today.getUTCFullYear(),
    today.getUTCMonth(),
    today.getUTCDate() - daysToShow + 1,
  ));

  return Array.from({ length: daysToShow }, (_, dayIndex) => {
    let production = 0;
    let target = 0;
    let good = 0;

    lineSeeds.forEach((line, lineIndex) => {
      const lineTarget = line.capacities.reduce((sum, capacity) => sum + capacity, 0) * 7.5;
      const attainment = 0.83 + ((dayIndex * 7 + lineIndex * 11) % 13) / 100;
      const lineProduction = Math.round(lineTarget * attainment);
      const lineGood = Math.round(lineProduction * (0.965 + (lineIndex % 4) * 0.005));
      production += lineProduction;
      target += lineTarget;
      good += lineGood;
    });

    const date = new Date(start);
    date.setUTCDate(date.getUTCDate() + dayIndex);
    return {
      production_date: date.toISOString().slice(0, 10),
      production_quantity: production,
      good_quantity: good,
      production_target: target,
    };
  });
}

function createMachines(): Machine[] {
  const machines: Machine[] = [];

  lineSeeds.forEach((line, lineIndex) => {
    line.capacities.forEach((capacity, machineIndex) => {
      const index = lineIndex * 3 + machineIndex;
      const target = Math.round(capacity * 7.5 * daysToShow);
      const attainment = 0.82 + ((index * 7) % 14) / 100;
      const production = Math.round(target * attainment);
      const inspected = Math.round(production * (0.09 + (index % 4) * 0.01));
      const defectRate = 0.018 + (index % 5) * 0.004;
      const defects = Math.round(inspected * defectRate);
      const downtime = 48 + ((index * 37) % 115);

      machines.push({
        machine_id: index + 1,
        machine_code: `M-${["US", "DE", "IN"][line.factoryId - 1]}-${String((lineIndex % 2) * 3 + machineIndex + 1).padStart(3, "0")}`,
        machine_name: machineNames[lineIndex][machineIndex],
        machine_type: machineTypes[lineIndex][machineIndex],
        rated_capacity_per_hour: capacity,
        line_id: line.lineId,
        line_code: line.code,
        line_name: line.name,
        factory_id: line.factoryId,
        factory_name: line.factory,
        production_quantity: production,
        production_target: target,
        target_attainment_pct: Number(((production / target) * 100).toFixed(2)),
        unplanned_downtime_minutes: downtime,
        inspected_units: inspected,
        defective_units: defects,
        defect_rate_pct: Number(((defects / inspected) * 100).toFixed(2)),
      });
    });
  });

  return machines;
}

function createLines(machines: Machine[]): ProductionLine[] {
  return lineSeeds.map((line) => {
    const lineMachines = machines.filter((machine) => machine.line_id === line.lineId);
    const production = lineMachines.reduce((sum, machine) => sum + machine.production_quantity, 0);
    const target = lineMachines.reduce((sum, machine) => sum + machine.production_target, 0);
    return {
      line_id: line.lineId,
      line_code: line.code,
      line_name: line.name,
      factory_name: line.factory,
      production_quantity: production,
      production_target: target,
      target_attainment_pct: Number(((production / target) * 100).toFixed(2)),
      unplanned_downtime_minutes: lineMachines.reduce((sum, machine) => sum + machine.unplanned_downtime_minutes, 0),
    };
  });
}

function createDowntimeCauses(): DowntimeCause[] {
  return [
    { cause: "equipment_failure", is_planned: false, event_count: 31, downtime_minutes: 658 },
    { cause: "material_shortage", is_planned: false, event_count: 25, downtime_minutes: 432 },
    { cause: "quality_hold", is_planned: false, event_count: 14, downtime_minutes: 296 },
    { cause: "changeover", is_planned: true, event_count: 21, downtime_minutes: 508 },
    { cause: "maintenance", is_planned: true, event_count: 16, downtime_minutes: 574 },
  ];
}

function createDowntimeRanking(machines: Machine[]): DowntimeMachine[] {
  return [...machines]
    .sort((left, right) => right.unplanned_downtime_minutes - left.unplanned_downtime_minutes)
    .map((machine, index) => ({
      downtime_rank: index + 1,
      machine_id: machine.machine_id,
      machine_code: machine.machine_code,
      machine_name: machine.machine_name,
      production_line: machine.line_name,
      factory_name: machine.factory_name,
      unplanned_event_count: 2 + (machine.machine_id % 4),
      unplanned_downtime_minutes: machine.unplanned_downtime_minutes,
    }));
}

function createQualityLines(machines: Machine[]): QualityLine[] {
  return lineSeeds.map((line) => {
    const lineMachines = machines.filter((machine) => machine.line_id === line.lineId);
    const inspected = lineMachines.reduce((sum, machine) => sum + machine.inspected_units, 0);
    const defective = lineMachines.reduce((sum, machine) => sum + machine.defective_units, 0);
    return {
      line_id: line.lineId,
      line_code: line.code,
      line_name: line.name,
      factory_name: line.factory,
      inspected_units: inspected,
      defective_units: defective,
      defect_rate_pct: Number(((defective / inspected) * 100).toFixed(2)),
    };
  });
}

const machines = createMachines();
const lines = createLines(machines);
const qualityLines = createQualityLines(machines);
const downtimeCauses = createDowntimeCauses();
const downtimeMachines = createDowntimeRanking(machines);
const trends = dailyTrends();
const productionQuantity = lines.reduce((sum, line) => sum + line.production_quantity, 0);
const productionTarget = lines.reduce((sum, line) => sum + line.production_target, 0);
const inspectedUnits = qualityLines.reduce((sum, line) => sum + line.inspected_units, 0);
const defectiveUnits = qualityLines.reduce((sum, line) => sum + line.defective_units, 0);
const plannedMinutes = 450 * daysToShow * machines.length;
const downtimeMinutes = lines.reduce((sum, line) => sum + line.unplanned_downtime_minutes, 0);
const runMinutes = plannedMinutes - downtimeMinutes;
const theoreticalRunUnits = machines.reduce(
  (sum, machine) =>
    sum +
    machine.rated_capacity_per_hour *
      (450 * daysToShow - machine.unplanned_downtime_minutes) /
      60,
  0,
);
const goodUnits = machines.reduce(
  (sum, machine) =>
    sum +
    machine.production_quantity *
      (0.965 + ((machine.machine_id - 1) % 4) * 0.005),
  0,
);
const performance = productionQuantity / theoreticalRunUnits;
const quality = goodUnits / productionQuantity;

export const demoDashboardData: DashboardData = {
  health: null,
  overview: {
    production_quantity: productionQuantity,
    production_target: productionTarget,
    target_attainment_pct: Number(((productionQuantity / productionTarget) * 100).toFixed(2)),
    oee_pct: Number(((runMinutes / plannedMinutes) * performance * quality * 100).toFixed(2)),
    unplanned_downtime_minutes: downtimeMinutes,
    inspected_units: inspectedUnits,
    defective_units: defectiveUnits,
    defect_rate_pct: Number(((defectiveUnits / inspectedUnits) * 100).toFixed(2)),
  },
  trends,
  lines,
  downtimeCauses,
  downtimeMachines,
  qualityLines,
  machines,
  errors: {},
};
