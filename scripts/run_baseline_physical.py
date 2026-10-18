#!/usr/bin/env python3
"""Portable pinned ORFS global-route run; no slack-derived frequency claims."""
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
ORFS_SHA = '8359fde81991e6118b15b8a93fcde606b577794d'
IMAGE = 'rv32ooo-orfs:8359fde-flat'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--period-ps', type=int, default=5500, help='exploration constraint, not achieved timing')
    parser.add_argument('--jobs', type=int, default=2)
    parser.add_argument('--container', help='reuse a running pinned-image container with the documented mounts')
    parser.add_argument('--label', default='', help='unique attempt suffix; existing logs are never overwritten')
    parser.add_argument('--resume-reason', help='resume a failed attempt with identical hashed build inputs; retain the prior log')
    parser.add_argument('--adder-mapping',choices=('platform','abc'),default='platform',
                        help='tool-flow probe: platform full-adder extraction or ordinary ABC gate mapping')
    parser.add_argument('--detached',action='store_true',help='durable worker in an existing container; does not depend on a tool session')
    parser.add_argument('--synthesis-from',type=Path,help='reuse a completed, identity-checked synthesis stage from another attempt')
    parser.add_argument('--cts-from',type=Path,help='restart global routing from a completed, identity-checked TT CTS stage')
    parser.add_argument('--grt-from',type=Path,help='incrementally repair a completed, identity-checked TT global-route stage')
    parser.add_argument('--eco-slew-margin',type=int,default=30,help='TT ECO slew margin percent; independent corner limits stay unchanged')
    parser.add_argument('--eco-hold-margin-ps',type=int,default=50,help='TT ECO hold repair margin ps; independent corner uncertainty stays unchanged')
    args = parser.parse_args()
    if args.period_ps <= 2200 or args.jobs < 1:
        parser.error('period must exceed frozen 1100ps input + output budgets; jobs positive')
    if args.detached and not args.container:parser.error('--detached requires --container')
    if args.detached and args.resume_reason:parser.error('use a fresh label for detached attempts; synthesis stages can be reused')
    if args.cts_from and (args.synthesis_from or args.resume_reason):parser.error('--cts-from requires its own fresh attempt')
    if args.grt_from and (args.cts_from or args.synthesis_from or args.resume_reason):parser.error('--grt-from requires its own fresh attempt')
    if not 0<=args.eco_slew_margin<100 or args.eco_hold_margin_ps<0:parser.error('invalid ECO margins')
    if args.label and not re.fullmatch(r'[a-zA-Z0-9_-]+', args.label):
        parser.error('label may contain letters, digits, underscore and hyphen only')
    source = ROOT / 'build/baseline-setup/ORFS'
    commit = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    if commit != ORFS_SHA or subprocess.check_output(['git', '-C', str(source), 'status', '--porcelain']):
        parser.exit(1, 'ORFS checkout must be the pinned clean revision\n')
    suffix = f'-{args.label}' if args.label else ''
    directory = ROOT / f'build/baselines/ap5b-post-lsu-v1/physical-{args.period_ps}ps{suffix}'
    previous = None
    if args.resume_reason:
        if not (directory/'run.json').exists():parser.error('resume requires an existing failed attempt')
        previous = json.loads((directory/'run.json').read_text())
        if not previous.get('returncode'):parser.error('only a finished failed attempt may be resumed')
    elif (directory/'run.json').exists():
        parser.exit(1, 'attempt already exists; choose a fresh --label\n')
    directory.mkdir(parents=True, exist_ok=True)
    sdc = directory / 'constraint.sdc'
    # Absolute I/O/uncertainty/load remain unchanged across period trials.
    constraint = f'''create_clock -name core_clk -period {args.period_ps} [get_ports clk]
set_clock_uncertainty -setup 50 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_input_transition 20 [all_inputs]
set_input_delay -max 1100 -clock core_clk [all_inputs -no_clocks]
set_input_delay -min 0 -clock core_clk [all_inputs -no_clocks]
set_output_delay -max 1100 -clock core_clk [all_outputs]
set_output_delay -min 0 -clock core_clk [all_outputs]
set_load 2 [all_outputs]
group_path -name in2reg -from [all_inputs -no_clocks] -to [all_registers]
group_path -name reg2out -from [all_registers] -to [all_outputs]
group_path -name reg2reg -from [all_registers] -to [all_registers]
group_path -name in2out -from [all_inputs -no_clocks] -to [all_outputs]
'''
    if not sdc.exists() or sdc.read_text()!=constraint:
        if previous:parser.error('resume constraint differs from the failed attempt')
        sdc.write_text(constraint)
    def guest(path):
        return '/workspace/' + str(path.relative_to(ROOT))
    expected_image = subprocess.check_output(['docker','image','inspect',IMAGE,'--format','{{.Id}}'], text=True).strip()
    prefix = ['docker', 'run', '--rm', '--user', '1000:1000', '-v', f'{ROOT}:/workspace',
           '-v', f'{source}:/orfs-source:ro', '-w', '/workspace', '--entrypoint', '/bin/bash',
           IMAGE]
    if args.container:
        actual = json.loads(subprocess.check_output(['docker','inspect',args.container],text=True))[0]
        mounts = {m['Destination']: m['Source'] for m in actual['Mounts']}
        if (not actual['State']['Running'] or actual['Image'] != expected_image
                or mounts.get('/workspace') != str(ROOT) or mounts.get('/orfs-source') != str(source)):
            parser.exit(1, 'container image, state or source mounts do not match the pinned setup\n')
        prefix = ['docker','exec','--user','1000:1000','-w','/workspace',args.container,'/bin/bash']
    makefile='/workspace/physical/asap7/baseline/eco.mk' if args.grt_from else '/orfs-source/flow/Makefile'
    cmd = prefix + ['-c', f'exec make -f {makefile} "$@"', 'baseline-orfs',
           'FLOW_HOME=/orfs-source/flow', 'PLATFORM_DIR=/OpenROAD-flow-scripts/flow/platforms/asap7',
           'PLATFORMS_DIR=/OpenROAD-flow-scripts/flow/platforms',
           'OPENROAD_EXE=/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad',
           'YOSYS_EXE=/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys',
           'RV32_ROOT=/workspace', f'RV32_SDC={guest(sdc)}', f'WORK_HOME={guest(directory)}',
           'DESIGN_CONFIG=/workspace/physical/asap7/baseline/config.mk',
           f'NUM_CORES={args.jobs}',
           # This pinned OpenROAD predates ORFS's optional placement seed flag.
           # An empty Make override omits the unsupported flag in both GPL stages.
           'GPL_RANDOM_SEED=',
           # Construction follows the agreed TT-only policy. SS/FF are loaded
           # later in independent analysis processes, never into this graph.
           'CORNER=TC', 'CORNERS=typical',
           # The independent STA retains propagated-clock setup/hold paths.
           # Avoid the costly redundant all-design skew summaries in ORFS.
           'REPORT_CLOCK_SKEW=0',
           # This binary has no resizer "reroute" move used by the optional
           # ORFS WNS pass. Ordinary global-route setup/hold repair stays enabled.
           'OPT_POST_GRT_WNS=0']
    if args.adder_mapping=='abc':cmd.append('ADDER_MAP_FILE=')
    if args.grt_from:
        cmd.extend([f'SLEW_MARGIN={args.eco_slew_margin}',f'HOLD_SLACK_MARGIN={args.eco_hold_margin_ps}'])
    cmd.append('baseline-grt-eco' if args.grt_from else 'grt')
    report = {'scope': 'global-route research baseline exploration, not detailed-route signoff',
              'period_ps': args.period_ps, 'orfs_commit': commit, 'command': cmd,
              'sdc_sha256': sha(sdc), 'lowered_rtl_sha256': sha(ROOT/'build/baseline-setup/rtl_lowered.v'),
              'rtl_files_sha256': {str(p.relative_to(ROOT)): sha(p) for p in sorted((ROOT/'rtl').rglob('*.sv'))},
              'config_sha256': sha(ROOT/'physical/asap7/baseline/config.mk'), 'passed': False}
    report['local_image_id'] = expected_image
    report['placement_seed_policy'] = 'pinned-tool default; GPL_RANDOM_SEED= overrides config seed (unsupported flag)'
    report['construction_timing_corners'] = ['TT']
    report['clock_skew_summary_policy'] = 'ORFS summaries disabled; independent propagated-clock setup/hold checks and expanded paths required'
    report['post_grt_wns_policy'] = 'optional unsupported reroute-move pass disabled; ordinary setup/hold/electrical repair enabled'
    report['synthesis_adder_mapping'] = args.adder_mapping
    report['process_lowering_sha256'] = sha(ROOT/'physical/asap7/baseline/lower_processes.tcl')
    report['source_commit'] = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    report['source_status'] = subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).splitlines()
    cts_inputs=[]
    if args.grt_from:
        from check_physical_closure import check_constraints
        cache=args.grt_from.resolve()
        if not cache.is_relative_to(ROOT/'build'):parser.error('GRT source must be under build/')
        prior=json.loads((cache/'run.json').read_text())
        for field in ('orfs_commit','lowered_rtl_sha256','rtl_files_sha256','config_sha256',
                      'local_image_id','process_lowering_sha256','period_ps','synthesis_adder_mapping'):
            if prior[field]!=report[field]:parser.error('cached global-route input changed: '+field)
        if (prior.get('construction_timing_corners')!=['TT'] or not prior.get('input_identities_unchanged')
                or not prior.get('flow_completed') or prior.get('returncode')!=0):
            parser.error('ECO requires a completed unchanged TT global-route attempt')
        relative=Path('asap7/rv32_post_lsu_v1/base')
        odb=cache/'results'/relative/'5_1_grt.odb';input_sdc=odb.with_suffix('.sdc')
        check_constraints(input_sdc.read_text(),args.period_ps)
        target=directory/'results'/relative;target.mkdir(parents=True,exist_ok=True)
        for source_file in (odb,input_sdc):
            output=target/('5_0_grt_input'+source_file.suffix)
            if output.exists():parser.error('ECO destination already exists')
            shutil.copy2(source_file,output);cts_inputs.append(output)
        report['cached_grt']={'source':str(cache.relative_to(ROOT)),
                              'source_report_sha256':sha(cache/'run.json'),
                              'odb_sha256':sha(odb),'sdc_sha256':sha(input_sdc)}
        report['post_route_eco']={'construction_corner':'TT','slew_margin_percent':args.eco_slew_margin,
                                  'hold_margin_ps':args.eco_hold_margin_ps,
                                  'script_sha256':sha(ROOT/'physical/asap7/baseline/repair.tcl'),
                                  'makefile_sha256':sha(ROOT/'physical/asap7/baseline/eco.mk'),
                                  'independent_acceptance_constraints':'unchanged'}
        for key in ('cached_synthesis','cached_cts'):
            if key in prior:report[key]=prior[key]
    if args.cts_from:
        from check_physical_closure import check_constraints
        cache=args.cts_from.resolve()
        if not cache.is_relative_to(ROOT/'build'):parser.error('CTS source must be under build/')
        prior=json.loads((cache/'run.json').read_text())
        for field in ('orfs_commit','lowered_rtl_sha256','rtl_files_sha256','config_sha256',
                      'local_image_id','process_lowering_sha256','period_ps','synthesis_adder_mapping'):
            if prior[field]!=report[field]:parser.error('cached CTS input changed: '+field)
        if prior.get('construction_timing_corners')!=['TT'] or not prior.get('input_identities_unchanged') or prior.get('job_state')!='finished':
            parser.error('CTS cache requires a finished TT construction attempt with unchanged inputs')
        relative=Path('asap7/rv32_post_lsu_v1/base')
        odb=cache/'results'/relative/'4_cts.odb'
        cts_sdc=cache/'results'/relative/'4_cts.sdc'
        cts_log=cache/'logs'/relative/'4_1_cts.log'
        text=cts_log.read_text()
        if ('[ERROR ' in text or 'Error:' in text
                or not re.search(r'^4_1_cts\s+\.odb\s+\d+',text,re.M)
                or sha(odb)!=sha(odb.with_name('4_1_cts.odb'))):
            parser.error('cached CTS stage lacks a completed log/database pair')
        check_constraints(cts_sdc.read_text(),args.period_ps)
        target=directory/'results'/relative;target.mkdir(parents=True,exist_ok=True)
        for source_file in (odb,cts_sdc):
            output=target/source_file.name
            if output.exists():parser.error('cached CTS destination already exists')
            shutil.copy2(source_file,output);cts_inputs.append(output)
        report['cached_cts']={'source':str(cache.relative_to(ROOT)),
                              'source_report_sha256':sha(cache/'run.json'),
                              'odb_sha256':sha(odb),'sdc_sha256':sha(cts_sdc),
                              'completed_stage_log_sha256':sha(cts_log),
                              'reason':'reuse completed CTS only; source global-route failure remains a failure'}
        if 'cached_synthesis' in prior:report['cached_synthesis']=prior['cached_synthesis']
        cmd[-1]='do-5_1_grt'
    if args.synthesis_from:
        cache=args.synthesis_from.resolve()
        if not cache.is_relative_to(ROOT/'build'):parser.error('synthesis source must be under build/')
        prior=json.loads((cache/'run.json').read_text())
        for field in ('orfs_commit','lowered_rtl_sha256','rtl_files_sha256','config_sha256',
                      'local_image_id','process_lowering_sha256'):
            if prior[field]!=report[field]:parser.error('cached synthesis input changed: '+field)
        prior_mapping=prior.get('synthesis_adder_mapping','abc' if 'ADDER_MAP_FILE=' in prior['command'] else 'platform')
        if prior_mapping!=args.adder_mapping:parser.error('cached adder mapping differs from requested mapping')
        relative=Path('asap7/rv32_post_lsu_v1/base')
        netlist=cache/'results'/relative/'1_2_yosys.v'
        synth_log=cache/'logs'/relative/'1_2_yosys.log'
        if ('End of script.' not in synth_log.read_text() or 'ERROR:' in synth_log.read_text()
                or not netlist.read_text().rstrip().endswith('endmodule')):
            parser.error('cached synthesis did not finish successfully')
        cmd.insert(-1,'SYNTH_NETLIST_FILES='+guest(netlist))
        report['cached_synthesis']={'source':str(cache.relative_to(ROOT)),'mapping_period_ps':prior['period_ps'],
                                   'source_report_sha256':sha(cache/'run.json'),
                                   'netlist':str(netlist.relative_to(ROOT)),'netlist_sha256':sha(netlist),
                                   'log':str(synth_log.relative_to(ROOT)),'log_sha256':sha(synth_log)}
    worker_command=['make','-f',makefile,*cmd[cmd.index('baseline-orfs')+1:]]
    if args.detached:
        inputs={guest(ROOT/name):value for name,value in report['rtl_files_sha256'].items()}
        for path in (sdc,ROOT/'physical/asap7/baseline/config.mk',ROOT/'physical/asap7/baseline/lower_processes.tcl',
                     ROOT/'build/baseline-setup/rtl_lowered.v',ROOT/'scripts/run_physical_job.py'):
            inputs[guest(path)]=sha(path)
        if args.synthesis_from:inputs[guest(netlist)]=sha(netlist)
        for path in cts_inputs:inputs[guest(path)]=sha(path)
        if args.grt_from:
            for path in (ROOT/'physical/asap7/baseline/eco.mk',ROOT/'physical/asap7/baseline/repair.tcl'):
                inputs[guest(path)]=sha(path)
        spec=directory/'job.json'
        spec.write_text(json.dumps({'report':guest(directory/'run.json'),'log':guest(directory/'make.log'),
                                    'command':worker_command,'cwd':'/workspace','inputs':inputs},indent=2)+'\n')
        cmd=['docker','exec','-d','--user','1000:1000','-w','/workspace',args.container,
             'python3','/workspace/scripts/run_physical_job.py',guest(spec)]
        report.update(command=cmd,worker_command=worker_command,job_spec_sha256=sha(spec),job_state='queued')
    if previous:
        for field in ('period_ps','orfs_commit','command','sdc_sha256','lowered_rtl_sha256',
                      'rtl_files_sha256','config_sha256','local_image_id','process_lowering_sha256'):
            if previous[field]!=report[field]:parser.error('resume input changed: '+field)
        history=previous.pop('previous_attempts',[])
        prior_log=directory/f'make-attempt{len(history)+1}.log'
        if prior_log.exists():parser.error('prior log already exists; refusing overwrite')
        (directory/'make.log').rename(prior_log)
        previous.update(log=str(prior_log.relative_to(ROOT)),resume_reason=args.resume_reason)
        history.append(previous);report['previous_attempts']=history
    summary = directory/'run.json';summary.write_text(json.dumps(report,indent=2)+'\n')
    if args.detached:
        result=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        if result.returncode:
            report.update(job_state='launch_failed',launch_returncode=result.returncode,launch_output=result.stdout)
            summary.write_text(json.dumps(report,indent=2)+'\n')
            raise SystemExit(result.returncode)
        print('detached job submitted; result:',summary,flush=True)
        return
    with (directory/'make.log').open('w') as log:
        result = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT)
    report.update(returncode=result.returncode, log_sha256=sha(directory/'make.log'))
    # Closure requires separate corner/path/area/constraint checks, never just rc=0.
    report['flow_completed'] = result.returncode == 0
    summary.write_text(json.dumps(report,indent=2)+'\n')
    print('global-route command returncode',result.returncode,flush=True)
    raise SystemExit(result.returncode)

if __name__ == '__main__':
    main()
