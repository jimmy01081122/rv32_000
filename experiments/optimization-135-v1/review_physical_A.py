#!/usr/bin/env python3
"""Admit fresh isolated A through the unchanged native guard reviewer."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = next(p for p in Path(__file__).resolve().parents if (p/'scripts/baseline_contract.py').exists())
HERE = ROOT/'experiments/optimization-135-v1'
BASE = ROOT/'build/experiments/optimization-135-v1'
OUT = BASE/'attempt-v2'
OLD = ROOT/'build/experiments/lsu-b-validation-v2'
ARCHIVE = ROOT/'docs/evidence/2026-10-29/lsu-b-complete-validation'
sys.path.insert(0, str(ROOT/'experiments/lsu-b-validation-v2'))
import review_guard as accepted
from review import review_formal, logical_sha, guest_path, sha, require


def read(path):
    return json.loads(path.read_text())


def archive_index():
    inventory = ARCHIVE/'copy-inventory.json'
    require(sha(inventory) == '4a67509515d6c320b633c9f0d2e063c9e85b5697d8ac739637759253ef5e1920',
            'original B archive inventory changed')
    index = {}
    for row in read(inventory)['records']:
        path = ARCHIVE/row['destination']
        require(sha(path) == row['stored_sha256'] and path.stat().st_size == row['stored_bytes'],
                'archived bytes changed: '+str(path))
        index[row['source']] = row
    require(len(read(inventory)['records']) == 1327, 'incomplete reference archive')
    return index


def archived_current(path, index):
    row = index[str(path.relative_to(ROOT))]
    require(logical_sha(path) == row['source_sha256'], 'current accepted evidence differs: '+str(path))
    return row['source_sha256']


def command_shape(command):
    variable = {'WORK_HOME', 'RV32_SDC', 'VERILOG_FILES', 'SYNTH_NETLIST_FILES'}
    return [arg.split('=', 1)[0]+'=<variant-path>' if arg.partition('=')[0] in variable else arg
            for arg in command]


def source_link(contract, index, formal):
    path = OLD/'formal-to-physical-link-review.json'
    digest = archived_current(path, index)
    link = read(path)
    require(link['passed'] and link['proof_summary_sha256'] == formal['proof_summary_sha256']
            and link['shared_graph_sha256'] == contract['shared_fpu_graph_sha256']
            and link['link_manifest_sha256'] == contract['shared_link_manifest']['sha256'],
            'formal/mapped graph binding differs')
    manifest_path = ROOT/contract['shared_link_manifest']['path']
    require(sha(manifest_path) == contract['shared_link_manifest']['sha256'], 'link manifest changed')
    manifest = read(manifest_path)
    row = manifest['variants']['A']
    policy = contract['variants']['A']
    require(row['linked_sha256'] == policy['netlist_sha256']
            == link['linked_cores']['A']['linked_netlist_sha256']
            and sha(ROOT/policy['netlist']) == policy['netlist_sha256'], 'A mapped netlist changed')
    # Recheck the actual module bodies, including A's untouched core and shared FPU.
    sys.path.insert(0, str(ROOT/'experiments/fpu-mapping-v1'))
    from link_shared import modules
    from compare_mapped import MODULE, canonical_graph
    parsed = modules(ROOT/policy['netlist'])
    require(hashlib.sha256(parsed['rv32_ooo_core']).hexdigest() == row['core_body_sha256']
            == link['linked_cores']['A']['core_body_sha256'], 'A core body changed at FPU link')
    require(hashlib.sha256(parsed[MODULE]).hexdigest() == manifest['shared_fpu_body_sha256']
            == link['linked_cores']['A']['shared_FPU_body_sha256'], 'A FPU module body changed')
    mapped = ROOT/'build/experiments/fpu-mapping-v1/shared-unit-v1/results/asap7/rv32_post_lsu_v1/base/fp_mapped.rtlil.json'
    raw = mapped.read_bytes() if mapped.is_file() else gzip.decompress(Path(str(mapped)+'.gz').read_bytes())
    require(hashlib.sha256(raw).hexdigest() == link['actual_mapped_json_sha256'], 'formal mapped model changed')
    _, graph = canonical_graph(json.loads(raw)['modules'][MODULE])
    require(graph == contract['shared_fpu_graph_sha256'], 'actual common FPU graph changed')
    lowering = ROOT/'build/experiments/lsu-a-v1/rtl_lowered.lowering.json'
    lowered = read(lowering)
    require(lowered['passed'] and lowered['returncode'] == 0 and lowered['input_identities_unchanged']
            and lowered['experiment_manifest_sha256'] == contract['a_manifest_sha256']
            and lowered['rtl_files_sha256'] == policy['rtl_files_sha256']
            and lowered['lowered_rtl_sha256'] == link['source_origins']['A']['lowered_source_sha256']
            == logical_sha(lowering.with_name('rtl_lowered.v')), 'A source/lowering lineage differs')
    native = ROOT/'build/experiments/fpu-mapping-v1/keep-v2/A'
    require(sha(native/'run.json') == row['native_report_sha256'], 'A native mapping record changed')
    run, job = read(native/'run.json'), read(native/'job.json')
    require(run['flow_completed'] and run['returncode'] == 0 and run['input_identities_unchanged']
            and sha(native/'make.log') == run['log_sha256'] and run['command'] == job['command'],
            'A native mapping incomplete')
    for name, expected in job['inputs'].items():
        require(logical_sha(guest_path(name)) == expected, 'A mapping input changed: '+name)
    require(logical_sha(ROOT/row['netlist']) == row['netlist_sha256'], 'A original mapped netlist changed')
    original_path = ROOT/row['netlist']
    class RetainedSource:
        def read_bytes(self):
            if original_path.is_file():
                return original_path.read_bytes()
            return gzip.decompress(Path(str(original_path)+'.gz').read_bytes())
    original_core = modules(RetainedSource())['rv32_ooo_core']
    require(original_core == parsed['rv32_ooo_core'], 'FPU relink altered A core')
    return dict(passed=True, retained_link_review_sha256=digest,
                common_graph_sha256=graph, A_linked_netlist_sha256=policy['netlist_sha256'],
                A_lowering_report_sha256=sha(lowering), A_mapping_report_sha256=sha(native/'run.json'))


def review(analysis):
    contract_path = OUT/'A-guard-bound-contract.json'
    contract = read(contract_path)
    old_policy = read(ROOT/'experiments/lsu-b-validation-v2/contract-ready-guard.json')
    require(contract['physical'] == old_policy['physical'], 'same-flow policy differs')
    require(contract['a_manifest_sha256'] == sha(ROOT/'experiments/lsu-a-v1/manifest.json')
            and contract['baseline_manifest_sha256'] == sha(ROOT/'baselines/ap5b-post-lsu-v1/manifest.json'),
            'frozen identity changed')
    for name, digest in {**contract['unchanged_rtl'], **contract['native_flow_sources_sha256'], **contract['study_sources_sha256']}.items():
        require(sha(ROOT/name) == digest, 'pinned construction source changed: '+name)
    controller = read(OUT/'physical-controller.json')
    require(controller['complete'] and controller['stages'] == ['grt', 'eco', 'guard']
            and controller['input_identities_unchanged'] and len(controller['checkpoints']) == 3
            and controller['bound_guard_contract_sha256'] == sha(contract_path), 'native chain incomplete')
    require(read(OUT/'native-exit.json')['returncode'] == 0, 'native controller failed')
    publication = read(OUT/'native-publication.json')
    require(publication['passed'] and publication['all_host_bytes_and_links_verified']
            and publication['private_tmpfs_unmounted'], 'durable native publication incomplete')
    sys.path.insert(0, str(HERE))
    from checkpoint import verify_archive
    for item in controller['checkpoints']:
        receipt = read(OUT/item['receipt'])
        require(receipt['passed'] and receipt['sha256'] == item['sha256']
                == sha(OUT/item['archive']), 'durable checkpoint changed')
        verify_archive(OUT/item['archive'], receipt['records'])
    index = archive_index()
    old_path = OLD/'final-common-clock-review.json'
    require(archived_current(old_path, index) == 'c133e45ff7ad30f1ad049a13a45f4c66b3c8a6d37e6cad85daa8aee397de0ea0',
            'accepted final reference review changed')
    previous = read(old_path)
    require(previous['passed'], 'unqualified historical reference')
    require(sha(ROOT/'experiments/lsu-b-validation-v2/review_guard.py') == previous['reviewer_sha256'],
            'accepted reviewer changed')
    for directory, collector in [
        (OUT/'physical-A-v2/eco/independent-sta-v1', OLD/'analyze_physical_v2.py'),
        (analysis, ROOT/'experiments/lsu-b-validation-v2/analyze_guard.py')]:
        require(archived_current(collector, index) == read(directory/'run.json')['collector_sha256'],
                'independent collector differs from the accepted source')
    formal = review_formal()
    link = source_link(contract, index, formal)
    comparisons = []
    for stage, directory in [('grt', 'physical-A-v1/grt'), ('eco', 'physical-A-v2/eco'), ('guard', 'physical-A-v4/guard')]:
        current = read(OUT/directory/'run.json')
        require(current['source_commit'] == controller['source_commit'], 'A native commits differ')
        for variant in ['baseline', 'B']:
            number = {'grt':1, 'eco':2, 'guard':4}[stage]
            path = OLD/f'physical-{variant}-v{number}'/stage/'run.json'
            archived_current(path, index)
            other = read(path)
            require(command_shape(current['command']) == command_shape(other['command']),
                    'native execution differs beyond explicit variant paths')
            for field in ['local_image_id', 'orfs_commit', 'period_ps', 'construction_timing_corners', 'config_sha256']:
                require(current[field] == other[field], 'native reference differs: '+field)
            comparisons.append(dict(stage=stage, reference=variant, native_arguments_equal_except_variant_paths=True,
                                    A_commit=current['source_commit'], reference_commit=other['source_commit']))
    accepted.CONTRACT = contract_path
    accepted.PARENT_CONTRACT = HERE/'contract-hold40.json'
    candidate = accepted.review_guard(analysis, 'A', contract)
    reference = previous['baseline_physical']
    require(10000 in reference['qualified_periods_ps'] and 10000 in candidate['qualified_periods_ps'],
            'common clock lacks physical qualification')
    baseline = read(ROOT/'baselines/ap5b-post-lsu-v1/manifest.json')
    area = candidate['standard_cell_area_um2']
    return dict(passed=True, scope='isolated A at shared-FPU/hold40/ready-guard global-route research boundary; no baseline promotion',
                reviewer_sha256=sha(Path(__file__)), accepted_guard_reviewer_sha256=sha(Path(accepted.__file__)),
                contract_sha256=sha(contract_path), formal=formal, formal_to_physical=link,
                A_physical=candidate, baseline_physical=reference, B_physical=previous['B_physical'],
                native_comparisons=comparisons, reference_review_sha256=sha(old_path),
                original_area_ratio=area/baseline['physical']['standard_cell_area_um2'],
                same_flow_area_ratio=area/reference['standard_cell_area_um2'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--analysis', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), 'preserve earlier review')
    result = review(args.analysis.resolve())
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('formal', 'formal_to_physical', 'A_physical',
                                                              'baseline_physical', 'B_physical', 'native_comparisons')}, indent=2))


if __name__ == '__main__':
    main()
