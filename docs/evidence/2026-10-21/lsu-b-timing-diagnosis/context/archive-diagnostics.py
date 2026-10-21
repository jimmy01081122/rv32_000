"""Publish diagnostic evidence separately from immutable baseline/A/B archives."""
from pathlib import Path
import datetime, gzip, hashlib, json, re, shutil
root=Path('/workspace/rv32_000');src=root/'build/experiments/lsu-b-diagnosis-v1'
dest=root/'docs/evidence/2026-10-21/lsu-b-timing-diagnosis'
assert not dest.exists();dest.mkdir(parents=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rawsha(p):
 h=hashlib.sha256()
 with gzip.open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def load(p):return json.loads(p.read_text())
assert load(src/'diagnostic-review.json')['passed']
assert load(src/'runtime-cleanup.json')['container_removed']
inventory=[]
def copy(p,name,compress=False):
 target=dest/name;target.parent.mkdir(parents=True,exist_ok=True);assert not target.exists()
 if compress:
  with p.open('rb') as inp,target.open('xb') as f:
   with gzip.GzipFile(filename='',mode='wb',fileobj=f,compresslevel=6,mtime=0) as zipped:shutil.copyfileobj(inp,zipped)
  assert rawsha(target)==sha(p)
 else:
  shutil.copyfile(p,target);assert sha(target)==sha(p)
 inventory.append(dict(source=str(p.relative_to(root)),source_sha256=sha(p),source_bytes=p.stat().st_size,archive=name,archive_sha256=sha(target),archive_bytes=target.stat().st_size,encoding='gzip' if compress else 'identity'))
for p in sorted(src.iterdir()):
 if p.is_file():
  folder='reported-paths' if p.suffix=='.rpt' else 'connectivity' if p.name.endswith('connectivity.jsonl.gz') else 'context'
  copy(p,f'{folder}/{p.name}')
for p in sorted((src/'native').rglob('*')):
 if p.is_file():copy(p,'native/'+str(p.relative_to(src/'native')))
native=load(src/'native-probes.json')
for name in sorted(native['input_sha256']):
 p=root/name
 if p.suffix=='.odb':continue # below: original archived checkpoints or synthesis gzip
 assert sha(p)==native['input_sha256'][name],name
 copy(p,'inputs/native-guards/'+name,compress=p.name.endswith('.v'))
inputs=load(src/'replay-inputs.json')
for row in inputs['restorations']:
 if '-synthesis.odb' not in row['restored']:continue
 name=Path(row['restored']).name
 p=root/row['source'];assert sha(p)==row['source_sha256'] and rawsha(p)==row['raw_sha256']
 copy(p,'inputs/synthesis-checkpoints/'+name+'.gz')
for candidate,record in inputs['implementations'].items():
 netlist=root/record['netlist']['path']
 stat=netlist.parents[4]/'reports/asap7/rv32_post_lsu_v1/base/synth_stat.txt'
 copy(stat,f'inputs/synth-stat/{candidate}.txt')
 implementation=root/record['implementation']['path']
 lowered=root/load(implementation).get('lowered_rtl_path','build/baseline-setup/rtl_lowered.v')
 copy(lowered,f'inputs/lowered/{candidate}.v.gz',compress=True)
 synth_log=netlist.parents[4]/'logs/asap7/rv32_post_lsu_v1/base/1_2_yosys.log'
 copy(synth_log,f'inputs/synthesis-logs/{candidate}.log')
 meta=root/record['final_metadata']['path']
 for corner in ('TT','SS','FF'):
  copy(meta.parent/corner/'clock_trials.json',f'inputs/original-timing/{candidate}/{corner}/clock_trials.json')
for row in load(src/'reported-path-comparison.json')['records']:
 p=root/row['source'];name=f'inputs/original-timing/{row["candidate"]}/{row["corner"]}/{p.name}'
 if not (dest/name).exists():copy(p,name)
copy(root/'docs/LSU_B_TIMING_DIAGNOSIS.md','inputs/diagnosis-report.md')
external=[]
routed_gzip={
 'baseline':'docs/evidence/2026-10-18/post-lsu-baseline/physical/5_1_grt.odb.gz',
 'A':'docs/evidence/2026-10-20/lsu-a-physical/physical/physical-14000ps-eco-clean-v1/5_1_grt.odb.gz',
 'B':'docs/evidence/2026-10-21/lsu-b/physical/physical-14000ps-eco-clean-v1/results/asap7/rv32_post_lsu_v1/base/5_1_grt.odb.gz',
}
for candidate,name in routed_gzip.items():
 p=root/name;expected=inputs['implementations'][candidate]['routed']['sha256']
 assert rawsha(p)==expected
 external.append(dict(candidate=candidate,archive_gzip=name,gzip_sha256=sha(p),raw_sha256=expected,restore_to=inputs['implementations'][candidate]['routed']['path']))
(dest/'external-checkpoints.json').write_text(json.dumps(dict(scope='Reuse immutable original routed databases; do not reroute or replace them',records=external),indent=2)+'\n')
(dest/'copy-inventory.json').write_text(json.dumps(dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_commit=native['source_commit'],records=inventory,note='Restore source path with identical bytes; encoding=gzip requires decompression. Identity copies of gzip sources remain gzip at the source path. Context helper filenames retain historical paths in their code.'),indent=2)+'\n')
(dest/'.gitattributes').write_text('* -text\n')
(dest/'README.md').write_text('''# B v1 timing diagnosis — 2026-10-21

**Diagnostic work is complete; B v1 remains timing rejected.** This separate
archive changes no original baseline/A/B evidence, CPU RTL, scored simulator,
physical construction policy, or acceptance rule. The current interpretation
and proposed next choices are in [the review](../../../LSU_B_TIMING_DIAGNOSIS.md).

The source checkout is `0804b7c37ad8a4b54a3391010ca608f024c1d4e6` on
`codex/lsu-b-marking`; its B CPU/physical inputs are unchanged from clean
`95ac0dd6451a1799f9f3fe948c7b74c02f5fccd2`. These are read-only analyses of
original completed implementations, not another synthesis/place/route run.

## Results and checks

- [Native collection](context/native-probes.json): 12 independent processes,
  real exit 0 and completion markers, unchanged guarded inputs and 204 pinned
  tool/platform hashes before and after. Nine original TT/SS/FF routed results
  reproduce within 0.000001 ps. Three SS synthesis views deliberately use zero
  wire delay and ideal clock; they do not qualify a physical clock.
- [Independent review](context/diagnostic-review.json): 72 selected cell/net
  decompositions, exact master/instance/pin connectivity of 534,342 synthesis
  cells, unchanged baseline simulator and all 2,060 indexed files in five old
  baseline/A/B archives checked. This is not full RTL/netlist equivalence.
- [Path comparison](context/native-path-comparison.json): worst FP data delay
  baseline/A/B is 9.609165/9.480563/12.214929 ns routed and
  6.518351/6.651498/8.455249 ns in the synthesis zero-wire view. Matching FP
  sink bit 115 also shows a 1.971862 ns pre-placement B-minus-baseline gap.
  Loaded cell arcs retain placement, fanout and slew effects.
- [Structural comparison](context/mapped-cone-comparison.json): the lowered
  FPU modules are byte identical; the routed critical paths contain
  105/106/137 original non-buffer mapped cells. Distinct structural hashes
  do not imply different logical functions. No particular opcode, optimizer
  pass or inevitable B architecture penalty is established.
- [Connectivity review](context/synthesis-connectivity-review.json): source
  parser counts match original Yosys statistics; all three recovered synthesis
  databases exactly match the recorded netlists after scalar-alias and OpenDB
  literal bracket/slash escape normalization. Earlier representation-only
  checker outputs are retained in context. The final checker is authoritative.
- B FF has two violating endpoints, −0.332734 and −0.298511 ps. The same
  ready-to-store-tracking path has +52.584854 ps in TT and −0.332734 ps in FF.
  No hold ECO was performed and no negative slack was waived.

## Contents and replay

`native/` keeps all original new tool outputs. `reported-paths/` extracts each
original worst group without mistaking the first printed block for the global
worst path. `inputs/` keeps original netlists, lowered RTL, synthesis checkpoints,
metadata, statistics and source guards. `connectivity/` retains the complete
OpenDB connection exports. `context/` contains exact scripts and receipts.

Verify this package from this directory:

```sh
sha256sum --strict --quiet -c SHA256SUMS
```

[Copy inventory](copy-inventory.json) binds each published copy to its original
repository path and SHA-256. For auditing the existing result, restore these
source paths in an isolated checkout: decompress `encoding=gzip` copies;
identity copies retain their original encoding. Existing files must have the
recorded hash before reuse. Restore the four temporary raw ODB paths listed in
`context/replay-inputs.json` from their gzip sources. Restore the original final
routed ODBs using [external checkpoint references](external-checkpoints.json).
The references bind to the old committed gzip files and verified raw hashes;
no duplicate routed DB is silently substituted.

For a fresh native replay, start with a fresh ignored
`build/experiments/lsu-b-diagnosis-v1` output directory containing only the helper
sources and restored original implementation inputs; do not prepopulate its
`native/`, `replays/` or result JSON. The pinned image is
`rv32ooo-orfs:8359fde-flat`, local ID
`sha256:92a37abacbbf91494f9a8078b45fe1f6688a533cf5c87d02599d28c5fe229b33`.
Use a disposable container named `rv32-lsu-b-diagnosis-v1`, user 1000:1000,
repository mounted at `/workspace`, pinned ORFS checkout at `/orfs-source:ro`,
and entrypoint `/bin/sleep infinity`. Do not run two large VFS tool runtimes
concurrently. `run-probes.py` requires fresh output paths and validates original
mapped/final identities; its exact commands and source guards are also saved.

`export-synth-connectivity.py` runs with pinned `openroad -python`; other Python
helpers run on the host. The dependency order is collection/export, reported
path extraction, connectivity/cone/path comparisons, then `review-diagnostics.py`.
Restore every input identity before repeating that review. The zero-wire
synthesis views have no CTS/route and their hold violations are diagnostic,
not a revision of the already qualified baseline/A operating points.

[Runtime cleanup](context/runtime-cleanup.json) records the idle-only container
removal and losslessly recoverable replay duplicate cleanup; pinned images and
original archives are retained. [Idle-cache compaction](context/idle-cache-compaction.json)
preserves original bytes/hashes in gzip for completed B intermediates. Restore
raw paths before old scripts require them. No original archive index changed.
''')
files=sorted(p for p in dest.rglob('*') if p.is_file())
(dest/'SHA256SUMS').write_text(''.join(f'{sha(p)}  {p.relative_to(dest)}\n' for p in files))
print(json.dumps(dict(indexed_files=len(files),copy_records=len(inventory),bytes=sum(p.stat().st_size for p in dest.rglob('*') if p.is_file())),indent=2))
