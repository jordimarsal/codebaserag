#!/usr/bin/env bash
# bench.sh — run stack benchmarks and compare against harness/baselines.json.
#
# Run by the reviewer at audit_level: strict. The installer never runs this
# script. Without a baseline the script records values and warns (never blocks).
#
# Usage: bash harness/tools/bench.sh [--json]
# Exit codes: 0/1 as before; 2 = usage error

set -uo pipefail

BASELINES="harness/baselines.json"
MEASURED=0
REJECT=0
REGRESSIONS="[]"
RESULTS_JSON="[]"
OUT="$(mktemp)"
trap 'rm -f "$OUT" harness/.bench-last.json' EXIT

STACK=""
if [ -f "tsconfig.json" ]; then STACK="typescript"
elif [ -f "package.json" ]; then STACK="node"
elif [ -f "requirements.txt" ] || [ -f "pyproject.toml" ] || [ -f "setup.py" ]; then STACK="python"
elif [ -f "Cargo.toml" ]; then STACK="rust"
else STACK="generic"
fi

JSON=0
for arg in "$@"; do
  case "$arg" in
    --json) JSON=1 ;;
    *) echo "unknown argument: $arg" >&2; exit 2 ;;
  esac
done

[ "$JSON" -eq 1 ] || echo "# Benchmark Report (stack: $STACK)"
[ "$JSON" -eq 1 ] || echo ""

case "$STACK" in
  python)
    if python3 -c "import pytest_benchmark" >/dev/null 2>&1; then
      [ "$JSON" -eq 1 ] || echo "## Runner: pytest-benchmark"
      if python3 -m pytest -q tests --benchmark-only --benchmark-json=harness/.bench-last.json > "$OUT" 2>&1; then
        [ "$JSON" -eq 1 ] || tail -n 15 "$OUT"
        MEASURED=1
        RESULTS_JSON="$(python3 - <<'PYEOF' 2>/dev/null || echo "[]"
import json
try:
    d = json.load(open("harness/.bench-last.json"))
    print(json.dumps([{"name": b["name"], "mean_ms": round(b["stats"]["mean"] * 1000.0, 3)} for b in d.get("benchmarks", [])]))
except Exception:
    print("[]")
PYEOF
)"
      else
        [ "$JSON" -eq 1 ] || echo "pytest --benchmark-only failed (no benchmark-marked tests?)"
        [ "$JSON" -eq 1 ] || cat "$OUT"
      fi
    else
      [ "$JSON" -eq 1 ] || echo "## Runner: pytest-benchmark — SKIPPED (not installed; pip install pytest-benchmark)"
      [ "$JSON" -eq 1 ] || echo "Record-only: no measurements taken."
    fi
    ;;
  typescript|node)
    if [ -d "node_modules/vitest" ] && npx vitest bench --run > "$OUT" 2>&1; then
      [ "$JSON" -eq 1 ] || echo "## Runner: vitest bench"
      [ "$JSON" -eq 1 ] || tail -n 15 "$OUT"
      MEASURED=1
    else
      [ "$JSON" -eq 1 ] || echo "## Runner: vitest bench — SKIPPED (not configured). Record-only."
    fi
    ;;
  rust)
    if { [ -d "benches" ] || grep -q "\[\[bench\]\]" Cargo.toml 2>/dev/null; } && cargo bench > "$OUT" 2>&1; then
      [ "$JSON" -eq 1 ] || echo "## Runner: cargo bench"
      [ "$JSON" -eq 1 ] || tail -n 15 "$OUT"
      MEASURED=1
    else
      [ "$JSON" -eq 1 ] || echo "## Runner: cargo bench — SKIPPED (no benches configured). Record-only."
    fi
    ;;
  *)
    [ "$JSON" -eq 1 ] || echo "## Checklist-only (no automated benchmarks for stack: $STACK)"
    ;;
esac

# Compare against baselines when we have measurements, a non-empty baseline
# file, and python3 available (only the python runner produces parseable JSON).
if [ "$MEASURED" -eq 1 ] && [ "$STACK" = "python" ] \
   && [ -s "$BASELINES" ] \
   && [ "$(cat "$BASELINES")" != "{}" ] \
   && command -v python3 >/dev/null 2>&1 \
   && [ -f "harness/.bench-last.json" ]; then
  [ "$JSON" -eq 1 ] || echo ""
  [ "$JSON" -eq 1 ] || echo "## Baseline comparison"
  if ! python3 - "$BASELINES" "harness/.bench-last.json" "$OUT.regres" <<'PYEOF'; then
import json, sys
base = json.load(open(sys.argv[1]))
data = json.load(open(sys.argv[2]))
regres = open(sys.argv[3], "w")
last = {b["name"]: b["stats"]["mean"] * 1000.0 for b in data["benchmarks"]}
reject = False
for name, entry in base.items():
    if name not in last:
        print(f"- {name}: no measurement found (baseline stale?)")
        continue
    mean_ms = last[name]
    ref = entry.get("mean_ms")
    th = entry.get("thresholds", {}).get("mean_ms", {})
    warn_m = th.get("warning", 1.5)
    crit_m = th.get("critical", 2.0)
    if ref is None:
        print(f"- {name}: measured {mean_ms:.1f} ms (no reference mean_ms yet; record it)")
        continue
    ratio = mean_ms / ref
    if ratio > crit_m:
        print(f"- {name}: REGRESSION {ratio:.2f}x vs baseline {ref:.1f} ms (critical {crit_m}x)")
        regres.write(name + "\n")
        reject = True
    elif ratio > warn_m:
        print(f"- {name}: WARNING {ratio:.2f}x vs baseline {ref:.1f} ms")
    else:
        print(f"- {name}: ok {mean_ms:.1f} ms ({ratio:.2f}x baseline)")
regres.close()
sys.exit(1 if reject else 0)
PYEOF
    REJECT=1
  fi
  if [ -f "$OUT.regres" ]; then
    REGRESSIONS="$(python3 -c "import json,sys; print(json.dumps([l.strip() for l in open(sys.argv[1]) if l.strip()]))" "$OUT.regres" 2>/dev/null || echo "[]")"
    rm -f "$OUT.regres"
  fi
elif [ "$MEASURED" -eq 1 ]; then
  [ "$JSON" -eq 1 ] || echo ""
  [ "$JSON" -eq 1 ] || echo "No usable baseline in $BASELINES — values recorded only (add entries after review)."
fi

if [ "$JSON" -eq 1 ]; then
  MODE="checklist-only"
  [ "$STACK" = "python" ] || [ "$STACK" = "typescript" ] || [ "$STACK" = "node" ] || [ "$STACK" = "rust" ] && MODE="record-only"
  [ "$MEASURED" -eq 1 ] && MODE="run"
  VERDICT="PASS"
  [ "$REJECT" -eq 1 ] && VERDICT="REJECT"
  printf '{"tool":"bench","protocol":1,"stack":"%s","mode":"%s","results":%s,"regressions":%s,"verdict":"%s"}\n' \
    "$STACK" "$MODE" "${RESULTS_JSON:-[]}" "$REGRESSIONS" "$VERDICT"
else
  echo ""
  if [ "$REJECT" -eq 1 ]; then
    echo "VERDICT: benchmark regression beyond critical threshold — approval rejected (strict)."
    exit 1
  fi
  echo "VERDICT: no benchmark regression."
  exit 0
fi
[ "$REJECT" -eq 1 ] && exit 1
exit 0
