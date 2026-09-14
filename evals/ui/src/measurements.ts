export type RunRecord = Record<string, unknown>;

export type ComparisonReason =
  | "select-exactly-two"
  | "duplicate-record"
  | "missing-campaign"
  | "missing-candidate"
  | "missing-case"
  | "missing-harness"
  | "missing-model"
  | "campaign-mismatch"
  | "candidate-mismatch"
  | "case-mismatch"
  | "harness-mismatch"
  | "model-mismatch"
  | "configuration-mismatch"
  | "execution-invalid";

export type ComparisonEligibility = {
  reason: ComparisonReason | null;
  baseline: RunRecord | null;
  with: RunRecord | null;
};

export type DescriptiveDelta = { delta: number | null; percent: number | null };

const identityFields = ["campaign", "candidate", "case", "harness", "model"] as const;

function record(value: unknown): RunRecord | null {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? value as RunRecord : null;
}

function measurement(recordValue: unknown): RunRecord | null {
  const value = record(recordValue);
  const measurementValue = record(value?.measurement);
  return measurementValue?.version === 1 && record(measurementValue.available)
    ? measurementValue : null;
}

function available(envelope: RunRecord | null, field: string): boolean {
  return record(envelope?.available)?.[field] === true;
}

export function measurementNumber(run: unknown, field: string): number | null {
  const value = record(run);
  const envelope = measurement(value);
  const actual = value?.[field];
  return available(envelope, field) && typeof actual === "number"
    && Number.isFinite(actual) && actual >= 0 ? actual : null;
}

export function measurementBoolean(run: unknown, field: string): boolean | null {
  const value = record(run);
  const envelope = measurement(value);
  const actual = value?.[field];
  return available(envelope, field) && typeof actual === "boolean" ? actual : null;
}

function invalid(baseline: RunRecord | null, withValue: RunRecord | null,
                 reason: ComparisonReason): ComparisonEligibility {
  return { reason, baseline, with: withValue };
}

function validExecution(run: RunRecord): boolean {
  return record(measurement(run)?.execution)?.validity === "valid";
}

export function comparisonEligibility(selected: readonly unknown[]): ComparisonEligibility {
  if (selected.length !== 2) return invalid(null, null, "select-exactly-two");
  const first = record(selected[0]);
  const second = record(selected[1]);
  if (!first || !second || typeof first.id !== "string" || !first.id.trim()
      || typeof second.id !== "string" || !second.id.trim()
      || first.id === second.id) return invalid(null, null, "duplicate-record");

  for (const field of identityFields) {
    if (typeof first[field] !== "string" || !first[field].trim()
        || typeof second[field] !== "string" || !second[field].trim()) {
      return invalid(null, null, `missing-${field}` as ComparisonReason);
    }
    if (first[field] !== second[field]) return invalid(null, null, `${field}-mismatch` as ComparisonReason);
  }

  const baseline = first.config === "baseline" ? first : second.config === "baseline" ? second : null;
  const withValue = first.config === "with" ? first : second.config === "with" ? second : null;
  if (!baseline || !withValue) return invalid(baseline, withValue, "configuration-mismatch");
  if (!validExecution(baseline) || !validExecution(withValue)) {
    return invalid(baseline, withValue, "execution-invalid");
  }
  return { reason: null, baseline, with: withValue };
}

export function descriptiveDelta(baseline: unknown, withValue: unknown): DescriptiveDelta {
  if (typeof baseline !== "number" || typeof withValue !== "number"
      || !Number.isFinite(baseline) || !Number.isFinite(withValue)) {
    return { delta: null, percent: null };
  }
  const delta = withValue - baseline;
  if (!Number.isFinite(delta)) return { delta: null, percent: null };
  const percent = baseline > 0 ? delta / baseline * 100 : null;
  return { delta, percent: percent !== null && !Number.isFinite(percent) ? null : percent };
}
