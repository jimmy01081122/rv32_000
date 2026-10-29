#!/usr/bin/env python3
"""Compare complete mapped FPU graphs, independent of generated cell/net names."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

MODULE = 'rv32_ooo_fp_execute'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical_graph(module):
    """Canonical traversal from ordered output ports, including FF feedback.

    Each cell has one identity even when several paths reach it. Thus sharing,
    fanout, pin order, sequential feedback, constants and unused input ports are
    retained, rather than comparing expression trees or just cell counts.
    Unreachable cells fail closed; the native mapped cleanup removes them.
    """
    cells = module['cells']
    if any('init' in n.get('attributes',{}) for n in module.get('netnames',{}).values()):
        raise ValueError('mapped wire initialization is not supported by this comparison')
    drivers, primary = {}, {}
    for name, port in sorted(module['ports'].items()):
        if port['direction'] not in ('input', 'output'):
            raise ValueError('inout boundary is unsupported')
        if port['direction'] == 'input':
            for index, bit in enumerate(port['bits']):
                if not isinstance(bit, int):
                    raise ValueError('constant primary input')
                primary.setdefault(bit, []).append([name, index])
    for name, cell in cells.items():
        if set(cell['connections']) != set(cell['port_directions']):
            raise ValueError('unknown cell pin direction: ' + name)
        for port, bits in cell['connections'].items():
            direction = cell['port_directions'][port]
            if direction not in ('input', 'output'):
                raise ValueError('inout cell pin is unsupported')
            if direction == 'output':
                for index, bit in enumerate(bits):
                    if not isinstance(bit, int) or bit in drivers or bit in primary:
                        raise ValueError('constant or multiply driven cell output')
                    drivers[bit] = (name, port, index)
    ids, records, pending = {}, [], []

    def signal(bit):
        if isinstance(bit, str):
            if bit not in ('0', '1'):
                raise ValueError('undefined mapped signal')
            return ['constant', bit]
        if bit in primary:
            return ['input', primary[bit]]
        if bit not in drivers:
            raise ValueError('undriven mapped signal')
        name, port, index = drivers[bit]
        if name not in ids:
            ids[name] = len(records)
            records.append(None)
            pending.append(name)
        return ['cell', ids[name], port, index]

    ports = {}
    for name, port in sorted(module['ports'].items()):
        ports[name] = {k: port[k] for k in ('direction', 'offset', 'upto', 'signed') if k in port}
        ports[name]['bits'] = [signal(bit) for bit in port['bits']]
    cursor = 0
    while cursor < len(pending):
        name = pending[cursor]
        cursor += 1
        cell = cells[name]
        records[ids[name]] = dict(type=cell['type'], parameters=cell['parameters'],
                                 ports={p: dict(direction=cell['port_directions'][p],
                                               bits=[signal(b) for b in bits])
                                        for p, bits in sorted(cell['connections'].items())})
    if len(ids) != len(cells):
        raise ValueError(f'{len(cells)-len(ids)} cells are unreachable from outputs')
    graph = dict(ports=ports, cells=records)
    encoded = json.dumps(graph, sort_keys=True, separators=(',', ':')).encode()
    return graph, digest(encoded)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('output already exists')
    rows = {}
    reference = None
    for variant in ('baseline', 'A', 'B'):
        directory = args.run / variant
        run = json.loads((directory / 'run.json').read_text())
        if not (run.get('flow_completed') and run.get('input_identities_unchanged') and run.get('returncode') == 0):
            raise ValueError('native synthesis is incomplete: ' + variant)
        path = directory / 'results/asap7/rv32_post_lsu_v1/base/fp_mapped.rtlil.json'
        raw = path.read_bytes()
        module = json.loads(raw)['modules'][MODULE]
        graph, sha = canonical_graph(module)
        if reference is None:
            reference = graph
        counts = Counter(c['type'] for c in module['cells'].values())
        rows[variant] = dict(input=str(path), input_sha256=digest(raw),
                             graph_sha256=sha, identical_to_baseline=graph == reference,
                             cells=len(module['cells']), cell_types=dict(sorted(counts.items())))
    passed = all(r['identical_to_baseline'] for r in rows.values())
    args.output.write_text(json.dumps(dict(scope='exact mapped connectivity including sequential feedback; not functional equivalence or PPA',
                                          variants=rows, passed=passed), indent=2) + '\n')
    print(json.dumps(dict(passed=passed, hashes={n:r['graph_sha256'] for n,r in rows.items()})))
    raise SystemExit(0 if passed else 1)


if __name__ == '__main__':
    main()
