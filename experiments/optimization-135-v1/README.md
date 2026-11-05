# Directions 1, 3 and 5 — controlled first study

The user selected architecture-map directions 1, 3 and 5 on 2026-10-30.
This stage completes the already-defined first comparisons: isolated A in the
new common physical flow, read-only FP scheduling/arbiter observations, and
FPU path/latency/throughput analysis. Keep the original frozen workloads,
fixed 10 ns memory and independent performance/area targets. There is no A+B
candidate or automatic baseline promotion.

Direction 1 uses the previously verified linked A netlist, shared FPU and
original A functional provenance. `run_A_physical.py` calls the unchanged B
GRT and hold40 stage functions under separate A identity contracts. The exact
accepted Tcl/config/tool inputs remain pinned. Its final guard contract binds
the actual completed A predecessor before `guard_A.py` applies the same single
BUFx2 input guard, original-connectivity proof and full route. Independent
TT/SS/FF processes and strict final review remain necessary.

Directions 3 and 5 first use all retained baseline/A/B profiles, then augment
read-only observation where the existing counters cannot resolve the hypothesis.
Observer off/on and original-model outputs, cycles and per-PC counts must match.
Test fixtures must exercise nonzero contention/blocking and reject wrong signal
interpretation. Overlapping counts are not saved-cycle estimates; a head opcode
is not the functional unit's own latency. No partial workload result replaces
the frozen full-suite score. Candidate implementation choices follow the evidence
and the user's joint architecture review.

Original frozen archives remain unchanged. Completed working checkpoints were
losslessly compacted with hash-checked receipts; raw OpenDB inputs must be restored
before a tool that requires them is rerun. Image/PDK identities and final acceptance
limits do not change.

## Completed study status (2026-11-05)

See [the measured review](../../docs/OPTIMIZATION_135_STUDY.md). All 81 retained
profiles and 27 observer off/on pairs pass. Six real instruction controls exercise
nonzero completion contention and preserve the full ordered retirement trace.
A now completes the identical shared-FPU/GRT/hold40/ready-guard flow at clean
`8a1c582`. Independent TT/SS/FF qualifies 9,400 and 10,000 ps; the actual adjacent
9,300 ps SS setup failure is −52.245 ps. Area is 21,602.442420 µm², 1.002643×
the same-flow baseline and 0.978322× the original frozen baseline.
Both new A full-27 replays at frozen `bf6702c` pass 3,629 numerical values and
per-PC retired work. Embench/FP32 are 1.045830×/1.078255× at 100 MHz and
0.765250×/0.737524× at 106.38 MHz. Fixed 10 ns memory is sampled after 18.8 ns
in the latter case. The original A functional qualification is revalidated,
not rerun as a fresh full Spike qualification. Both speed goals remain unmet.
The [completion archive](../../docs/evidence/2026-11-05/optimization-135-A/README.md)
preserves the new results separately from the first observer study.

The first native attempt supplies no physical qualification: its unpublished
tmpfs outputs were lost when the environment stopped. The successful replacement
saves automatic verified stage checkpoints below. Publication was corrected to
stream `tar` through `docker exec`, because daemon-side `docker cp` saw the
underlying bind view instead of the container's private mount. Every output
byte/link was verified before unmount and independent STA. Original failed
attempts and controls remain recorded.

Actual diagnostic output is at `/tmp/rv32-opt135`; the full archive is also saved
as [a portable repository bundle](../../docs/evidence/optimization-135-study-2026-10-30.tar.gz).
The temporary extracted copy is `/tmp/rv32-opt135/archive`. These are source-hash-bound host observations,
not a new clean-commit full architectural qualification or a partial-suite score.
The v1 observer controller accepted B; baseline/A stopped on differing ELF path
labels. The v2 controller validates that path label and requires every other log
byte to match. Failed v1 data is retained, and completed B observations are reused
without changing their source or model bytes.

```bash
python3 experiments/optimization-135-v1/preflight_A.py
python3 experiments/optimization-135-v1/analyze_retained.py --repo "$PWD" --output /tmp/new-retained-study
python3 experiments/optimization-135-v1/run_observer.py --repo "$PWD" --output /tmp/new-observer-study
g++ -std=c++14 -O2 -Isim/tb experiments/optimization-135-v1/test_observer_adapter.cpp -o /tmp/fp-observer-adapter-test
/tmp/fp-observer-adapter-test
python3 experiments/optimization-135-v1/verify_study_archive.py /tmp/rv32-opt135/archive
```

The new harness uses the retained model archive and Verilator runtime objects,
the local v4.038 headers and host g++. Build commands and every input hash are
saved. The adapter reads const signals only; its diagnostics exclude flush
cycles. Issue/first-valid/grant observations include speculative work and are
not retirement latency measurements. Inputs with completions outside the ROI
are excluded from pair histograms; outstanding work is dropped on flush.

Before native A construction, verify available output storage, commit the source,
verify the fixed image/tool/PDK manifest, and use a fresh native runtime mounted at
`/workspace` and `/orfs-source`. `run_A_physical.py` then uses the unchanged
accepted native construction functions. Independent corner checks and actual
adjacent-period failures remain required after construction. A preflight PASS
does not qualify timing, area or system speed.

### Storage recovery on 2026-10-31

Docker/network access was approved and the first study commit was pushed.
Two unregistered VFS copies from the failed create were positively identified;
the complete copy matched the 204-file tool/platform manifest before its contents
were removed. Three unused project images were saved in a verified gzip archive,
including every image config and layer digest, before removing their tags and
explicitly inventoried build-cache records. The pinned ORFS image is unchanged.

The native runtime uses a private 4 GiB tmpfs at the same experiment output path
to avoid the VFS copies competing with intermediate OpenDB files on the 32 GiB
disk. The existing 3 GiB preflight applies to that actual output filesystem.
The previous B GRT used about 1.14 GiB of intermediate databases and less than
3.7 GiB peak process memory; the host has an 8 GiB memory limit. Native commands,
placement/route policy, tool/PDK bytes and acceptance thresholds are unchanged.
After construction, copy and hash-check every output onto the host, then detach
the private tmpfs inside the container before running the unchanged independent
STA collectors against the shared host paths. The runtime's SYS_ADMIN capability
is used only for that private mount operation. Keep recovery/backup/publication
receipts in the experiment's ignored working directory.

### Durable checkpoints after the November 5 restart

The initial native container stopped on November 3 without OOM; on November 5
its tmpfs was empty. No native completion or timing result is admitted from that
attempt. The separate October 31 A measurement finished 27/27 on durable storage.

`run_A_physical.py --label v2` uses a fresh `attempt-v2` namespace and saves each
completed GRT/hold40/guard stage automatically before proceeding. `checkpoint.py`
checks every archive member, decoded file SHA/size and relative symlink, then
fsyncs the archive and receipt. Controller progress and the bound guard contract
also go directly to durable storage. Five negative controls cover changed bytes,
missing/duplicate members, existing checkpoints and escaping links. Native flow
functions, PDK/tool identities, timing policy and acceptance remain unchanged.

Inside the existing disposable container, a nonrecursive bind of `/workspace`
to `/run/rv32-durable` exposes the underlying host directory without the nested
tmpfs mount. Its host-visible marker and distinct filesystem are verified before
launch. SYS_ADMIN is used for this private bind and eventual tmpfs detachment.
A detached supervisor stores the native controller log on the host, then attempts
full publication and the unchanged independent STA collectors. A stage checkpoint
is a recovery artifact, not physical closure. The complete physical review and
adjacent failing clock point are still required.

### Completed admission and portable verification

`review_physical_A.py` reuses the unchanged accepted guard reviewer and collectors,
revalidates the full shared-FPU proof/mapping link and A source chain, and checks
native commands against both baseline and B. Only four explicit variant path
arguments are normalized. Original clock/corner/area/electrical limits remain.
`review_measurement_A.py` binds the original qualified executable and frozen A
source independently of the current B worktree; all 27 cases, 3,629 numerical
values and per-PC work are mandatory. Source-link, workload-admission and
publication negative controls are included in the archive.

```bash
python3 experiments/optimization-135-v1/verify_completion_archive.py   docs/evidence/2026-11-05/optimization-135-A
```

The verifier streams split files without extracting them, verifies the combined
archive identity and every decoded member, and rejects missing/duplicate/unlisted
entries. This proves archive integrity; the separately recorded reviewers supply
functional/physical admission. The three native checkpoint tarballs are original
bytes and include the original raw OpenDB files. Subsequent independent STA
outputs are archived separately. `archive_A_completion.py` creates a fresh output
only and records native source commit separately from archive-parent commit and
worktree status. Large tool-image payloads are excluded; identity/restore receipts
are included. Final environment receipts supersede earlier temporary cold-cache
states. Historical working gzip caches must be restored before old direct-file
reviewers are rerun; original committed evidence is unchanged.
