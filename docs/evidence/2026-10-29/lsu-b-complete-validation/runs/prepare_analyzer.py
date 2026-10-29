from pathlib import Path
src=Path('scripts/analyze_baseline_physical.py').read_text()
src=src.replace('from baseline_contract import ROOT,sha,load,check_rtl', '''import sys
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p/'scripts/baseline_contract.py').exists())/'scripts'))
from baseline_contract import ROOT,sha,load,check_rtl
DOCKER=['env','-u','DOCKER_HOST','-u','DOCKER_CONTEXT','-u','DOCKER_TLS','-u','DOCKER_TLS_VERIFY','-u','DOCKER_CERT_PATH','docker','--host=unix:///var/run/docker.sock']''')
src=src.replace("parser.add_argument('--experiment',type=Path,help='explicit candidate contract; absent means immutable baseline RTL')", "parser.add_argument('--contract',type=Path,default=ROOT/'experiments/lsu-b-validation-v2/contract.json')")
a=src.index('    manifest=load()');b=src.index("    if 'post_route_eco' in implementation:",a)
src=src[:a]+'''    contract=json.loads(args.contract.read_text())
    variant=implementation['variant']
    if variant not in contract['variants'] or implementation['contract_sha256']!=sha(args.contract):
        parser.error('v2 implementation contract differs')
    expected=contract['variants'][variant]
    if implementation['rtl_files_sha256']!=expected['rtl_files_sha256']:
        parser.error('v2 RTL identity differs')
    if any(p%contract['physical']['period_grid_ps'] for p in args.periods_ps):
        parser.error('frozen 100 ps trial grid required')
    if (sha(ROOT/expected['netlist'])!=expected['netlist_sha256'] or
            implementation['linked_netlist_sha256']!=expected['netlist_sha256'] or
            sha(ROOT/contract['shared_link_manifest']['path'])!=contract['shared_link_manifest']['sha256']):
        parser.error('shared FPU link proof changed')
    if implementation['source_status'] or implementation['source_commit']!=json.loads((attempt.parent/'grt/run.json').read_text())['source_commit']:
        parser.error('clean same-source physical stages required')
    for path,key in [('physical/asap7/baseline/config.mk','config_sha256')]:
        if sha(ROOT/path)!=implementation[key]:parser.error('implementation input changed: '+path)
    eco=contract['physical']['post_route_eco']
    required={'NUM_CORES=2','CORNER=TC','CORNERS=typical','GPL_RANDOM_SEED=',
              'REPORT_CLOCK_SKEW=0','OPT_POST_GRT_WNS=0','ADDER_MAP_FILE=',
              'SLEW_MARGIN='+str(eco['slew_margin_percent']),
              'HOLD_SLACK_MARGIN='+str(eco['hold_margin_ps'])}
    if (not required.issubset(implementation['command']) or implementation['period_ps']!=14000 or
            any(implementation['post_route_eco'].get(k)!=v for k,v in eco.items())):
        parser.error('v2 physical construction policy differs')
    incoming=attempt.parent/'grt'
    if (sha(incoming/'run.json')!=implementation['incoming_route']['report_sha256'] or
            sha(incoming/'make.log')!=json.loads((incoming/'run.json').read_text())['log_sha256']):
        parser.error('incoming native stage proof changed')
''' +src[b:]
src=src.replace("['docker','image','inspect',IMAGE", "DOCKER+['image','inspect',IMAGE")
src=src.replace("['docker','inspect',args.container]", "DOCKER+['inspect',args.container]")
src=src.replace("['docker','exec',args.container", "DOCKER+['exec',args.container")
src=src.replace("['docker','exec','--user'", "DOCKER+['exec','--user'")
src=src.replace("    if args.experiment:\n        report.update(experiment_id=experiment['experiment_id'],experiment_manifest_sha256=sha(args.experiment))", "    report.update(experiment_id=contract['experiment_id'],contract_sha256=sha(args.contract),variant=variant,collector_sha256=sha(Path(__file__)))")
src=src.replace("    summary.write_text(json.dumps(report,indent=2)+'\\n')\n\n\nif __name__", "    summary.write_text(json.dumps(report,indent=2)+'\\n')\n    from check_physical_closure import review_collection\n    review=review_collection(destination)\n    (destination/'closure-review.json').write_text(json.dumps(review,indent=2)+'\\n')\n    print(json.dumps({k:v for k,v in review.items() if k!='records'},indent=2),flush=True)\n\n\nif __name__")
assert 'args.experiment' not in src
Path('build/experiments/lsu-b-validation-v2/analyze_physical_v2.py').write_text(src)
