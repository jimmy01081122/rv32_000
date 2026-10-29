#!/usr/bin/env python3
"""Exercise the real mapping/readback reviewers with corrupted measured inputs."""
import argparse
import copy
import gzip
import json
from pathlib import Path
import subprocess
import sys

from compare_mapped import canonical_graph, MODULE
from check_readback import read_flat, name


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--unit-json', type=Path, required=True)
    parser.add_argument('--readback', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir()  # Never overwrite a prior attempt.
    module = json.loads(args.unit_json.read_text())['modules'][MODULE]
    _, reference = canonical_graph(module)
    mutant = copy.deepcopy(module)
    bits = mutant['ports']['issue_req']['bits']
    bits[0], bits[1] = bits[1], bits[0]
    _, changed = canonical_graph(mutant)
    records = [dict(control='swapped_input_bits', rejected=changed != reference)]
    mutant = copy.deepcopy(module)
    next(iter(mutant['netnames'].values())).setdefault('attributes', {})['init'] = '0'
    try:
        canonical_graph(mutant)
        rejected = False
    except ValueError as exc:
        rejected = 'initialization' in str(exc)
    records.append(dict(control='unsupported_initial_state', rejected=rejected))

    source = args.readback.resolve()
    cells, resolve = read_flat(source / 'baseline-flat.v')
    live = next(inst for inst, (_, pins) in cells.items()
                if any(pin in {'Y', 'QN', 'Q', 'H', 'L'} and resolve(net) in resolve.top_outputs
                       for pin, net in pins.items()))
    for control in ('changed_pin', 'missing_live_cell'):
        directory = args.output / control
        directory.mkdir()
        for variant in ('baseline', 'A', 'B'):
            (directory / (variant+'-flat.v')).symlink_to(source / (variant+'-flat.v'))
            export = variant+'-synthesis-connectivity.jsonl.gz'
            if variant != 'baseline':
                (directory / export).symlink_to(source / export)
                continue
            mutations = 0
            with gzip.open(source / export, 'rt') as src, gzip.open(directory / export, 'wt') as dst:
                for line in src:
                    inst, master, pins = json.loads(line)
                    if name(inst) == live:
                        mutations += 1
                        if control == 'missing_live_cell':
                            continue
                        pins[next(iter(pins))] = 'deliberately_wrong_net'
                    dst.write(json.dumps([inst, master, pins])+'\n')
            if mutations != 1:
                raise ValueError('negative control must modify exactly one live cell')
        command = [sys.executable, str(Path(__file__).with_name('check_readback.py')), str(directory)]
        with (directory / 'review.log').open('x') as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
        review = json.loads((directory / 'connectivity-review.json').read_text())
        records.append(dict(control=control, returncode=result.returncode, instance=live,
                            rejected=result.returncode == 1 and review['passed'] is False))
    passed = all(r['rejected'] for r in records)
    (args.output / 'summary.json').write_text(json.dumps(dict(passed=passed, records=records), indent=2)+'\n')
    print(json.dumps(dict(passed=passed, controls=len(records))))
    raise SystemExit(0 if passed else 1)


if __name__ == '__main__':
    main()
