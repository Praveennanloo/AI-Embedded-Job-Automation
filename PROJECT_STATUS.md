# Project Status

## Current verified status

- Scope: existing AI Embedded Job Automation project; no new product features added.
- Python syntax: PASS.
- Core imports: PASS.
- Automated tests: **100 passed, 0 failed** at final audit.
- API root endpoint: locally verified after application startup with scheduling disabled in doctor mode.
- Keyword false-positive regression checks: PASS.
- Provider live availability: **not claimed here**; external provider/network behavior must be verified from the user's machine.

## Target pipeline

Provider retrieval -> normalization -> target filtering -> entry-level filtering -> scoring/ranking -> persistence -> API response.

## Bugs fixed in this audit

1. Keyword matching used substring matching, producing false positives such as `intern` inside `international` and `arm` inside `harmonic`.
2. Role classification bypassed the corrected keyword matcher and could classify unrelated marketing/account jobs as Embedded/Embedded Linux.
3. Target-document matching allowed bare `linux kernel` text to pass without additional embedded/hardware context, contrary to the existing regression requirement.

## Clean source policy

The source distribution excludes local virtual environments, Git history, Python caches, generated logs, local SQLite data, and historical backup copies. Those are environment/state artifacts, not required source for deployment or review.
