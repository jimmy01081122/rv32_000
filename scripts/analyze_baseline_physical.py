#!/usr/bin/env python3
"""Collect independent TT/SS/FF timing trials; collection alone is not closure."""
import argparse
import json
from pathlib import Path
import re
import subprocess
from baseline_contract import ROOT,sha,load,check_rtl
from run_baseline_physical import IMAGE


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--attempt',type=Path,required=True)
    parser.add_argument('--container',required=True)
    parser.add_argument('--label',default='independent-sta')
    args=parser.parse_args()
    if not re.fullmatch(r'[a-zA-Z0-9_-]+',args.label):parser.error('invalid output label')
    attempt=args.attempt.resolve()
    if not attempt.is_relative_to(ROOT/'build'):parser.error('attempt must be under repository build/')
    implementation=json.loads((attempt/'run.json').read_text())
    if not implementation.get('flow_completed'):parser.error('implementation command has not completed successfully')
    check_rtl(load())
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
            'local_image_id':image_id,'records':[],'passed':False}
    summary=destination/'run.json'
    summary.write_text(json.dumps(report,indent=2)+'\n')
    for corner in ('TT','SS','FF'):
        out=destination/corner;out.mkdir()
        command=['docker','exec','--user','1000:1000','-w','/workspace',
                 '-e','RV32_CORNER='+corner,'-e','RV32_ODB='+guest(odb),
                 '-e','RV32_REPORT_DIR='+guest(out),args.container,
                 '/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad',
                 '-no_init','-exit','-threads','2',guest(script)]
        with (out/'sta.log').open('w') as log:
            result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
        report['records'].append({'corner':corner,'command':command,'returncode':result.returncode,
                                  'log_sha256':sha(out/'sta.log')})
        summary.write_text(json.dumps(report,indent=2)+'\n')
        print(corner,'STA returncode',result.returncode,flush=True)
        if result.returncode:raise SystemExit(result.returncode)
    report['collection_completed']=True
    summary.write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
