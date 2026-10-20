#!/usr/bin/env python3
"""Reproduce sv2v lowering with hashed inputs; run in the pinned synthesis image."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
import subprocess
from baseline_contract import ROOT,MANIFEST,load,check_rtl,sha


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--compare',type=Path,help='existing lowered RTL to verify without overwriting it')
    parser.add_argument('--experiment',type=Path,help='explicit frozen candidate contract; baseline default remains strict')
    args=parser.parse_args()
    out=args.out.resolve()
    if not out.is_relative_to(ROOT/'build'):parser.error('output must be under build/')
    summary=out.with_suffix('.lowering.json');log=out.with_suffix('.lowering.log')
    if any(p.exists() for p in (out,summary,log)):parser.error('choose fresh output paths')
    manifest=load()
    if args.experiment:
        from experiment_contract import load_experiment
        experiment,manifest=load_experiment(args.experiment)
    else:check_rtl(manifest)
    tool=shutil.which('sv2v')
    if not tool:parser.error('sv2v missing; use rv32ooo-syn:g1')
    version=subprocess.check_output([tool,'--numeric-version'],text=True).strip()
    if version!='0.0.12':parser.error('expected pinned sv2v 0.0.12')
    filelist=ROOT/'sim/scripts/rv32_ooo_core.f'
    files=[line.strip() for line in filelist.read_text().splitlines() if line.strip() and not line.startswith('#')]
    inputs={name:sha(ROOT/name) for name in files}
    # Preserve the physical build's SYNTHESIS preprocessing boundary.
    command=[tool,'--top=rv32_ooo_core','-DSYNTHESIS','-I','rtl/pkg',*files]
    out.parent.mkdir(parents=True,exist_ok=True)
    report={'scope':'RTL-to-Verilog lowering only, not functional or physical qualification',
            'started_utc':datetime.now(timezone.utc).isoformat(),'command':command,
            'manifest_sha256':sha(MANIFEST),'filelist_sha256':sha(filelist),
            'rtl_files_sha256':inputs,'sv2v_version':version,'sv2v_binary_sha256':sha(Path(tool)),
            'wrapper_sha256':sha(Path(__file__)),'passed':False}
    if args.experiment:
        report.update(experiment_id=experiment['experiment_id'],experiment_manifest_sha256=sha(args.experiment))
    summary.write_text(json.dumps(report,indent=2)+'\n')
    with out.open('wb') as output,log.open('wb') as errors:
        result=subprocess.run(command,cwd=ROOT,stdout=output,stderr=errors)
    report.update(returncode=result.returncode,lowered_rtl_sha256=sha(out),log_sha256=sha(log),
                  finished_utc=datetime.now(timezone.utc).isoformat(),
                  input_identities_unchanged=all(sha(ROOT/name)==digest for name,digest in inputs.items()))
    report['passed']=result.returncode==0 and report['input_identities_unchanged']
    if args.compare:
        reference=args.compare.resolve()
        report.update(compare=str(reference.relative_to(ROOT)),compare_sha256=sha(reference),
                      byte_identical=sha(reference)==sha(out))
        report['passed'] &= report['byte_identical']
    summary.write_text(json.dumps(report,indent=2)+'\n')
    print('sv2v lowering', 'PASS' if report['passed'] else 'FAIL',report['lowered_rtl_sha256'],flush=True)
    raise SystemExit(0 if report['passed'] else 1)


if __name__=='__main__':main()
