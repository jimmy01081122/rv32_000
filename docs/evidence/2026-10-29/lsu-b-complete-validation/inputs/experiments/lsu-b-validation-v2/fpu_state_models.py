#!/usr/bin/env python3
"""Build reset and inductive transition obligations for the holding-stage FPU.

The relation is derived only from externally visible registered outputs. No
internal arithmetic node is matched or assumed. Native CEC must discharge all
reset, step and output obligations before this relation establishes equivalence.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path

MODULE = 'rv32_ooo_fp_execute'
FF = 'DFFHQNx1_ASAP7_75t_R'


def checked(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path, name=MODULE):
    data = json.loads(path.read_text())
    checked(set(data['modules']) == {name}, 'unexpected module set')
    return data['modules'][name]


def observed(module):
    return module['ports']['cmp_data']['bits'] + module['ports']['cmp_valid']['bits']


def all_bits(module):
    for port in module['ports'].values():
        yield from port['bits']
    for cell in module['cells'].values():
        for bits in cell['connections'].values():
            yield from bits
    for net in module['netnames'].values():
        yield from net['bits']


class Builder:
    def __init__(self, module):
        self.module = copy.deepcopy(module)
        self.next_bit = max(b for b in all_bits(module) if isinstance(b, int)) + 1
        self.inversions = {}

    def bits(self, width):
        result = list(range(self.next_bit, self.next_bit + width))
        self.next_bit += width
        return result

    def invert(self, bit):
        if isinstance(bit, str):
            checked(bit in ('0', '1'), 'undefined relation constant')
            return '1' if bit == '0' else '0'
        if bit not in self.inversions:
            output = self.bits(1)[0]
            name = '$proof_invert_' + str(output)
            checked(name not in self.module['cells'], 'proof cell collision')
            self.module['cells'][name] = dict(
                hide_name=1, type='$_NOT_', parameters={}, attributes={},
                port_directions={'A': 'input', 'Y': 'output'},
                connections={'A': [bit], 'Y': [output]})
            self.inversions[bit] = output
        return self.inversions[bit]

    def replace(self, substitutions):
        def remap(bits):
            return [substitutions.get(bit, bit) for bit in bits]
        for port in self.module['ports'].values():
            port['bits'] = remap(port['bits'])
        for cell in self.module['cells'].values():
            cell['connections'] = {p: remap(bits) for p, bits in cell['connections'].items()}
        for net in self.module['netnames'].values():
            net['bits'] = remap(net['bits'])


def validate_library_cell(cell):
    """Check the actual pinned Liberty model: positive CLK, QN(next) = NOT D."""
    checked(set(cell['ports']) == {'CLK', 'D', 'QN'}, 'unexpected FF interface')
    checked(len(cell['cells']) == 2, 'changed FF function model')
    ff = [c for c in cell['cells'].values() if c['type'] == '$_DFF_P_']
    inv = [c for c in cell['cells'].values() if c['type'] == '$_NOT_']
    checked(len(ff) == len(inv) == 1, 'unexpected FF model primitives')
    ff, inv = ff[0], inv[0]
    checked(ff['connections']['C'] == cell['ports']['CLK']['bits']
            and ff['connections']['Q'] == cell['ports']['QN']['bits']
            and ff['connections']['D'] == inv['connections']['Y']
            and inv['connections']['A'] == cell['ports']['D']['bits'], 'FF polarity/clock mismatch')
    checked(not ff['parameters'] and not inv['parameters'], 'unexpected cell parameters')


def gold_flops(module):
    flops = {n: c for n, c in module['cells'].items() if c['type'] == '$dff'}
    checked(len(flops) == 2, 'expected original data and valid state registers')
    next_bits = {}
    for cell in flops.values():
        checked(int(cell['parameters']['CLK_POLARITY'], 2) == 1
                and cell['connections']['CLK'] == module['ports']['clk']['bits'], 'gold clock changed')
        q, d = cell['connections']['Q'], cell['connections']['D']
        checked(len(q) == len(d) == int(cell['parameters']['WIDTH'], 2), 'gold width mismatch')
        for qb, db in zip(q, d):
            checked(qb not in next_bits, 'duplicate gold state driver')
            next_bits[qb] = db
    checked(len(next_bits) == 156 and set(next_bits) == set(observed(module)), 'gold hidden or missing state')
    checked(not any('init' in n.get('attributes', {}) for n in module['netnames'].values()), 'unexpected gold initialization')
    # The complete cell list is subsequently synthesized and checked for any
    # remaining state. This shape check is not itself a functional proof.
    return flops, next_bits


def mapped_relation(module):
    flops = {n: c for n, c in sorted(module['cells'].items()) if c['type'] == FF}
    checked(len(flops) == 100, 'expected 100 mapped FFs')
    states, ds, names = [], [], []
    for name, cell in flops.items():
        checked(not cell['parameters'] and set(cell['connections']) == {'CLK', 'D', 'QN'}
                and all(len(v) == 1 for v in cell['connections'].values())
                and cell['connections']['CLK'] == module['ports']['clk']['bits'], 'mapped FF/clock changed')
        states += cell['connections']['QN']; ds += cell['connections']['D']; names.append(name)
    checked(len(set(states)) == 100, 'duplicate mapped state driver')
    checked(not any('init' in n.get('attributes', {}) for n in module['netnames'].values()), 'unexpected mapped initialization')
    drivers = {}
    for name, cell in module['cells'].items():
        checked(set(cell['port_directions']) == set(cell['connections']), 'unknown pin direction')
        for pin, bits in cell['connections'].items():
            if cell['port_directions'][pin] == 'output':
                for bit in bits:
                    checked(bit not in drivers, 'multiple mapped drivers')
                    drivers[bit] = (name, cell)
    indices = {bit: i for i, bit in enumerate(states)}

    def trace(bit, active=None):
        active = set() if active is None else active
        if isinstance(bit, str):
            checked(bit in ('0', '1'), 'unknown output constant')
            return {'constant': int(bit)}
        if bit in indices:
            return {'state': indices[bit], 'invert': 0}
        checked(bit not in active and bit in drivers, 'output cycle/undriven signal')
        active.add(bit)
        _, cell = drivers[bit]
        if cell['type'] == 'TIELOx1_ASAP7_75t_R':
            checked(cell['connections'] == {'L': [bit]}, 'unexpected tie cell')
            return {'constant': 0}
        checked(cell['type'].startswith(('BUF', 'INV')) and set(cell['connections']) == {'A', 'Y'}
                and cell['connections']['Y'] == [bit] and len(cell['connections']['A']) == 1,
                'registered output has non-unary logic: ' + cell['type'])
        row = trace(cell['connections']['A'][0], active)
        if cell['type'].startswith('INV'):
            key = 'constant' if 'constant' in row else 'invert'
            row[key] ^= 1
        return row

    relation = [trace(bit) for bit in observed(module)]
    checked({r['state'] for r in relation if 'state' in r} == set(range(100)), 'unobserved mapped state')
    return flops, states, ds, names, relation


def gold_model(original, flops, next_bits, relation, reset):
    b = Builder(original)
    for name in flops:
        del b.module['cells'][name]
    qs = observed(original)
    b.module['ports']['next_observed'] = dict(direction='output', bits=[next_bits[q] for q in qs])
    if reset:
        b.module['ports']['proof_state'] = dict(direction='input', bits=qs)
    else:
        states = b.bits(100)
        substitutions = {}
        for q, row in zip(qs, relation):
            bit = str(row['constant']) if 'constant' in row else states[row['state']]
            if row.get('invert'):
                bit = b.invert(bit)
            substitutions[q] = bit
        b.replace(substitutions)
        b.module['ports']['proof_state'] = dict(direction='input', bits=states)
    return finish(b, reset)


def gate_model(original, flops, states, ds, relation, reset):
    b = Builder(original)
    for name in flops:
        del b.module['cells'][name]
    b.module['ports']['proof_state'] = dict(direction='input', bits=states)
    expanded = []
    for row in relation:
        if 'constant' in row:
            expanded.append(str(row['constant']))
        else:
            # Actual library model gives QN(next) = NOT D. Compose that
            # polarity with the independently traced output inversion.
            bit = ds[row['state']]
            expanded.append(b.invert(bit) if (1 ^ row['invert']) else bit)
    b.module['ports']['next_observed'] = dict(direction='output', bits=expanded)
    return finish(b, reset)


def finish(builder, reset):
    if reset:
        rst = builder.module['ports'].pop('rst')['bits']
        checked(len(rst) == 1, 'reset width changed')
        builder.replace({rst[0]: '1'})
        for name in list(builder.module['ports']):
            if builder.module['ports'][name]['direction'] == 'output' and name != 'next_observed':
                del builder.module['ports'][name]
    return builder.module


def zero_reference(module):
    ports = copy.deepcopy(module['ports'])
    for port in ports.values():
        if port['direction'] == 'output':
            port['bits'] = ['0'] * len(port['bits'])
    return dict(attributes={}, ports=ports, cells={}, netnames={})


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('original', 'mapped', 'cell', 'output'):
        ap.add_argument('--'+name, type=Path, required=True)
    args = ap.parse_args()
    args.output.mkdir()
    gold, gate, cell = load(args.original), load(args.mapped), load(args.cell, FF)
    checked({n: (p['direction'], len(p['bits'])) for n, p in gold['ports'].items()}
            == {n: (p['direction'], len(p['bits'])) for n, p in gate['ports'].items()}, 'interface mismatch')
    checked(not ({'proof_state', 'next_observed'} & gold['ports'].keys()), 'proof port collision')
    validate_library_cell(cell)
    gf, gd = gold_flops(gold)
    mf, states, ds, names, relation = mapped_relation(gate)
    models = {}
    for reset in (False, True):
        label = 'reset' if reset else 'step'
        models[label+'-gold'] = gold_model(gold, gf, gd, relation, reset)
        models[label+'-gate'] = gate_model(gate, mf, states, ds, relation, reset)
        if reset:
            for role in ('gold', 'gate'):
                models[label+'-'+role+'-zero'] = zero_reference(models[label+'-'+role])
    mutant = Builder(models['step-gate'])
    bits = mutant.module['ports']['next_observed']['bits']
    bits[115] = mutant.invert(bits[115])
    models['step-mutant'] = mutant.module
    for name, model in models.items():
        (args.output/(name+'.json')).write_text(json.dumps({'modules': {MODULE: model}}, separators=(',', ':'))+'\n')
    report = dict(scope='models only; sequential equivalence requires both reset-to-zero obligations and unrestricted step/output CEC',
                  initial_condition='at least one synchronous reset rising edge before observable comparison',
                  original_state_bits=156, mapped_state_bits=100,
                  library_transition='positive CLK; QN(next) = NOT D', state_names=names,
                  observation_order='cmp_data[0:154], cmp_valid', relation=relation,
                  inputs={str(getattr(args, n)): digest(getattr(args, n)) for n in ('original', 'mapped', 'cell')},
                  models={name: digest(args.output/(name+'.json')) for name in models})
    (args.output/'relation.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(original_state_bits=156, mapped_state_bits=100,
                          constant_observations=sum('constant' in r for r in relation), proof_pending=True)))


if __name__ == '__main__':
    main()
