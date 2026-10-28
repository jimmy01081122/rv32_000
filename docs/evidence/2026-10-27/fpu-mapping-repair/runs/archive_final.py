from pathlib import Path
import argparse, gzip, hashlib, json, shutil, subprocess

ROOT = Path.cwd()
BASE = ROOT/'build/experiments/fpu-mapping-v1'
DEST = ROOT/'docs/evidence/2026-10-27/fpu-mapping-repair'
REL = Path('results/asap7/rv32_post_lsu_v1/base')
ap=argparse.ArgumentParser();ap.add_argument('--final',action='store_true');args=ap.parse_args()
selected={}
def add(p):
    if p.is_file() and not p.is_symlink(): selected[p]=Path('runs')/p.relative_to(BASE)
def glob(directory, pattern):
    for p in directory.glob(pattern):add(p)
def native(directory, results):
    for n in ('job.json','run.json','constraint.sdc','make.log','fp-source.v'):add(directory/n)
    glob(directory/'logs','**/*');glob(directory/'reports','**/*')
    for n in results:
        p=directory/REL/n
        if not p.exists():p=p.with_name(p.name+'.gz')
        if not p.exists():raise FileNotFoundError(p)
        add(p)
for n in ('baseline','A','B'):
    native(BASE/'keep-v2'/n,['1_2_yosys.v','fp_mapped.rtlil.json'])
    native(BASE/'shared-native-v1'/n,['1_2_yosys.v','1_synth.odb','1_2_yosys.sdc','1_synth.sdc'])
native(BASE/'shared-unit-v1',['1_2_yosys.v','1_1_yosys_canonicalize.rtlil','fp_pre_abc.rtlil','fp_pre_abc.rtlil.json','fp_mapped.rtlil','fp_mapped.rtlil.json'])
native(BASE/'shared-unit-repeat-v1',['1_2_yosys.v','fp_mapped.rtlil.json'])
for directory in ('shared-linked-v1','shared-readback-v1','mapping-cec-v2','formal-controls','review-controls-v2'):
    glob(BASE/directory,'**/*')
for directory in ('keep-v1','equivalence-pre-v1','equivalence-pre-v2','equivalence-pre-v3','equivalence-pre-v4','equivalence-full-v1','equivalence-shared-v1'):
    d=BASE/directory
    for pat in ('*.py','*.json','*.eqy','*.log','*/run.json','*/job.json','*/make.log','work/logfile.txt','work/status','work/strategies_*/logfile.txt','work/strategies/**/logfile.txt','work/strategies/**/status','work/strategies/**/*.sby'):
        glob(d,pat)
for v in (1,2,3,4,5,6,7,8):
    d=BASE/f'gate-sim-v{v}'
    for pat in ('*.json','*.log','*.ys','*.v','*.py','driver-used.cc'):glob(d,pat)
add(BASE/'gate-sim-v4/model.cc')
glob(BASE/'gate-sim-v1/include','**/*.h')
for n in ('mapping-comparison-v1.json','repeat-comparison.json','unit-readback-review.json','unit-readback.ys','unit-readback.log','unit-from-verilog.json','link-replay-review.json','state-cut-review.json','state-cut-negative-review.json','state-cut-negative.log','preservation-review.json','runtime-cleanup.json','archive_evidence.py','archive_final.py','host-compiler.json','old-archives-review.json','native-review.json','finalize_result.py','documentation-review.json','validate_archive.py','host-test-scheduling.json'):
    add(BASE/n)
for pat in ('*compaction.json','*controller.log'):glob(BASE,pat)
add(BASE/'keep-v2/pipeline.json');add(BASE/'shared-link-replay-v1/link-manifest.json')
if args.final:
    qualification=json.loads((BASE/'gate-sim-v9/qualification.json').read_text())
    if not qualification.get('passed'):raise ValueError('gate regression must finish successfully before final archive')
    for pat in ('*.json','*.log','*.py'):glob(BASE/'gate-sim-v9',pat)
    add(BASE/'gate-sim-v9/model.cc')
    add(BASE/'result.json')
# Snapshot the current review tools and every hash-guarded input of completed jobs.
for directory in ('experiments/fpu-mapping-v1','physical/asap7/fpu-isolated','physical/asap7/baseline'):
    for p in (ROOT/directory).iterdir():
        if p.is_file():selected[p]=Path('inputs')/p.relative_to(ROOT)
for n in ('scripts/run_physical_job.py','docs/evidence/2026-10-18/post-lsu-baseline-preparation/environment/physical-tool-platform-sha256.txt'):
    p=ROOT/n;selected[p]=Path('inputs')/n
sha=lambda data:hashlib.sha256(data).hexdigest()
for spec in list(selected):
    if spec.name!='job.json':continue
    report=spec.with_name('run.json')
    if not report.exists() or not json.loads(report.read_text()).get('flow_completed'):continue
    for guest,h in json.loads(spec.read_text())['inputs'].items():
        p=ROOT/Path(guest).relative_to('/workspace')
        if sha(p.read_bytes())!=h:raise ValueError('completed native input changed: '+guest)
        if p not in selected:selected[p]=Path('inputs')/p.relative_to(ROOT)
selected[ROOT/'experiments/fpu-mapping-v1/gate_driver.cc'] = Path('inputs-final/experiments/fpu-mapping-v1/gate_driver.cc')
DEST.mkdir(parents=True,exist_ok=True)
records=[]
for source,rel in sorted(selected.items()):
    raw=source.read_bytes(); compressed=source.suffix=='.gz'
    decoded=gzip.decompress(raw) if compressed else raw
    encode=not compressed and len(raw)>131072
    target=DEST/(str(rel)+('.gz' if encode else ''))
    encoded=gzip.compress(raw,compresslevel=6,mtime=0) if encode else raw
    if target.exists():
        if target.read_bytes()!=encoded:raise ValueError('refusing changed archive payload: '+str(target))
    else:
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(encoded)
    check=gzip.decompress(encoded) if compressed or encode else encoded
    if check!=decoded:raise ValueError('lossless roundtrip failed')
    records.append(dict(source=str(source.relative_to(ROOT)),stored=str(target.relative_to(DEST)),encoding='gzip' if compressed or encode else 'identity',source_sha256=sha(raw),decoded_sha256=sha(decoded),stored_sha256=sha(encoded),decoded_bytes=len(decoded),stored_bytes=len(encoded)))
previous=json.loads((DEST/'copy-inventory.json').read_text())['records']
merged={r['stored']:r for r in previous}
merged.update({r['stored']:r for r in records})
records=list(merged.values())
(DEST/'copy-inventory.json').write_text(json.dumps(dict(final=args.final,records=records),indent=2)+'\n')
print(json.dumps(dict(final=args.final,files=len(records),stored_bytes=sum(r['stored_bytes'] for r in records),decoded_bytes=sum(r['decoded_bytes'] for r in records))))
