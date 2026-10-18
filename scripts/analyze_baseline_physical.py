#!/usr/bin/env python3
"""Collect independent TT/SS/FF timing trials; collection alone is not closure."""
import argparse
import json
from pathlib import Path
import re
import subprocess
from baseline_contract import ROOT,sha,load,check_rtl
from run_baseline_physical import IMAGE
from audit_asap7_adders import validate as validate_adder_arcs


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--attempt',type=Path,required=True)
    parser.add_argument('--container',required=True)
    parser.add_argument('--label',default='independent-sta')
    parser.add_argument('--adder-audit',type=Path,required=True,help='summary.json from audit_asap7_adders.py')
    parser.add_argument('--periods-ps',nargs='+',type=int,
                        default=[2500,3000,3500,4000,4500,5000,5500,6000,7000,8000,10000,12000,14000,16000,20000])
    args=parser.parse_args()
    if not re.fullmatch(r'[a-zA-Z0-9_-]+',args.label):parser.error('invalid output label')
    if args.periods_ps!=sorted(set(args.periods_ps)) or min(args.periods_ps)<=2200:
        parser.error('clock trials must be unique, increasing and above the fixed 2200 ps I/O budget sum')
    attempt=args.attempt.resolve()
    if not attempt.is_relative_to(ROOT/'build'):parser.error('attempt must be under repository build/')
    implementation=json.loads((attempt/'run.json').read_text())
    if not implementation.get('flow_completed'):parser.error('implementation command has not completed successfully')
    if implementation.get('construction_timing_corners')!=['TT']:
        parser.error('implementation must use the agreed TT-only construction view')
    manifest=load()
    check_rtl(manifest)
    if implementation['rtl_files_sha256']!=manifest['rtl_files_sha256']:
        parser.error('implementation RTL identities differ from the frozen baseline')
    for path,key in [('physical/asap7/baseline/config.mk','config_sha256'),
                     ('physical/asap7/baseline/lower_processes.tcl','process_lowering_sha256'),
                     ('build/baseline-setup/rtl_lowered.v','lowered_rtl_sha256')]:
        if sha(ROOT/path)!=implementation[key]:parser.error('implementation input changed: '+path)
    if sha(attempt/'constraint.sdc')!=implementation['sdc_sha256']:parser.error('implementation SDC changed')
    image_id=subprocess.check_output(['docker','image','inspect',IMAGE,'--format','{{.Id}}'],text=True).strip()
    actual=json.loads(subprocess.check_output(['docker','inspect',args.container],text=True))[0]
    mounts={m['Destination']:m['Source'] for m in actual['Mounts']}
    if (not actual['State']['Running'] or actual['Image']!=image_id
            or image_id!=implementation['local_image_id'] or mounts.get('/workspace')!=str(ROOT)):
        parser.error('container/image/source mount differs from implementation')
    audit_path=args.adder_audit.resolve()
    audit=json.loads(audit_path.read_text())
    if (not audit.get('passed') or len(audit['libraries'])!=3 or len(audit['sta_records'])!=30
            or len(audit['negative_controls'])!=3 or not all(r['rejected'] for r in audit['negative_controls'])):
        parser.error('incomplete adder model audit')
    for name,digest in audit['source_sha256'].items():
        if sha(ROOT/name)!=digest:parser.error('adder audit source changed: '+name)
    raw=audit_path.parent/'raw-arcs.json'
    if sha(raw)!=audit['raw_arcs_sha256']:parser.error('adder raw arc audit changed')
    validate_adder_arcs(json.loads(raw.read_text()))
    for row in audit['sta_records']:
        if sha(audit_path.parent/row['corner']/(row['path']+'.rpt'))!=row['sha256']:
            parser.error('adder STA path evidence changed')
    tool='/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad'
    wanted=dict(audit['libraries']);wanted[tool]=audit['openroad_binary_sha256']
    live=subprocess.check_output(['docker','exec',args.container,'sha256sum',*wanted],text=True)
    if {line.split(maxsplit=1)[1]:line.split(maxsplit=1)[0] for line in live.splitlines()}!=wanted:
        parser.error('live tool/library hashes differ from the adder audit')
    platform_manifest=ROOT/'docs/evidence/2026-10-18/post-lsu-baseline-preparation/environment/physical-tool-platform-sha256.txt'
    platform_command=['docker','exec',args.container,'sha256sum','--strict','--quiet','-c',
                      '/workspace/'+str(platform_manifest.relative_to(ROOT))]
    subprocess.check_call(platform_command)
    result_dir=attempt/'results/asap7/rv32_post_lsu_v1/base'
    odb=result_dir/'5_1_grt.odb'
    if not odb.is_file():parser.error('global-route database missing')
    destination=attempt/args.label
    if destination.exists():parser.error('analysis output already exists; choose a fresh label')
    destination.mkdir()
    script=ROOT/'physical/asap7/baseline/report.tcl'
    def guest(path):return '/workspace/'+str(path.relative_to(ROOT))
    report={'scope':'independent corner timing collection, pending closure review',
            'implementation_report_sha256':sha(attempt/'run.json'),
            'odb_sha256':sha(odb),'report_script_sha256':sha(script),
            'timing_common_sha256':sha(ROOT/'physical/asap7/baseline/timing_common.tcl'),
            'adder_audit_summary_sha256':sha(audit_path),
            'platform_manifest_sha256':sha(platform_manifest),
            'platform_files_verified':len(platform_manifest.read_text().splitlines()),
            'platform_validation_command':platform_command,
            'platform_validation_before_returncode':0,
            'clock_trials_ps':args.periods_ps,
            'local_image_id':image_id,'records':[],'passed':False}
    summary=destination/'run.json'
    summary.write_text(json.dumps(report,indent=2)+'\n')
    for corner in ('TT','SS','FF'):
        out=destination/corner;out.mkdir()
        command=['docker','exec','--user','1000:1000','-w','/workspace',
                 '-e','RV32_CORNER='+corner,'-e','RV32_ODB='+guest(odb),
                 '-e','RV32_ADDER_AUDIT_VERIFIED=1',
                 '-e','RV32_PERIODS_PS='+' '.join(map(str,args.periods_ps)),
                 '-e','RV32_REPORT_DIR='+guest(out),args.container,
                 '/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad',
                 '-no_init','-exit','-threads','2',guest(script)]
        with (out/'sta.log').open('w') as log:
            result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
        report['records'].append({'corner':corner,'command':command,'returncode':result.returncode,
                                  'log_sha256':sha(out/'sta.log'),
                                  'outputs_sha256':{str(p.relative_to(out)):sha(p)
                                                    for p in sorted(out.iterdir()) if p.is_file()}})
        summary.write_text(json.dumps(report,indent=2)+'\n')
        print(corner,'STA returncode',result.returncode,flush=True)
        if result.returncode:raise SystemExit(result.returncode)
    if (sha(script)!=report['report_script_sha256']
            or sha(ROOT/'physical/asap7/baseline/timing_common.tcl')!=report['timing_common_sha256']
            or sha(odb)!=report['odb_sha256']):
        parser.exit(1,'analysis inputs changed during collection\n')
    subprocess.check_call(platform_command)
    report['platform_validation_after_returncode']=0
    report['collection_completed']=True
    summary.write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
