# G0 Freeze Verification Evidence — v2 Response

**Date:** 2026-08-08
**Responding to:** `/home/a/g0_independent_verification_v2.md`

## File hashes after v2 fixes

```
82bc7330bf247babc307dfa79a11e96b2b5ea8f1c95ba13474cc5f08866f767d  architecture_spec.md  (v0.2.1)
3db7b02b81fe53632b8b37f352963a4aa603d13c5f6cf02b59e9d7e8c4d0d9ba  uop_spec.md           (v0.2.1)
6879322214299ad88ed7b1c3d6752ad6f40bb41f1d7a804a35da3f4eb735f2e1  PLAN.md               (v1.1, unchanged)
```

---

## NEW-CRIT-01 — dmem_pending_t alias guard

**Finding:** `dmem_req_valid` tracks the request channel, not an in-flight response.

**Fix in `architecture_spec.md` §15.2 (lines 494–511):**
- Introduced `dmem_pending_t` struct: `valid` (set on `dmem_req_valid && dmem_req_ready`, cleared on `dmem_rsp_valid && dmem_rsp_ready`), `rob_tag`, `lq_tag`, `sq_tag`.
- Alias guard now compares against `dmem_pending.rob_tag.seq` while `dmem_pending.valid` is asserted.
- `dmem_pending` declared as normative source for stale load-response validation (§22.6).

**Verified:** `grep dmem_pending architecture_spec.md` → lines 508, 511 ✓

---

## NEW-CRIT-02 — data_valid semantics

**Finding:** `data_valid = src1.ready` conflates producer-readiness with data capture.

**Fix in `uop_spec.md` §22 (lines 1013–1016):**
- `data_valid` is set to `1` **only** when the SQ has physically captured the data bits.
- On allocation with `src1.ready == 1`: SQ attempts immediate PRF read on dedicated SQ port; if granted, `data_valid = 1`; if not granted (IQ issue wins contention), `data_valid = 0` and capture defers to writeback snooping.
- When `data_valid == 0`: SQ snoops accepted writeback buses each cycle.

**Verified:** `grep "data_valid" uop_spec.md` → line 1013 contains "not merely when `src1.ready` is asserted" ✓

---

## NEW-HIGH-01 — Store AGU issue readiness

**Finding:** Generic IQ readiness (`all sources ready`) contradicts intended address-only issue for stores.

**Fix in `architecture_spec.md` §17.3 (line 629) and `uop_spec.md` §22 (line 1016):**
- Architecture spec §17.3 adds explicit **Store AGU issue exception**: `src0`-only readiness for store uops in Integer IQ. `src1` ownership transfers to SQ at rename. IQ copy marks `src1 = SRC_NONE`. AGU does not read `src1`.
- `uop_spec.md` §22 capture rules confirm: "At rename, the IQ entry for a store marks `src1` as `SRC_NONE` in the IQ copy."

**Verified:** `grep "AGU does not read" architecture_spec.md` → line 629 ✓; `grep "AGU does not read" uop_spec.md` → line 1016 ✓

---

## NEW-HIGH-02 — Integer SQ store-data capture port frozen

**Finding:** Integer SQ store-data capture port/arbitration undefined.

**Fix in `architecture_spec.md` §6 and Appendix C:**
- `INT_PRF_READ_PORTS` changed from `2` to `3` (line 138).
- Port allocation defined (line 147): 2 ports for two-source IQ issue, 1 dedicated for SQ integer store-data capture, lower priority than IQ issue, defers to writeback snooping on contention.
- Appendix C item 4 (line 1283): Int PRF Read Ports and arbitration policy frozen.

**Verified:** `grep INT_PRF_READ_PORTS architecture_spec.md` → line 138: `= 3` ✓

---

## NEW-HIGH-03 — JAL in global redirect priority

**Finding:** JAL decode redirect missing from §11.3 global priority list.

**Fix in `architecture_spec.md` §11.3 (lines 344–358):**
- Priority list now has 6 levels: reset > trap/MRET > branch/JALR misprediction > **JAL decode redirect** > fetch retry > normal flow.
- Added rule: "Exactly one `fetch_epoch` increment shall be generated per cycle regardless of how many redirect sources are active."

**Verified:** `grep "JAL decode redirect" architecture_spec.md` → line 354 (in §11.3 priority list) ✓

---

## NEW-MED-01 — Trap free-list rebuild frozen

**Finding:** Appendix C showed two options, not a frozen choice.

**Fix in `architecture_spec.md` Appendix C item 7 (line 1310):**
- Frozen to: single-cycle combinational membership-mask rebuild (not sequential scan).
- Formula: `free_mask[p] = (p != p0) && !rrat_contains(p)`, computed in parallel across all physical registers.

**Verified:** `grep "membership-mask" architecture_spec.md` → line 1310 ✓

---

## All prior v1 checks (still passing)

| Check | Line | Status |
|---|---|---|
| B-01 `misa = 32'h4000_1120` | arch §18.2 L643 | PASS (unchanged) |
| B-02 `sq_entry_t` `data_domain`/`data_phys` | uop §22 L994–995 | PASS |
| B-03 no `inside`, no `unique case` | uop_spec.md | PASS (unchanged) |
| B-04 JAL in `fetch_epoch` list | arch §12.2 L370 | PASS (unchanged) |
| B-05 ROB alias guard | arch §15.2 L511 (now `dmem_pending`) | PASS (upgraded) |
| B-06 `mstatus` trap fields | arch §25.3 L1033 | PASS (unchanged) |
| B-07 `retire_valid`/`trap_valid` trace | arch §29.2 L1142 | PASS (unchanged) |
| C-01 PLAN rollback `dst.valid` | PLAN L807 | PASS (unchanged) |
| C-02 branch `src2` prose removed | uop §23.1 | PASS (unchanged) |
| C-03 versions/freeze headers | all three files | PASS (bumped to 0.2.1) |

## Summary

| Finding | Verdict |
|---|---|
| NEW-CRIT-01 `dmem_pending_t` | CLOSED |
| NEW-CRIT-02 `data_valid` semantics | CLOSED |
| NEW-HIGH-01 store AGU readiness | CLOSED |
| NEW-HIGH-02 INT PRF ports frozen | CLOSED |
| NEW-HIGH-03 JAL in priority | CLOSED |
| NEW-MED-01 trap recovery frozen | CLOSED |
| All 10 prior v1 checks | PASS |
