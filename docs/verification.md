# Verification

This document defines how to prove that work works. Every feature must pass verification
before it can be marked as done. There are no exceptions.

---

## Verification Levels

### Level 1: Unit Tests (Mandatory)

Every feature must have unit tests. Unit tests verify individual functions, methods, and
classes in isolation. They must:

- Cover every public function and method.
- Test both the happy path and every documented error case.
- Be deterministic: running the same test twice must produce the same result.
- Be fast: the full unit test suite must complete in under 60 seconds.

### Level 2: Integration Tests (Mandatory for UI/API)

Any feature that introduces or modifies a user interface endpoint, REST API endpoint,
or inter-service boundary must include integration tests. These tests must:

- Exercise the full request/response cycle from the external interface inward.
- Use realistic inputs, including edge cases and malformed data.
- Verify both correct behavior and correct error responses.
- Run against a test environment that mirrors production configuration as closely as
  possible.

Features that are purely internal (utilities, data transformations, algorithms) do not
require integration tests but still require unit tests.

### Level 3: Smoke Tests (Optional)

Smoke tests are lightweight checks that confirm the system starts and responds to basic
requests. They are optional but recommended for:

- Services that have historically had startup regressions.
- Features that change dependency injection, configuration loading, or initialization
  order.

Smoke tests must not replace unit or integration tests. They are a supplement, not a
substitute.

### Level 4: Requirement Traceability (Mandatory for All Features)

Every requirement R\<n\> in the spec must map to at least one test that verifies it.
This mapping is documented in the progress file (see `specs.md` - Traceability section).
A feature cannot be marked as done until every requirement has a passing test that
proves it works.

---

## Anti-Patterns

The following are explicitly prohibited and will cause a review rejection:

### "It should work" without tests

Claiming that code is correct by visual inspection or informal manual testing is not
acceptable. If there is no automated test, the feature is not done. This applies to
bug fixes as well: every bug fix must include a test that would have caught the bug.

### Tests that only check no-throw

A test whose only assertion is that the code does not throw an exception is not a valid
test. Example of an invalid test:

```python
def test_login():
    result = login("user", "pass")  # no assertion on result
    # test passes if no exception is raised -- INVALID
```

Every test must assert something specific about the output, state change, or returned
value. At minimum, verify the return type and at least one expected property.

### Marking done without harness/init.sh

No feature may be marked as `done` unless `harness/init.sh` completes successfully. This is
the final gate. If `harness/init.sh` fails for any reason, the feature remains `in_progress`.

---

## Final Verification

The last step before any feature transitions to `done` is:

```
harness/init.sh
```

The script must finish with the output:

```
[OK]
```

If the script produces any error output, exits with a non-zero code, or does not print
`[OK]` as its final line, the feature is not done. The implementer must diagnose and
fix the issue before requesting the completion gate review.

This check is not optional. It is not a suggestion. It is the final, non-negotiable
proof that the system is in a working state.

<!-- harness:module:performance-benchmarks:start -->
## Performance Benchmarks (performance-benchmarks module)

> Appended by the harness `performance-benchmarks` module. Benchmarks are run by
> the reviewer with `bash harness/tools/bench.sh` at `audit_level: strict`. They
> are required when a feature: processes > 1,000 items, involves I/O operations
> (DB, API, file), has concurrency/parallelism concerns, or uses caching or
> memoization.

### Framework per stack

| Stack | Tool | When unavailable |
|---|---|---|
| python | `pytest-benchmark` (mark tests with `@pytest.mark.benchmark`) | `bench.sh` reports record-only |
| typescript / node | `vitest bench` (if configured) | record-only |
| rust | `cargo bench` (if `benches/` configured) | record-only |
| java / android | checklist-only (measure manually if needed) | checklist-only |
| generic | checklist-only | checklist-only |

### Baselines (`harness/baselines.json`)

Starts empty (`{}`). After the first measurement of a function/test, add an entry:

```json
{
  "test_send_email_throughput": {
    "mean_ms": 42.3,
    "thresholds": {
      "mean_ms": { "warning": 1.5, "critical": 2.0 }
    }
  }
}
```

- `mean_ms` is the reference measurement (milliseconds; `mean * 1000` from
  pytest-benchmark).
- Multipliers: exceeding `warning` logs a warning; exceeding `critical` rejects
  approval at `strict`.

### Report (compact — only when benchmarks were required)

```markdown
## Performance Benchmarks
- Scenario: <what was measured>
- Result: <mean/p95 or framework output excerpt>
- vs baseline: ok (<ratio>x) | warning | REGRESSION
```

Without a baseline, `bench.sh` records values and warns; it never blocks.

A transient `harness/.bench-last.json` may be produced by the benchmark run;
delete it before closing the session (it is not user state).
<!-- harness:module:performance-benchmarks:end -->

<!-- harness:module:security-audit:start -->
## Security Audit Checklist (security-audit module)

> Appended by the harness `security-audit` module. The reviewer applies this
> checklist manually at `audit_level: basic`, and runs
> `bash harness/tools/audit-security.sh` at `standard` and above. Findings are
> recorded in the feature's progress entry with severity (HIGH/MEDIUM/LOW),
> description, and resolution or explicit waiver.

### A01 Broken Access Control
- [ ] Sensitive endpoints and operations require authentication.
- [ ] Role/permission checks enforced server-side, not only in the UI.

### A02 Cryptographic Failures
- [ ] No hardcoded secrets; credentials come from environment or a secrets manager.
- [ ] Cryptographic randomness from the stack's secure source (`secrets`, `crypto`).
- [ ] Sensitive data encrypted at rest and in transit where required.

### A03 Injection
- [ ] SQL via parameterized queries only — never string concatenation.
- [ ] No `shell=True` or unsanitized shell interpolation; file paths validated against traversal.
- [ ] HTML/JSON output escaped (XSS) when data reaches a UI.

### A04 Insecure Design
- [ ] External input validated (type, range, format, length) at the boundary.
- [ ] Rate limiting and retry-with-backoff considered for public endpoints.

### A05 Security Misconfiguration
- [ ] No debug mode, verbose stack traces, or default credentials in production config.
- [ ] Error messages generic externally; internal detail logged securely, without PII.

### API security headers (when serving HTTP)

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Content-Security-Policy: default-src 'self'
Strict-Transport-Security: max-age=31536000; includeSubDomains
Permissions-Policy: <deny unused browser capabilities>
Referrer-Policy: no-referrer
Cache-Control: no-store          # only for sensitive responses
```

(Deprecated `X-XSS-Protection` is intentionally not listed.)

### Automated scanning (audit_level standard and above)

Run `bash harness/tools/audit-security.sh` from the project root. The script uses
the stack's tools when installed and degrades to this checklist otherwise — it
must never be a blocker by itself; HIGH findings it reports reject the approval.

### Report format (in the review file)

```markdown
## Security Audit
- Method: manual checklist | audit-security.sh
- Findings:
  - [HIGH/MEDIUM/LOW] <description> — <resolution or waiver>
- Result: PASS | REJECTED (HIGH findings unresolved)
```
<!-- harness:module:security-audit:end -->
