"""
AGT-05: Parameter Interpretation Agent

Compares recorded measurements against component-specific reference
ranges and produces annotated results for the Diagnostic Agent to use.
Reference ranges are defined statically here; they match the values in
the knowledge base .txt files.
"""

from typing import Any
from agents.base_agent import BaseAgent


# ─── Reference parameter ranges per component ────────────────────────────────
# Format: parameter_key → (min, max, unit, critical_below, critical_above)
#   None = no critical threshold in that direction

PARAM_SPECS: dict[str, dict[str, tuple]] = {
    "Hoist Motor": {
        "voltage":               (380, 420,   "V",   360, 440),
        "current":               (0,   None,  "A",   None, None),   # rated load-dependent
        "temperature":           (0,   90,    "°C",  None, 120),
        "insulation_resistance": (1.0, None,  "MΩ",  0.5,  None),
        "vibration":             (0,   4.5,   "mm/s RMS", None, 7.1),
    },
    "Hoist Brake": {
        "brake_gap":             (0.2, 0.5,   "mm",  None, 1.0),
        "voltage":               (380, 420,   "V",   360, 440),
        "temperature":           (0,   80,    "°C",  None, 100),
    },
    "Wire Rope": {
        "load":                  (0,   None,  "kg",  None, None),
    },
    "Gearbox": {
        "temperature":           (0,   80,    "°C",  None, 95),
        "vibration":             (0,   4.5,   "mm/s RMS", None, 7.1),
    },
    "Trolley Motor": {
        "voltage":               (380, 420,   "V",   360, 440),
        "current":               (0,   None,  "A",   None, None),
        "temperature":           (0,   90,    "°C",  None, 120),
        "insulation_resistance": (1.0, None,  "MΩ",  0.5,  None),
    },
    "Bridge Motor": {
        "voltage":               (380, 420,   "V",   360, 440),
        "current":               (0,   None,  "A",   None, None),
        "temperature":           (0,   90,    "°C",  None, 120),
        "insulation_resistance": (1.0, None,  "MΩ",  0.5,  None),
    },
    "Control System": {
        "voltage":               (380, 420,   "V",   360, 440),
        "insulation_resistance": (1.0, None,  "MΩ",  0.5,  None),
    },
    "Power Supply": {
        "voltage":               (380, 420,   "V",   360, 440),
        "insulation_resistance": (1.0, None,  "MΩ",  0.5,  None),
    },
    "Limit Switch": {
        "voltage":               (20,  30,    "V",   None, None),
    },
}

# Friendly labels for parameter keys
PARAM_LABELS = {
    "voltage":               "Voltage",
    "current":               "Current",
    "temperature":           "Temperature",
    "load":                  "Load",
    "brake_gap":             "Brake Gap",
    "insulation_resistance": "Insulation Resistance",
    "vibration":             "Vibration",
}

# Map measurement dict keys → display names and units
MEASUREMENT_FIELDS = {
    "voltage":               ("Voltage",              "V"),
    "current":               ("Current",              "A"),
    "temperature":           ("Temperature",          "°C"),
    "load":                  ("Load",                 "kg"),
    "brake_gap":             ("Brake Gap",            "mm"),
    "insulation_resistance": ("Insulation Resistance","MΩ"),
    "vibration":             ("Vibration",            "mm/s RMS"),
}


class ParameterInterpretationAgent(BaseAgent):
    AGT_ID = "AGT-05"

    def _execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Input keys:
          component_key:  str
          measurements:   list[dict]   (raw measurement records from DB)

        Output:
          annotated_measurements: list[dict]
          has_critical:  bool
          summary_text:  str   (for injection into system prompt)
        """
        component: str      = payload.get("component_key", "")
        measurements: list  = payload.get("measurements", [])

        specs = PARAM_SPECS.get(component, {})
        annotated = []
        has_critical = False

        for m in measurements:
            row_annotations = []
            for field, (label, unit) in MEASUREMENT_FIELDS.items():
                value = m.get(field)
                if value is None:
                    continue

                spec = specs.get(field)
                if spec:
                    lo, hi, _, crit_lo, crit_hi = spec
                    status, annotation, critical = _evaluate(
                        field, value, unit, lo, hi, crit_lo, crit_hi
                    )
                    if critical:
                        has_critical = True
                else:
                    status = "NO_REFERENCE"
                    annotation = f"{label}: {value} {unit} (no reference range defined)"
                    critical = False

                row_annotations.append({
                    "parameter":   field,
                    "label":       label,
                    "value":       value,
                    "unit":        unit,
                    "status":      status,
                    "annotation":  annotation,
                    "critical":    critical,
                })

            if m.get("notes"):
                row_annotations.append({
                    "parameter": "notes",
                    "label":     "Engineer Notes",
                    "value":     m["notes"],
                    "unit":      "",
                    "status":    "NOTE",
                    "annotation": f"Engineer note: {m['notes']}",
                    "critical":  False,
                })

            annotated.append(row_annotations)

        # Build a compact text block for system prompt injection
        lines = ["=== MEASUREMENT INTERPRETATION ==="]
        for row in annotated:
            for a in row:
                if a["parameter"] == "notes":
                    lines.append(f"  • {a['annotation']}")
                else:
                    lines.append(f"  • {a['annotation']}")
        if has_critical:
            lines.insert(1, "  ⚠ CRITICAL VALUES DETECTED — see annotations below")
        summary_text = "\n".join(lines)

        return {
            "annotated_measurements": annotated,
            "has_critical":           has_critical,
            "summary_text":           summary_text,
        }


def _evaluate(
    field: str, value: float, unit: str,
    lo, hi, crit_lo, crit_hi
) -> tuple[str, str, bool]:
    label = PARAM_LABELS.get(field, field)
    critical = False

    if crit_lo is not None and value < crit_lo:
        status = "CRITICAL_LOW"
        annotation = (
            f"{label}: {value} {unit} — CRITICAL: below minimum safe threshold "
            f"({crit_lo} {unit}). Immediate action required."
        )
        critical = True
    elif crit_hi is not None and value > crit_hi:
        status = "CRITICAL_HIGH"
        annotation = (
            f"{label}: {value} {unit} — CRITICAL: exceeds maximum safe threshold "
            f"({crit_hi} {unit}). Immediate action required."
        )
        critical = True
    elif lo is not None and value < lo:
        status = "BELOW_MINIMUM"
        annotation = (
            f"{label}: {value} {unit} — below specification minimum "
            f"(expected ≥ {lo} {unit})."
        )
    elif hi is not None and value > hi:
        status = "ABOVE_MAXIMUM"
        annotation = (
            f"{label}: {value} {unit} — above specification maximum "
            f"(expected ≤ {hi} {unit})."
        )
    else:
        status = "WITHIN_RANGE"
        range_str = f"{lo}–{hi}" if (lo is not None and hi is not None) else "acceptable range"
        annotation = f"{label}: {value} {unit} — within normal range ({range_str} {unit})."

    return status, annotation, critical
