# Submission code review — 7 November 2026

Repository: https://github.com/Pulkit-10-0/pharma-path-nesfic

This review covers the current Python backend, forecast and dataset code,
React website, shared client modules, Android source, migrations, original CSV
experiments and notebook. Static checks and focused review were followed by
backend integration tests, web tests and Android export validation.

## English comments and original experiments

- Translated the four Hindi/Hinglish comments found in `02_build_demand.py` and
  `03_build_network.py` into English. The obsolete fixed-row-count expectation
  now explains that the count depends on the input's date range.
- Notebook code and explanatory text were inspected after decoding the JSON.
  Its comments were already English. Added explicit original-experiment context,
  a fallback to the included public CSV, explicit paths for generated experiment
  outputs and loading of `recommendations.csv` before using `rec`.
- The Hindi character in the mobile Unicode storage test is intentional input
  for multibyte chunk handling, not a comment; it remains part of that test.
- The original network script now writes the final product CSV once, after
  assigning unknown valuation and source metadata.
- Commit history and original-team attribution are preserved. See
  [SOURCE_ORIGIN.md](SOURCE_ORIGIN.md).

## Performance and correctness improvements

### Demand imports

Imports now batch product/location reads, existing-observation checks and inserts.
CSV parsing and XLSX reads stop after the 10,001st row, so oversized inputs can be
rejected before an entire larger file is materialised. The 5 MB, 10,000-row and
workbook expansion limits remain enforced.

Dry-run behaviour, row errors, unit validation, organisation/site scope,
idempotent file replay and atomic rejection of overlapping or invalid files
remain covered. Replaying an existing file also checks the caller's current
site scope and the current product units.

A disposable SQLite dry-run compared the original `fa7dd06` importer with this
revision, alternating three runs for one product/site and 400 observations:

| Measurement | Original | Reviewed |
| --- | ---: | ---: |
| SELECT queries per import | 802 | 5 |
| Median execution time on the review machine | 119.42 ms | 6.60 ms |

These are local diagnostic results, not hosted throughput or an availability
guarantee. Raw measurements: [import-benchmark.json](review-evidence/import-benchmark.json).

### Demand history

`GET /api/v1/demand` now applies pagination in SQL, with a stable date/ID order
and a separately counted total. Optional `measure`, `start` and `end` filters
preserve the old unfiltered behaviour when omitted. Invalid filters and site
scope are checked before data is returned.

An unevaluated chart requests only requested-demand observations needed for its
fourteen complete weeks, rather than downloading both measures across five
years. The worker still evaluates the full source history. Chart equivalence,
separate measures, bounded page loads and ordering have regression coverage.

### Local sign-in

The local development sign-in helper has a bounded wait and a project-named
default email. A failed helper can return to the normal sign-in form instead of
leaving the initial connection screen indefinitely. The hosted shared synthetic
credentials requested by the owner are preserved.

## Verification

| Check | Result |
| --- | --- |
| Full backend suite, disposable SQLite | 83 passed; one PostgreSQL-specific concurrency test skipped |
| Full backend suite, isolated PostgreSQL 16 | 84 passed, including competing stock approvals |
| PostgreSQL migrations and ORM schema check | Passed; no unrecorded schema changes |
| Python lint for backend, scripts and tests | Passed |
| Website tests | 30 passed |
| Website TypeScript and production build | Passed |
| Android tests | 13 passed |
| Android TypeScript and lint | Passed |
| Android production JavaScript/asset export | Passed |
| Tracked Python and notebook-code syntax | Checked |
| Dataset file hashes | Verified against the preserved manifest |

Reproduce the normal checks with the commands in the repository's
[Product checks workflow](../.github/workflows/backend.yml). The PostgreSQL suite
requires a dedicated disposable database named `grd_test`; it is not run against
the hosted operating database.

## Publication and evidence scope

The new repository includes the existing dynamic dataset, provenance, tests,
deployment configuration, source notices, a current network screenshot and
[START_HERE.md](../START_HERE.md). Existing reviewer downloads continue to point
to their actual release in the previous repository.

The live website remains at https://pharma-path.onrender.com/ and is still
configured from the previous repository. The source changes documented here
are published in the new repository; provider settings and live records were
not changed by this code review.

No new forecast-accuracy or pilot-impact claim was created. The observed public
benchmark remains separate from generated operating data. A physical Android
camera/QR test and field recording remain pending; an Android asset export is
not evidence of a successful camera test or a newly signed APK.
