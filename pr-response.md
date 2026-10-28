# PR Response Doc — CineLog Watchlist Feature

## AI Usage

Codex inspected the starter models, collection service, tests, and the six review comments on CodePath's PR #1. It is helping prepare code changes, tests, the rebase, commit-history cleanup, and submission verification. The final record will identify completed assistance and verification. Comments 4 and 5 are awaiting Brian's own design reasoning.

## Comment 1 — Rename

**What I did:** Renamed `save_to_watchlist()` to `add_to_watchlist()` in `services/watchlist_service.py`, including the import and endpoint call in `routes/watchlist/watchlist.py`. This matches `add_to_collection()` and the project's `verb_to_noun` convention.

**How I verified:** Searched Python files across the repository for both names to identify the definition, import, and call. Test results will be recorded after execution.

## Comment 2 — Deduplication

**What I did:** Followed `add_to_collection()` in `services/collection_service.py`: after checking that the film exists, query for an existing entry matching both `user_id` and `film_id` with `filter_by(...).first()`. The collection service raises `AlreadyInCollectionError` on a match; the watchlist now raises `AlreadyInWatchlistError` before inserting or committing. Including both IDs keeps separate users' lists independent.

**How I verified:** The added duplicate regression test will check that the second add raises the domain error and exactly one row remains; a separate edge case will cover different users saving the same film. Full-suite results are recorded below after execution.

## Comment 3 — Missing test

Pending.

## Comment 4 — Default visibility

**My position:** Pending Brian's decision.

**Reasoning:** Pending Brian's reasoning.

**Tradeoff acknowledged:** Pending.

## Comment 5 — Sort order

**My position:** Pending Brian's decision.

**Reasoning:** Pending Brian's reasoning.

**Engagement with reviewer's point:** Pending.

## Comment 6 — Rebase

Pending.

## PR Description

Pending final verification and design decisions.
