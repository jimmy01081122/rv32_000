#!/usr/bin/env python3
"""Review independent-corner trials; never infer a clock from a slack offset."""
import argparse
import json
import math
from pathlib import Path
import re
from baseline_contract import ROOT, sha


def check_constraints(text,period):
    number=r'([-+\d.eE]+)'
    clocks=re.findall(r'^create_clock -name core_clk -period '+number+r' \[get_ports \{clk\}\]$',text,re.M)
    if len(clocks)!=1 or float(clocks[0])!=period or len(re.findall(r'^create_clock ',text,re.M))!=1:
        raise ValueError('serialized clock differs from tested period')
    for mode,value in [('setup',50),('hold',25)]:
        matches=re.findall(r'^set_clock_uncertainty -'+mode+' '+number+r' core_clk$',text,re.M)
        if len(matches)!=1 or float(matches[0])!=value:raise ValueError('clock uncertainty changed')
    if re.search(r'^set_(?:false_path|multicycle_path|disable_timing|max_delay|min_delay)\b',text,re.M):
        raise ValueError('unreviewed timing exception')
    if 'set_propagated_clock [get_clocks {core_clk}]' not in text:
        raise ValueError('propagated clock missing')
    transitions=re.findall(r'^set_input_transition '+number+r' \[get_ports \{([^}]+)\}\]$',text,re.M)
    loads=re.findall(r'^set_load -pin_load '+number+r' \[get_ports \{([^}]+)\}\]$',text,re.M)
    if not transitions or not loads or any(float(value)!=20 for value,_ in transitions) or any(float(value)!=2 for value,_ in loads):
        raise ValueError('input slew/output load changed')
    for direction,ports in [('input',{port for _,port in transitions}-{'clk'}),
                            ('output',{port for _,port in loads})]:
        for mode,expected in [('min',0),('max',1100)]:
            matches=re.findall(r'^set_'+direction+'_delay '+number+r' -clock \[get_clocks \{core_clk\}\] -'+mode+r' -add_delay \[get_ports \{([^}]+)\}\]$',text,re.M)
            if len(matches)!=len(ports) or {port for _,port in matches}!=ports or any(float(value)!=expected for value,_ in matches):
                raise ValueError('serialized '+direction+' '+mode+' delay coverage/value changed')


def worst_slack(path,mode):
    match=re.fullmatch(r'worst slack '+mode+r' ([-+\d.eE]+)\s*',path.read_text())
    if not match:raise ValueError('missing/invalid worst-slack report: '+str(path))
    result=float(match[1])
    if not math.isfinite(result):raise ValueError('non-finite reported slack')
    return result


def review_corner(directory,corner,periods):
    data=json.loads((directory/'clock_trials.json').read_text())
    if data['corner']!=corner or not data['global_routes_restored']:
        raise ValueError('corner identity or restored-route proof missing')
    area=data['standard_cell_area_um2']
    if (not math.isfinite(area) or area<=0 or data['standard_cell_count']<=0
            or data['register_count']<=0 or data['macro_count']!=0):
        raise ValueError('invalid core area/storage boundary')
    if not re.search(r'^\s*time 1ps$',(directory/'units.rpt').read_text(),re.M):
        raise ValueError('timing unit is not explicitly ps')
    if [r['period_ps'] for r in data['trials']]!=periods:
        raise ValueError('trial set differs from requested clock periods')
    trials=[]
    for row in data['trials']:
        period=row['period_ps'];problems=[]
        for kind,mode in [('setup','max'),('hold','min')]:
            value=row[kind+'_slack_ps']
            if not math.isfinite(value):raise ValueError('non-finite numerical slack')
            if abs(value-worst_slack(directory/f'{kind}_{period}.rpt',mode))>=0.011:
                raise ValueError('numerical/text slack disagreement')
            paths=(directory/f'{kind}_paths_{period}.rpt').read_text()
            groups=set(re.findall(r'Path Group: (\S+)',paths))
            # The current whole-core contract has valid paths in all four groups.
            # A changed/empty group needs review, not implicit acceptance.
            if groups!={'in2reg','reg2reg','reg2out','in2out'} or 'Path Type: '+mode not in paths:
                raise ValueError('missing/changed core path-group coverage')
            if value<0 or 'slack (VIOLATED)' in paths:problems.append(kind+' violation')
        if (directory/f'check_setup_{period}.rpt').read_text().strip():
            problems.append('constraint coverage needs review')
        if (directory/f'electrical_{period}.rpt').read_text().strip():
            problems.append('electrical/library timing checks need review')
        constraints=(directory/f'constraints_{period}.sdc').read_text()
        check_constraints(constraints,period)
        trials.append({'period_ps':period,'setup_slack_ps':row['setup_slack_ps'],
                       'hold_slack_ps':row['hold_slack_ps'],'problems':problems,'passed':not problems})
    return {'corner':corner,'standard_cell_area_um2':area,
            'standard_cell_count':data['standard_cell_count'],'register_count':data['register_count'],
            'library_warning_cell_instances':data['library_warning_cell_instances'],'trials':trials}


def review_collection(directory):
    source=directory/'run.json';collection=json.loads(source.read_text())
    if not collection.get('collection_completed'):
        raise ValueError('independent corner collection incomplete')
    platform_manifest=ROOT/'docs/evidence/2026-10-18/post-lsu-baseline-preparation/environment/physical-tool-platform-sha256.txt'
    if (collection.get('platform_manifest_sha256')!=sha(platform_manifest)
            or collection.get('platform_validation_before_returncode')!=0
            or collection.get('platform_validation_after_returncode')!=0):
        raise ValueError('tool/complete platform identity proof required before and after analysis')
    periods=collection['clock_trials_ps']
    if not periods or periods!=sorted(set(periods)) or min(periods)<=2200:
        raise ValueError('invalid tested clock set')
    if [r['corner'] for r in collection['records']]!=['TT','SS','FF']:
        raise ValueError('all three independent corner records required')
    implementation_path=directory.parent/'run.json'
    if sha(implementation_path)!=collection['implementation_report_sha256']:
        raise ValueError('implementation record changed')
    implementation=json.loads(implementation_path.read_text())
    if (not implementation.get('flow_completed') or implementation.get('returncode')!=0
            or not implementation.get('input_identities_unchanged')
            or implementation.get('construction_timing_corners')!=['TT']):
        raise ValueError('durable implementation/input identity proof required')
    if sha(directory.parent/'make.log')!=implementation['log_sha256']:
        raise ValueError('implementation log changed')
    odb=directory.parent/'results/asap7/rv32_post_lsu_v1/base/5_1_grt.odb'
    if sha(odb)!=collection['odb_sha256']:raise ValueError('global-route database changed')
    for name,key in [('physical/asap7/baseline/report.tcl','report_script_sha256'),
                     ('physical/asap7/baseline/timing_common.tcl','timing_common_sha256')]:
        if sha(ROOT/name)!=collection[key]:raise ValueError('analysis source changed: '+name)
    records=[]
    for row in collection['records']:
        if row['returncode']!=0:raise ValueError('failed corner command')
        corner_dir=directory/row['corner']
        inventory=row.get('outputs_sha256',{})
        if not inventory or set(inventory)!={p.name for p in corner_dir.iterdir() if p.is_file()}:
            raise ValueError('incomplete corner artifact inventory')
        for name,digest in inventory.items():
            if Path(name).name!=name or sha(corner_dir/name)!=digest:
                raise ValueError('corner artifact changed: '+name)
        records.append(review_corner(corner_dir,row['corner'],periods))
    if len({(r['standard_cell_area_um2'],r['standard_cell_count'],r['register_count']) for r in records})!=1:
        raise ValueError('corner geometry/storage disagreement')
    qualified=[period for index,period in enumerate(periods)
               if all(row['trials'][index]['passed'] for row in records)]
    return {'scope':'tested global-route timing trials only; routing review and formal measurement still required',
            'analysis_report_sha256':sha(source),'implementation_report_sha256':sha(implementation_path),
            'checker_sha256':sha(Path(__file__)),
            'records':records,'qualified_periods_ps':qualified,
            'smallest_tested_passing_period_ps':min(qualified) if qualified else None,
            'standard_cell_area_um2':records[0]['standard_cell_area_um2'],
            'passed':bool(qualified)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--analysis',type=Path,required=True)
    args=parser.parse_args()
    directory=args.analysis.resolve()
    if not directory.is_relative_to(ROOT/'build'):parser.error('analysis must be under build/')
    output=directory/'closure-review.json'
    if output.exists():parser.error('closure review already exists; retain it and collect a new label')
    try:result=review_collection(directory)
    except (ValueError,KeyError,OSError,TypeError) as error:
        result={'passed':False,'error':str(error)}
    output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='records'},indent=2),flush=True)
    raise SystemExit(0 if result['passed'] else 1)


if __name__=='__main__':main()
