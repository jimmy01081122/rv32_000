# AP5B post-LSU v1 physical research baseline

This directory implements the approved **global-route research** boundary.
It does not establish detailed-route closure. See the input contract in
`baselines/ap5b-post-lsu-v1/manifest.json`: the frozen result is 10 ns and
22,081.1184 µm², with all 27 formal workloads passing. The complete raw evidence
is in `docs/evidence/2026-10-18/post-lsu-baseline/`.

Use the ORFS commit and parent image digest in `../toolchain.lock`.
The image contains no ORFS git history, so use a separate clean checkout:

```sh
git clone --filter=blob:none --no-checkout https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts.git build/baseline-setup/ORFS
git -C build/baseline-setup/ORFS sparse-checkout set flow/scripts flow/util flow/platforms/common
git -C build/baseline-setup/ORFS checkout --detach 8359fde81991e6118b15b8a93fcde606b577794d
```

On this 32 GB host Docker uses VFS. A regular image pull exhausted space while
registering cumulative layers. The pinned image was instead exported as a flat
filesystem using crane v0.22.1 and imported locally. This changes image packaging,
not the tool binaries or ASAP7 files. The upstream digest, export platform,
local image ID, actual binary hashes and platform file hashes must all accompany
results; a local tag alone is insufficient provenance.

The crane Linux x86-64 release archive SHA256 is
`0ab7a1d6932a213aed964ce97666c3077fe691c8606413674a8b3e0b9ec4cda0`.
After verifying that archive, use Bash with `set -euo pipefail`:

```sh
build/baseline-setup/crane/crane export --platform=linux/amd64 \
  openroad/flow-ubuntu22.04-builder@sha256:fd940893eafe2410ed9513441f91e15be5fe9f73a29d68e5655ad62a39ac2e9a - \
  | docker import \
      --change 'ENV PATH=/usr/local/bin/wrapped-cc:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin' \
      --change 'WORKDIR /OpenROAD-flow-scripts' - rv32ooo-orfs:8359fde-flat
```

The driver requires `build/baseline-setup/rtl_lowered.v`, generated with the
pinned sv2v v0.0.12, `-DSYNTHESIS --top=rv32_ooo_core -Irtl/pkg` and the ordered
source list in `sim/scripts/rv32_ooo_core.f`. It records its hash and all RTL
hashes. Run an explicitly labeled attempt:

```sh
python3 scripts/run_baseline_physical.py --period-ps 5500 --jobs 2 --label trial1
```

`5500` is an exploration constraint, not an achieved period. Each attempt has
its own output directory and refuses to overwrite an existing `run.json`.
After correcting an infrastructure dependency, `--resume-reason TEXT` may resume
a finished failed attempt only when all recorded build input hashes still match;
the prior run record and log are retained as a separate attempt.
To avoid another VFS filesystem copy, `--container ID` can reuse a running
container with the exact image and `/workspace` plus `/orfs-source` mounts;
the driver verifies these before executing. Read-only ORFS source, image platform
files and project flow configuration remain separately identifiable.

The canonicalization hook simplifies mux expressions before extracting DFFs
and memory writes. It must prove that no process or latch remains and pass
`check -assert`; downstream synthesis, mapping and physical repairs use the
pinned ORFS flow. A preprocessing failure is not a usable checkpoint. Global
placement and global routing seeds are fixed at 1; jobs are fixed at 2. I/O maximum delays are 1100 ps; minimum input/output
delays are explicitly 0 ps, with no false paths.

TT libraries drive construction, with TT/SS/FF timing views. The upstream platform
temperature labels disagree with its Liberty headers: the actual RVT libraries
are TT 0.70 V/25°C, SS 0.63 V/100°C and FF 0.77 V/0°C. Use library contents as
evidence. Final STA runs in a fresh process for each corner to avoid mismatching
the PDK's conditional and non-unate XOR arcs in a shared timing graph.
`report.tcl` evaluates explicit clock trials on the same global-route
database and nominal wire RC. Never derive a claimed clock from slack algebra.
Require valid setup/hold, complete timing constraints and inspected electrical
checks before filling the baseline's physical fields.

The pinned SIMPLE libraries also contain CON→SN output-port timing groups in
FAx1/HAxp5 that OpenSTA warns about (`STA-1212`). The bounded
[`audit_asap7_adders.py`](../../../scripts/audit_asap7_adders.py) tool checks their
Boolean functions, all 144 functional input/output transitions, 30 independent
min/max STA paths and three negative controls. It preserves the original models
and warnings. The full-core analysis requires that audit and verifies live binary
and library hashes; this does not validate analog characterization or OCV.

After a completed implementation, collect the three independent corner reports:

```sh
python3 scripts/analyze_baseline_physical.py --attempt build/baselines/ap5b-post-lsu-v1/physical-5500ps-trial1 \
  --container ID --adder-audit build/asap7-adders-fresh/summary.json
```

Collection still leaves `passed: false` pending inspection of constraints,
setup/hold, electrical checks, route restoration and area. `--adder-mapping abc`
on the implementation driver is a separately labeled tool-flow probe that skips
optional platform FA extraction. Its results must not be mixed with platform
adder mapping or with CPU A/B architecture experiments.

The first direct ORFS synthesis stalled in `proc_dlatch`; diagnostic preprocessing
attempts also exposed missing memory conversion, cleanup and an incompatible old
Yosys export command. These failed attempts must remain identified separately
from any successful run. The flow driver deliberately leaves `passed: false`;
`flow_completed` only records the Make command's exit status.
