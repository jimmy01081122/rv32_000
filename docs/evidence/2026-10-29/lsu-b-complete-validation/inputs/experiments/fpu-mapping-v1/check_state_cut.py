#!/usr/bin/env python3
"""Bind the CEC input models to the exact pre/post mapping state transition."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re

MODULE = 'rv32_ooo_fp_execute'
FF = 'DFFHQNx1_ASAP7_75t_R'
COMB = re.compile(r'(?:\$_(?:AND|OR|NOT|XOR|MUX)_|(?:AO|OA|AND|OR|NAND|NOR|XOR|XNOR|INV|BUF|MAJ|TIE)[A-Za-z0-9]*_ASAP7_75t_R)$')


def cut(module):
    if any('init' in n.get('attributes', {}) for n in module['netnames'].values()):
        raise ValueError('unexpected initial state')
    if any(c['type'] != FF and not COMB.fullmatch(c['type']) for c in module['cells'].values()):
        raise ValueError('unreviewed cell type')
    flops = {n: c for n, c in sorted(module['cells'].items()) if c['type'] == FF}
    if len(flops) != 100:
        raise ValueError('expected 100 mapped state bits')
    result = copy.deepcopy(module)
    state, nextstate, signature = [], [], {}
    for name, cell in flops.items():
        if (cell['port_directions'] != {'CLK': 'input', 'D': 'input', 'QN': 'output'}
                or cell['parameters'] or set(cell['connections']) != {'CLK', 'D', 'QN'}
                or any(len(bits) != 1 for bits in cell['connections'].values())
                or cell['connections']['CLK'] != module['ports']['clk']['bits']):
            raise ValueError('unexpected flip-flop or clock mapping: '+name)
        state.extend(cell['connections']['QN'])
        nextstate.extend(cell['connections']['D'])
        signature[name] = dict(type=cell['type'], clock_port='clk', parameters=cell['parameters'])
        del result['cells'][name]
    if {'state', 'nextstate'} & result['ports'].keys():
        raise ValueError('cut-point port collision')
    result['ports']['state'] = dict(direction='input', bits=state)
    result['ports']['nextstate'] = dict(direction='output', bits=nextstate)
    return result, signature


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ('pre', 'mapped', 'gold', 'gate', 'output'):
        parser.add_argument('--'+arg, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('output must be fresh')
    modules, hashes = {}, {}
    for key in ('pre', 'mapped', 'gold', 'gate'):
        data = getattr(args, key).read_bytes()
        design = json.loads(data)
        if set(design['modules']) != {MODULE}:
            raise ValueError('unexpected module set')
        modules[key] = design['modules'][MODULE]
        hashes[key] = hashlib.sha256(data).hexdigest()
    gold, sig1 = cut(modules['pre'])
    gate, sig2 = cut(modules['mapped'])
    checks = dict(identical_state_identity_and_clock=sig1 == sig2,
                  exact_gold_model=gold == modules['gold'], exact_gate_model=gate == modules['gate'])
    result = dict(passed=all(checks.values()), checks=checks, state_bits=100, inputs=hashes)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))
    raise SystemExit(0 if result['passed'] else 1)


if __name__ == '__main__':
    main()
