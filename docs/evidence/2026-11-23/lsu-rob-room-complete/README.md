# ROB-space physical completion evidence

Fresh native ROOM synthesis, the exact proved shared FPU, global-route, hold40,
uniform ready guard, independent TT/SS/FF trials and complete workload measurements.
The original baseline, fixed 10,000 ps memory and two-family targets are unchanged.
This is global-route research evidence, not detailed-route or tapeout signoff.

Stage checkpoint archives retain raw construction files. Independent STA reports
and all workload files are separate members. Failed capacity preparation and its
recovery are retained. The interrupted predecessor collection and its replay
receipt are also included. Exact parked images and historical caches are restored.
The prior complete functional archive is nested unchanged. Replay additionally
uses the original baseline, shared-FPU proof and A+B/arbitration reference archives;
their identities are checked by the retained independent reviewers.

Verify all public files and every decoded payload without extraction:

```sh
python3 experiments/lsu-rob-room-v1/verify_completion_archive.py docs/evidence/2026-11-23/lsu-rob-room-complete
```

Only extract verified evidence into a fresh review checkout. Member paths are
repository relative; original execution commands retain their original paths.
See [the result](../../../LSU_ROB_ROOM_REVIEW.md) and
[critical paths](../../../CRITICAL_PATHS.md).

The extra SS report binds all five ROB occupancy flops and all 32 address
outputs to the admitted 10 ns database and constraints. See
[the targeted path receipt](rob-count-SS.json).
The environment recovery loaded the synthesis image separately after the first
combined load exhausted VFS space. All three original image IDs and all eight
historical raw cache hashes were verified.

The working checkout retains the timing reports, workload results and split
archive. To materialize the large generated ROOM files for another native
review, allow about 2.1 GiB of free space and run from the repository root:

```sh
python3 experiments/lsu-rob-room-v1/restore_physical_cache.py
```

This verifies each public file, restores the mapping and nested stage checkpoints,
and checks every restored file against its recorded SHA-256.
