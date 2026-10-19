"""Bind the authorized LSU A experiment to the immutable measured baseline."""
import json
from pathlib import Path
from baseline_contract import ROOT, MANIFEST, load, validate, sha

BASELINE_COMMIT='58a4159da0372b3286758be1e6c1b50f9f28cc27'
BASELINE_INPUTS_SHA256='ad56ddd224ec34bd78f9fdef542a6b06535581927db3af395988ba6cbafe4bad'
ALLOWED_RTL={'rtl/lsu/rv32_ooo_lsu.sv'}
SIM_INPUTS=['scripts/build_sim.sh','sim/scripts/rv32_ooo_core.f','sim/tb/sim_main.cpp','sim/tb/sim_mem.cpp',
            *[str(p.relative_to(ROOT)) for p in sorted((ROOT/'sim/tb').glob('*.h'))]]
PHYSICAL_INPUTS=['physical/asap7/baseline/config.mk','physical/asap7/baseline/lower_processes.tcl',
                 'physical/asap7/baseline/eco.mk','physical/asap7/baseline/repair.tcl',
                 'physical/asap7/baseline/report.tcl','physical/asap7/baseline/timing_common.tcl',
                 'physical/asap7/toolchain.lock']


def reference_sha(name):
    # Minimal pinned sv2v images have no git. This hash-only inventory was
    # extracted from git show BASELINE_COMMIT, then anchored here by its SHA.
    path=ROOT/'experiments/lsu-a-v1/baseline-inputs.json'
    if sha(path)!=BASELINE_INPUTS_SHA256:raise ValueError('baseline input inventory changed')
    inventory=json.loads(path.read_text())
    if inventory['baseline_commit']!=BASELINE_COMMIT:raise ValueError('baseline inventory revision changed')
    return inventory['files_sha256'][name]


def validate_experiment(contract):
    if contract.get('experiment_id')!='lsu-a-v1' or contract.get('baseline_commit')!=BASELINE_COMMIT:
        raise ValueError('unrecognized experiment or baseline commit')
    if contract.get('state')!='inputs_frozen':raise ValueError('candidate inputs not frozen')
    if set(contract.get('allowed_rtl_changes',[]))!=ALLOWED_RTL:
        raise ValueError('only the approved LSU A RTL scope is allowed')
    if (sha(MANIFEST)!=contract['baseline_manifest_sha256']
            or sha(MANIFEST)!=reference_sha(str(MANIFEST.relative_to(ROOT)))):
        raise ValueError('frozen baseline manifest changed')
    baseline=load();validate(baseline)
    if baseline['state']!='frozen':raise ValueError('baseline not frozen')
    expected=contract['candidate_rtl_files_sha256'];original=baseline['rtl_files_sha256']
    if set(expected)!=set(original):raise ValueError('RTL input file set changed')
    changed={name for name in expected if expected[name]!=original[name]}
    if changed!=ALLOWED_RTL:raise ValueError('candidate changes extend beyond LSU A or contain no A change')
    for name,digest in expected.items():
        if sha(ROOT/name)!=digest:raise ValueError('live candidate RTL changed: '+name)
    for names,key in [(SIM_INPUTS,'simulation_inputs_sha256'),(PHYSICAL_INPUTS,'physical_inputs_sha256')]:
        wanted=contract[key]
        if set(wanted)!=set(names):raise ValueError('comparison input file set changed: '+key)
        for name,digest in wanted.items():
            if sha(ROOT/name)!=digest or reference_sha(name)!=digest:
                raise ValueError('baseline simulation/physical policy changed: '+name)
    memory=baseline['memory']
    if contract.get('memory_ps')!=10000 or any(memory[k]!=10000 for k in
            ['reference_core_period_ps','instruction_response_ps','instruction_initiation_interval_ps','data_response_ps']):
        raise ValueError('memory service must stay at the frozen 10000 ps')
    if contract.get('planning_targets')!=baseline['planning_targets']:
        raise ValueError('approved planning targets changed')
    return baseline


def load_experiment(path):
    path=Path(path).resolve()
    if not path.is_relative_to(ROOT/'experiments'):raise ValueError('experiment contract must be tracked under experiments/')
    contract=json.loads(path.read_text())
    return contract,validate_experiment(contract)
