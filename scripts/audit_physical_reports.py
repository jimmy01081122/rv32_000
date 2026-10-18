#!/usr/bin/env python3
"""Exercise saved-route reporting and real STA failure controls on four cells."""
import argparse
import json
import math
from pathlib import Path
import re
import subprocess
from baseline_contract import ROOT, sha
from run_baseline_physical import IMAGE


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--container',required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    out=args.out.resolve()
    if not out.is_relative_to(ROOT/'build') or out.exists():
        parser.error('use a new output directory under build/')
    info=json.loads(subprocess.check_output(['docker','inspect',args.container],text=True))[0]
    image=subprocess.check_output(['docker','image','inspect',IMAGE,'--format','{{.Id}}'],text=True).strip()
    if (not info['State']['Running'] or info['Image']!=image
            or {m['Destination']:m['Source'] for m in info['Mounts']}.get('/workspace')!=str(ROOT)):
        parser.error('pinned running container/source mount required')
    out.mkdir(parents=True)
    tool='/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad'
    def guest(path):return '/workspace/'+str(path.relative_to(ROOT))
    report={'scope':'four-cell report qualification, not CPU closure','local_image_id':image,
            'source_sha256':{p:sha(ROOT/p) for p in [
                'physical/asap7/baseline/timing_common.tcl','physical/asap7/baseline/report.tcl',
                'physical/asap7/baseline/report_audit.tcl','physical/asap7/baseline/report_audit.v',
                'scripts/audit_physical_reports.py']},'commands':[],'controls':[],'passed':False}
    def save():
        (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    def run(name,script,env):
        cmd=['docker','exec','--user','1000:1000','-w','/workspace']
        for key,value in env.items():cmd+=['-e',key+'='+value]
        cmd += [args.container,tool,'-no_init','-exit','-threads','2',guest(script)]
        with (out/(name+'.log')).open('w') as log:
            result=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
        report['commands'].append({'name':name,'command':cmd,'returncode':result.returncode})
        save()
        return result.returncode
    def control(name,condition):
        report['controls'].append({'name':name,'passed':bool(condition)})
        save()
        if not condition:raise RuntimeError('report control failed: '+name)
    rc=run('build',ROOT/'physical/asap7/baseline/report_audit.tcl',
           {'RV32_CORNER':'TT','RV32_AUDIT_DIR':guest(out)})
    control('fixture global route completed',rc==0)
    for corner in ('TT','SS','FF'):
        dest=out/corner;dest.mkdir()
        env={'RV32_CORNER':corner,'RV32_ODB':guest(out/'routed.odb'),
             'RV32_REPORT_DIR':guest(dest),'RV32_PERIODS_PS':'2300 5500',
             'RV32_ADDER_AUDIT_VERIFIED':'1'}
        rc=run(corner,ROOT/'physical/asap7/baseline/report.tcl',env)
        control(corner+' saved-route reports completed',rc==0)
        data=json.loads((dest/'clock_trials.json').read_text())
        control(corner+' area, storage and restored routes',data['global_routes_restored']
                and data['standard_cell_count']==4 and data['register_count']==2
                and data['macro_count']==0 and math.isclose(data['standard_cell_area_um2'],0.91854,abs_tol=1e-8))
        control(corner+' explicit ps units',bool(re.search(r'^\s*time 1ps$',(dest/'units.rpt').read_text(),re.M)))
        for trial in data['trials']:
            period=trial['period_ps']
            for kind,mode in [('setup','max'),('hold','min')]:
                value=float(re.fullmatch(r'worst slack '+mode+r' ([-+\d.eE]+)\s*',
                            (dest/f'{kind}_{period}.rpt').read_text()).group(1))
                control(f'{corner} {period} {kind} numerical/report agreement',
                        math.isfinite(trial[kind+'_slack_ps']) and abs(value-trial[kind+'_slack_ps'])<0.011)
            for kind in ('setup','hold'):
                groups=set(re.findall(r'Path Group: (\S+)',(dest/f'{kind}_paths_{period}.rpt').read_text()))
                control(f'{corner} {period} {kind} four path groups',groups=={'in2reg','reg2reg','reg2out','in2out'})
            control(f'{corner} {period} complete constraints',not (dest/f'check_setup_{period}.rpt').read_text().strip())
        if corner=='TT':
            control('real setup violation detected',data['trials'][0]['setup_slack_ps']<0)
        control(corner+' real hold violation detected',data['trials'][1]['hold_slack_ps']<0)
    # Change actual STA state after the normal report; no synthetic report strings.
    negative=out/'negative.tcl'
    negative.write_text('''source physical/asap7/baseline/report.tcl
unset_input_delay -clock core_clk [get_ports A]
save_report $directory/missing-input-delay.rpt {check_setup -verbose}
set_load 10000 [all_outputs]
save_report $directory/excess-load.rpt {report_check_types -max_slew -max_capacitance -violators}
''')
    dest=out/'negative';dest.mkdir()
    env={'RV32_CORNER':'TT','RV32_ODB':guest(out/'routed.odb'),
         'RV32_REPORT_DIR':guest(dest),'RV32_PERIODS_PS':'5500','RV32_ADDER_AUDIT_VERIFIED':'1'}
    rc=run('negative',negative,env)
    control('real constraint/electrical control completed',rc==0)
    control('missing input constraint detected','A' in (dest/'missing-input-delay.rpt').read_text()
            and bool((dest/'missing-input-delay.rpt').read_text().strip()))
    control('real output overload detected','VIOLATED' in (dest/'excess-load.rpt').read_text())
    for name,odb,flag,message in [
            ('unrouted','unrouted.odb','1','database has no restorable global routes'),
            ('unaudited','routed.odb','0','adder output-port warning interpretation needs')]:
        dest=out/name;dest.mkdir()
        env.update(RV32_ODB=guest(out/odb),RV32_REPORT_DIR=guest(dest),RV32_ADDER_AUDIT_VERIFIED=flag)
        rc=run(name,ROOT/'physical/asap7/baseline/report.tcl',env)
        control(name+' rejected',rc!=0 and message in (out/(name+'.log')).read_text())
    report['output_sha256']={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*'))
                             if p.is_file() and p.name!='summary.json'}
    report['passed']=all(c['passed'] for c in report['controls'])
    save()
    print('physical report controls:',len(report['controls']),'PASS',flush=True)


if __name__=='__main__':main()
