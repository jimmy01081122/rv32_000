"""Bind scored results to the actual normal/assert builds and functional run."""
import json
from pathlib import Path
from baseline_contract import ROOT, sha


def artifact_path(value):
    """Resolve recorded repository/container paths without rewriting evidence."""
    path = Path(value)
    if not path.is_absolute():
        path = ROOT/path
    elif not path.is_relative_to(ROOT) and path.is_relative_to('/workspace'):
        path = ROOT/path.relative_to('/workspace')
    path = path.resolve()
    if not path.is_relative_to(ROOT/'build'):
        raise ValueError('execution artifact is outside repository build/: '+str(value))
    return path


def clean_success(report, label):
    start = report.get('start', {})
    if (report.get('passed') is not True or not start.get('commit') or
            start.get('status') != '' or report.get('end') != start):
        raise ValueError(label+' lacks successful clean start/end proof')


def artifacts(value):
    """Check recorded raw log/trace identities, including nested suite runs."""
    if isinstance(value, dict):
        for name in ['log', 'trace']:
            if name in value and name+'_sha256' in value:
                if sha(artifact_path(value[name])) != value[name+'_sha256']:
                    raise ValueError('functional/build '+name+' changed')
        for child in value.values():
            artifacts(child)
    elif isinstance(value, list):
        for child in value:
            artifacts(child)


def option(command, name):
    if command.count(name) != 1 or command.index(name)+1 >= len(command):
        raise ValueError('missing/duplicated execution option: '+name)
    return command[command.index(name)+1]


def retired_work(profile):
    rows = [p for p in profile['pcs'] if p['retired']]
    counts = {(p['pc'], p['insn'], p['kind']):p['retired'] for p in rows}
    if len(rows) != len(counts) or any(value <= 0 for value in counts.values()):
        raise ValueError('invalid/duplicated per-PC retired-work record')
    return counts


def measurement_command(record, normal, directory, period):
    command = record['execution']['command']
    if not command or artifact_path(command[0]) != normal:
        raise ValueError('measurement command uses a different simulator')
    values = {}
    for argument in command[1:]:
        key, separator, value = argument.partition('=')
        if not separator or key in values:
            raise ValueError('invalid/duplicated measurement argument')
        values[key] = value
    paths = {'+elf':directory/'input.elf', '+memory-audit':directory/'memory.json',
             '+profile-core-roi':directory/'profile.json'}
    expected = {'+max-cycles':'100000000', '+core-period-ps':str(period),
                '+imem-response-ps':'10000', '+imem-interval-ps':'10000',
                '+dmem-response-ps':'10000', **{key:None for key in paths}}
    if set(values) != set(expected):
        raise ValueError('measurement command differs from frozen timing/input policy')
    for key, value in expected.items():
        if key in paths:
            if artifact_path(values[key]) != paths[key].resolve():
                raise ValueError('measurement command is bound to different raw artifacts')
        elif values[key] != value:
            raise ValueError('measurement command timing/cycle policy changed')


def review_provenance(experiment_path, experiment, measurement, build_summary, qualification_summary):
    if build_summary is None or qualification_summary is None:
        raise ValueError('explicit build and functional qualification summaries required')
    build_summary = Path(build_summary)
    qualification_summary = Path(qualification_summary)
    build = json.loads(build_summary.read_text())
    qualification = json.loads(qualification_summary.read_text())
    clean_success(build, 'build')
    clean_success(qualification, 'functional qualification')
    digest = sha(experiment_path)
    build_digest = sha(build_summary)
    sources = {**experiment['candidate_rtl_files_sha256'], **experiment['simulation_inputs_sha256']}
    if (build.get('experiment_manifest_sha256') != digest or
            build.get('experiment_id') != experiment['experiment_id'] or
            build.get('source_sha256') != sources or
            build.get('wrapper_sha256') != sha(ROOT/'scripts/build_experiment_sim.py')):
        raise ValueError('build source/experiment/wrapper identity differs')
    if (not build.get('verilator_version', '').startswith('Verilator 4.038 ') or
            '11.4.0' not in build.get('gxx_version', '')):
        raise ValueError('build tools differ from pinned versions')
    if (measurement.get('build_summary_sha256') != build_digest or
            qualification.get('build_summary_sha256') != build_digest or
            qualification.get('experiment_manifest_sha256') != digest):
        raise ValueError('measurement/functional run are not bound to this build proof')
    if measurement.get('wrapper_sha256') != sha(ROOT/'scripts/measure_cpu_experiment.py'):
        raise ValueError('measurement wrapper identity differs')
    if set(build.get('executables', {})) != {'normal', 'assert'} or len(build.get('records', [])) != 2:
        raise ValueError('both normal/assert build records required')
    binaries = {}
    for mode in ['normal', 'assert']:
        executable = build['executables'][mode]
        binary = artifact_path(executable['path'])
        generated = binary.parent/'Vrv32_ooo_core__verFiles.dat'
        if sha(binary) != executable['sha256'] or sha(generated) != executable['verFiles_sha256']:
            raise ValueError('candidate executable/generated build proof changed')
        command = next((line for line in generated.read_text().splitlines() if line.startswith('C ')), None)
        if command != executable['verilator_command'] or (' --assert ' in command) != (mode == 'assert'):
            raise ValueError('generated normal/assert build mode differs')
        binaries[mode] = binary
    for record in build['records']:
        if record.get('returncode') != 0:
            raise ValueError('failed build record')
    artifacts(build['records'])
    if measurement.get('simulator_sha256') != build['executables']['normal']['sha256']:
        raise ValueError('measurement simulator is not the qualified normal executable')

    records = qualification.get('records', [])
    names = [r['name'] for r in records]
    if (len(records) != 22 or len(set(names)) != 22 or
            any(not name.startswith('directed-') for name in names[:18]) or
            names[18:] != ['spike', 'interface', 'memory', 'fma'] or
            any(r.get('passed') is not True or r['execution']['returncode'] != 0 for r in records)):
        raise ValueError('complete successful directed18 and four functional suites required')
    artifacts(records)
    for record in records[:18]:
        command = record['execution']['command']
        elf_args = [arg[5:] for arg in command[1:] if arg.startswith('+elf=')]
        if (artifact_path(command[0]) != binaries['normal'] or len(elf_args) != 1 or
                sha(artifact_path(elf_args[0])) != record['elf_sha256']):
            raise ValueError('directed qualification used a different executable/ELF')
        text = artifact_path(record['execution']['log']).read_text()
        if 'PASS (0)' not in text or 'TRAP encountered' in text:
            raise ValueError('directed qualification raw result failed')
    suite_files = {'spike':'spike/diff_results.json', 'interface':'interface/summary.json',
                   'memory':'memory/summary.json', 'fma':'fma/summary.json'}
    normal_sha = build['executables']['normal']['sha256']
    assert_sha = build['executables']['assert']['sha256']
    for record in records[18:]:
        name = record['name']
        source = qualification_summary.parent/suite_files[name]
        if sha(source) != record['summary_sha256']:
            raise ValueError('functional suite summary changed: '+name)
        suite = json.loads(source.read_text())
        command = record['execution']['command']
        expected_binary = binaries['assert' if name in ['interface', 'memory'] else 'normal']
        if artifact_path(option(command, '--sim')) != expected_binary:
            raise ValueError('functional suite used a different simulator')
        if artifact_path(option(command, '--out')) != source.parent.resolve():
            raise ValueError('functional suite command points to different raw evidence')
        cases = suite.get('results' if name == 'spike' else 'records', [])
        identities = [(r.get('name'), r.get('mode')) for r in cases]
        if any(not row[0] for row in identities) or len(set(identities)) != len(identities):
            raise ValueError('duplicated/missing functional case identity')
        if name == 'spike':
            valid = (suite.get('all_passed') is True and suite.get('total') == 18 and
                     suite.get('passed') == 18 and len(suite.get('results', [])) == 18 and
                     all(r.get('pass') is True and r.get('diff_pass') is True for r in suite['results']))
        elif name in ['interface', 'memory']:
            valid = (suite.get('passed') is True and len(suite.get('records', [])) == (48 if name == 'interface' else 58)
                     and all(r.get('passed') is True for r in suite['records'])
                     and suite.get('simulator_sha256') == assert_sha)
            if name == 'memory':
                valid = valid and suite.get('reference_simulator_sha256') == normal_sha
                valid = valid and artifact_path(option(command, '--reference-sim')) == binaries['normal']
        else:
            valid = (suite.get('all_passed') is True and suite.get('vector_count') == 3400 and
                     suite.get('simulator_sha256') == normal_sha and
                     suite.get('fp_execute_sha256') == experiment['candidate_rtl_files_sha256']['rtl/execute/fp/rv32_ooo_fp_execute.sv']
                     and suite.get('oracle_sha256') == sha(ROOT/'scripts/fma_reference.py') and
                     len(suite.get('records', [])) == 2 and all(r.get('passed') is True for r in suite['records']))
        if not valid:
            raise ValueError('functional suite count/result/executable proof differs: '+name)
        artifacts(suite)
    return {'validator_sha256':sha(Path(__file__)), 'build_summary_sha256':build_digest,
            'qualification_summary_sha256':sha(qualification_summary),
            'normal_simulator_sha256':normal_sha, 'assert_simulator_sha256':assert_sha,
            'directed_cases':18, 'spike_cases':18, 'interface_cases':48,
            'fixed_time_controls':58, 'finite_fma_values':3400, 'passed':True}, binaries['normal']
