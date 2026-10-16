# Historical document archive

Archived 2026-10-16 from maintenance revision
`1b266ed0b17aaec2dc598e5128fc57ab9edf56bb`.

| Document | Original role |
| --- | --- |
| [G0 PLAN](g0/PLAN.md) | Initial project proposal and milestone sequence |
| [G0 architecture](g0/architecture_spec.md) | v0.2.2 architecture contract and design intent |
| [G0 uop contract](g0/uop_spec.md) | v0.2.2 proposed packets, semantics and invariants |

Each file retains its original body after an archive notice. Legacy section
numbers in RTL comments and the [old audits](../../audit/README.md) refer to these
documents. Requirements in them remain useful review inputs, but implementation
or verification cannot be inferred from their former Frozen status.

Examples superseded by current implementation include static branch prediction,
one outstanding instruction fetch, four-entry LQ/SQ, G0 PRF port counts,
immediate branch recovery/reverse walking, and ROB result-storage assumptions.
The current references are [PLAN](../../PLAN.md),
[architecture](../../architecture_spec.md) and [uops](../../uop_spec.md).

Phase reports and raw evidence remain at their original locations:
[reports](../../reports/README.md), [audit](../../audit/README.md),
[results](../../results), and [ASAP7 results](../../physical/asap7/results).
Their filenames and recorded claims do not make them current signoff evidence.
