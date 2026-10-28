#!/usr/bin/env python3
"""Replace only an isolated FPU body with one standalone mapped implementation.

The existing core bodies are copied byte-for-byte. No core reoptimization or
cross-boundary propagation is performed at this link step. Native read/link and
functional qualification must still pass before the output can be admitted.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
from compare_mapped import canonical_graph, MODULE

REL = Path('results/asap7/rv32_post_lsu_v1/base')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def modules(path):
    data = path.read_bytes()
    pairs = re.findall(rb'^module (\w+)\b(.*?^endmodule)', data, re.M | re.S)
    result = {name.decode(): b'module '+name+body for name, body in pairs}
    if len(result) != len(pairs):
        raise ValueError('duplicate modules')
    return result


def complete(directory):
    run = json.loads((directory / 'run.json').read_text())
    if not (run.get('returncode') == 0 and run.get('flow_completed')
            and run.get('input_identities_unchanged')):
        raise ValueError('incomplete native input: ' + str(directory))
    root = Path(__file__).resolve().parents[2]
    spec = json.loads((directory / 'job.json').read_text())
    for guest, expected in spec['inputs'].items():
        path = root / Path(guest).relative_to('/workspace')
        if sha(path.read_bytes()) != expected:
            raise ValueError('native input changed after completion: '+guest)
    log = root / Path(spec['log']).relative_to('/workspace')
    if sha(log.read_bytes()) != run.get('log_sha256'):
        raise ValueError('native log changed after completion')
    return run


def interface(module):
    return {n: {**{k:v for k,v in p.items() if k != 'bits'}, 'width':len(p['bits'])}
            for n,p in module['ports'].items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cores', type=Path, required=True)
    parser.add_argument('--unit', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('output must be fresh')
    complete(args.unit)
    unit_path = args.unit / REL / '1_2_yosys.v'
    unit_modules = modules(unit_path)
    if set(unit_modules) != {MODULE}:
        raise ValueError('standalone input must contain only the FPU')
    unit = json.loads((args.unit / REL / 'fp_mapped.rtlil.json').read_text())['modules'][MODULE]
    _, fingerprint = canonical_graph(unit)
    inputs, outputs = {}, {}
    for variant in ('baseline', 'A', 'B'):
        directory = args.cores / variant
        complete(directory)
        path = directory / REL / '1_2_yosys.v'
        original = modules(path)
        if set(original) != {'rv32_ooo_core', MODULE}:
            raise ValueError('expected exactly core and FPU modules')
        old_fp = json.loads((directory / REL / 'fp_mapped.rtlil.json').read_text())['modules'][MODULE]
        if interface(old_fp) != interface(unit):
            raise ValueError('FPU port interface changed: ' + variant)
        inputs[variant] = dict(netlist=str(path), netlist_sha256=sha(path.read_bytes()),
                               core_body_sha256=sha(original['rv32_ooo_core']),
                               native_report_sha256=sha((directory/'run.json').read_bytes()))
        outputs[variant] = b'// Shared standalone FPU mapping; see link-manifest.json.\n'+original['rv32_ooo_core']+b'\n'+unit_modules[MODULE]+b'\n'
    args.output.mkdir(parents=True)
    for variant, data in outputs.items():
        path = args.output / (variant+'.v')
        path.write_bytes(data)
        reread = modules(path)
        if sha(reread['rv32_ooo_core']) != inputs[variant]['core_body_sha256'] or reread[MODULE] != unit_modules[MODULE]:
            raise ValueError('linked output does not preserve module bodies')
        inputs[variant].update(linked_netlist=str(path), linked_sha256=sha(data))
    result = dict(scope='mapped module link only; no PPA admission',
                  unit_netlist=str(unit_path), unit_netlist_sha256=sha(unit_path.read_bytes()),
                  shared_fpu_body_sha256=sha(unit_modules[MODULE]), shared_fpu_graph_sha256=fingerprint,
                  interface=interface(unit), variants=inputs, passed=True)
    (args.output/'link-manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(passed=True, shared_fpu_graph_sha256=fingerprint)))


if __name__ == '__main__':
    main()
