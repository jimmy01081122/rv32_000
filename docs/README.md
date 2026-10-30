# Documentation index

Updated 2026-10-30 (Asia/Taipei). Begin with current documents below. A historical PASS or
signoff label applies only to the source/configuration and checks in that record.

## Current documents

| Document | Responsibility |
| --- | --- |
| [Project README](../README.md) | Entry point and development commands |
| [Project plan](../PLAN.md) | Agreed direction, review process, proposed targets and milestones |
| [Status](STATUS.md) | Evidence and unresolved implementation/verification gaps |
| [Current architecture map](ARCHITECTURE_MAP.md) | Source-checked B diagram, editable SVG/Graphviz/Mermaid and candidate optimization directions |
| [Architecture](../architecture_spec.md) | Implemented structures and architectural obligations |
| [Micro-operations](../uop_spec.md) | Current packet/schema reference |
| [Workloads](WORKLOADS.md) | Approved main suites, targets and frozen v1 measurement contract |
| [Balanced FP32 proposal](FP32_BALANCED_PROPOSAL.md) | Approved control/DSP and matrix/ML selection and weights; source and numerical qualification |
| [Initial workload qualification](WORKLOAD_QUALIFICATION_2026-10-16.md) | Embench library blockers and PolyBench FP32 source/resource probes |
| [Approved Embench rerun](evidence/2026-10-17/embench-approved-rerun/README.md) | Clean-commit 19/19 native/Spike/DUT checks, diagnostic cycles, raw logs and hashes |
| [FP32 numerical qualification](evidence/2026-10-17/fp32-balanced-qualification/README.md) | Clean-commit 8/8 provisional cases, independent references, all outputs, numerical bounds and FFT ROI audit |
| [LSU candidate review](LSU_OPTIMIZATION_REVIEW.md) | Preregistered six-case sensitivity and A/B/C design tradeoffs |
| [LSU interface fixes](LSU_INTERFACE_FIX.md) | Backpressure / access-fault repair, assertion-enabled tests and archived regressions |
| [FIR/BiCG bottleneck review](FMA_BOTTLENECK_REVIEW.md) | Approved fast default, instruction contraction and measured load/store retirement waits |
| [FMA contraction review](FMA_CONTRACTION_REVIEW.md) | Off/fast policy, matched cycle/error data, finite FMA correctness fix and regression evidence |
| [Progress and baseline review](PROGRESS_REVIEW.md) | Updated FP toolchain evidence, honest progress gates and discussion proposals |
| [Frozen post-LSU baseline](evidence/2026-10-18/post-lsu-baseline/README.md) | Actual 10 ns TT/SS/FF closure, cell area, fixed-time memory and formal 27/27 evidence |
| [LSU A functional milestone](evidence/2026-10-19/lsu-a-functional/README.md) | Clean-source interface qualification and original full common-clock measurement |
| [LSU A physical and operating-point review](evidence/2026-10-20/lsu-a-physical/README.md) | Actual timing grid, area and complete 27-case comparison at both qualified clocks |
| [LSU A verification review](LSU_A_VERIFICATION_REVIEW.md) | Build/functional provenance and per-PC admission fixes, expanded unit cases and unchanged full-denominator results |
| [B complete validation](LSU_B_COMPLETE_VALIDATION.md) | Full B contract completion, FPU reset/transition proof, same-flow physical qualification and both 27-case results |
| [B completion raw evidence](evidence/2026-10-29/lsu-b-complete-validation/README.md) | Final reviews, native proof/timing, preserved failures, workload records and hashes |
| [FPU mapping repair](FPU_MAPPING_REPAIR.md) | Shared map, equivalence evidence and current qualification scope |
| [LSU B review](LSU_B_REVIEW.md) | Historical B v1 functional/cycle evidence and failed original-flow timing |
| [LSU B raw evidence](evidence/2026-10-21/lsu-b/README.md) | All27 diagnostic cases, binaries/netlist/ODB, actual timing failures and reproducible proof |
| [LSU B timing diagnosis](LSU_B_TIMING_DIAGNOSIS.md) | Original corner replay, mapped FP depth and cell/net delay comparison, TT/FF hold limits and next choices |
| [Session handoff](SESSION_HANDOFF.md) | Bring-up measurements, tool images and local evidence locations |
| [CI workflow](../.github/workflows/README.md) | Existing jobs, prerequisites and limits |
| [Physical flow](../physical/asap7/README.md) | ASAP7 setup status and current research limitations |
| [Constraint notes](../physical/asap7/constraint_notes.md) | Actual checked-in constraints and unresolved assumptions |

Numerical targets marked **proposed** require baseline qualification and user
discussion. Measured, implemented and planned are distinct statuses.
The RTL records what currently exists; ISA requirements and reviewed contracts
determine what it should do. Disagreement must be tracked and verified.

## Historical material

- [Archive guide](archive/README.md): superseded G0 plan, architecture and uop contracts.
- [Report index](../reports/README.md): AP0–AP5A research reports and their applicability.
- [Audit index](../audit/README.md): old spec reviews and milestone evidence.
- [Diagram provenance](../graph/README.md): historical AP5A image.

Raw results, archives and manifests remain at their original paths so existing
evidence can be traced. New results must identify their source SHA and exact
configuration. Update the current status when evidence changes; do not rewrite
an old measurement as if it had been rerun on current RTL.
