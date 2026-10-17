"""Deterministic provisional FP32 inputs and independent host-double references.

Inputs are rounded to binary32 before computing references. References never
call the measured library kernels. No training or random data generation occurs.
"""
from __future__ import annotations

import math
from pathlib import Path
import struct

NAMES = ('fir', 'iir', 'fft', 'pid', 'gemm', 'bicg', 'cholesky', 'svm')


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def pattern(path, floating):
    lines = path.read_text().splitlines()
    words = [int(x, 16) for x in lines if x.startswith('0x')]
    if len(words) != int(lines[1]):
        raise ValueError(f'pattern count mismatch: {path}')
    if floating:
        return [struct.unpack('<f', struct.pack('<I', x))[0] for x in words]
    return words


def cholesky(a):
    n = len(a)
    lower = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            value = a[i][j] - math.fsum(lower[i][k] * lower[j][k] for k in range(j))
            lower[i][j] = math.sqrt(value) if i == j else value / lower[j][j]
    return lower


def condition_inf(a, lower):
    n = len(a)
    inverse = [[0.0] * n for _ in range(n)]
    for col in range(n):
        y, x = [0.0] * n, [0.0] * n
        for i in range(n):
            y[i] = ((1.0 if i == col else 0.0) - math.fsum(lower[i][k] * y[k] for k in range(i))) / lower[i][i]
        for i in reversed(range(n)):
            x[i] = (y[i] - math.fsum(lower[k][i] * x[k] for k in range(i + 1, n))) / lower[i][i]
        for i in range(n):
            inverse[i][col] = x[i]
    return max(sum(abs(x) for x in row) for row in a) * max(sum(abs(x) for x in row) for row in inverse)


def fixture(name, cmsis):
    arrays, dimensions, notes = {}, {}, {}
    atol, rtol = 1e-5, 1e-5
    if name == 'fir':
        x = [(int((i * 37 + 11) % 113) - 56) / 64 for i in range(256)]
        c = [(int((k * 17 + 3) % 43) - 21) / 512 for k in range(32)]
        y = [math.fsum(c[k] * x[n - 31 + k] for k in range(32) if n - 31 + k >= 0) for n in range(256)]
        arrays = {'input': x, 'coeff': c}
        expected = (y + x[-31:]) * 2
        dimensions = {'samples': 256, 'taps': 32, 'split_block': 64}
        notes['reference'] = 'Direct convolution; terminal delay line; whole-block and 4x64 streaming'
    elif name == 'iir':
        x = [((i * 37 + 11) % 113 - 56) / 64 for i in range(256)]
        coeff = sum(([0.25 + s / 64, 0.125, 0.0625, 0.5, -0.125] for s in range(4)), [])
        stage_input, states = x[:], []
        for s in range(4):
            b0, b1, b2, a1, a2 = coeff[s * 5:s * 5 + 5]
            y, x1, x2, y1, y2 = [], 0.0, 0.0, 0.0, 0.0
            for sample in stage_input:
                out = math.fsum((b0 * sample, b1 * x1, b2 * x2, a1 * y1, a2 * y2))
                y.append(out)
                x2, x1, y2, y1 = x1, sample, y1, out
            states += [b1 * x1 + b2 * x2 + a1 * y1 + a2 * y2, b2 * x1 + a2 * y1]
            stage_input = y
        arrays = {'input': x, 'coeff': coeff}
        expected = (stage_input + states) * 2
        dimensions = {'samples': 256, 'sections': 4, 'split_block': 64}
        atol, rtol = 1e-6, 2e-5
        notes.update(reference='Double direct-form-I cascade vs measured DF2T; terminal states; streaming split',
                     pole_radius=math.sqrt(0.125))
    elif name == 'fft':
        n = 256
        real = [((i * 37 + 11) % 113 - 56) / 64 for i in range(n)]
        imag = [((i * 19 + 5) % 79 - 39) / 64 for i in range(n)]
        expected = []
        for k in range(n):
            angles = [-2 * math.pi * k * j / n for j in range(n)]
            expected += [math.fsum(real[j] * math.cos(a) - imag[j] * math.sin(a) for j, a in enumerate(angles)),
                         math.fsum(real[j] * math.sin(a) + imag[j] * math.cos(a) for j, a in enumerate(angles))]
        arrays = {'input': [v for pair in zip(real, imag) for v in pair]}
        dimensions = {'points': n}
        atol, rtol = 2e-5, 2e-5
        notes['reference'] = 'Double O(N^2) forward DFT, negative exponent, unnormalized, all real/imaginary outputs'
    elif name == 'pid':
        x = [((i * 13 + 7) % 97 - 48) / 64 for i in range(512)]
        kp, ki, kd = 0.5, 1 / 64, 0.125
        y = [kp * v + ki * math.fsum(x[:i + 1]) + kd * (v - (x[i - 1] if i else 0)) for i, v in enumerate(x)]
        arrays = {'input': x, 'gains': [kp, ki, kd]}
        expected = y + [x[-1], x[-2], y[-1]]
        dimensions = {'samples': 512}
        notes['reference'] = 'Double positional PID using integral sum, vs incremental CMSIS recurrence; all outputs and state'
    elif name == 'gemm':
        ni, nj, nk = 20, 25, 30
        a = [[f32((i * (k + 1) % nk) / nk) for k in range(nk)] for i in range(ni)]
        b = [[f32((k * (j + 2) % nj) / nj) for j in range(nj)] for k in range(nk)]
        c = [[f32(((i * j + 1) % ni) / ni) for j in range(nj)] for i in range(ni)]
        alpha, beta = f32(1.5), f32(1.2)
        arrays = {'A': sum(a, []), 'B': sum(b, []), 'C': sum(c, []), 'scalars': [alpha, beta]}
        expected = [alpha * math.fsum(a[i][k] * b[k][j] for k in range(nk)) + beta * c[i][j] for i in range(ni) for j in range(nj)]
        dimensions = {'ni': ni, 'nj': nj, 'nk': nk}
        notes['reference'] = 'Double dot products with math.fsum; PolyBench MINI initialization rounded to float'
    elif name == 'bicg':
        m, n = 38, 42
        a = [[f32((i * (j + 1) % n) / n) for j in range(m)] for i in range(n)]
        p, r = [f32(i / m) for i in range(m)], [f32(i / n) for i in range(n)]
        arrays = {'A': sum(a, []), 'p': p, 'r': r}
        expected = [math.fsum(r[i] * a[i][j] for i in range(n)) for j in range(m)]
        expected += [math.fsum(a[i][j] * p[j] for j in range(m)) for i in range(n)]
        dimensions = {'m': m, 'n': n}
        notes['reference'] = 'Separate double A-transpose*r and A*p with math.fsum'
    elif name == 'cholesky':
        n = 40
        base = [[(1.0 if j == i else f32(f32(-j / n) + 1)) if j <= i else 0.0 for j in range(n)] for i in range(n)]
        a = [[0.0] * n for _ in range(n)]
        for t in range(n):
            for i in range(n):
                for j in range(n):
                    a[i][j] = f32(a[i][j] + f32(base[i][t] * base[j][t]))
        lower = cholesky(a)
        arrays = {'A': sum(a, [])}
        expected = [lower[i][j] for i in range(n) for j in range(i + 1)]
        dimensions = {'n': n}
        atol, rtol = 1e-4, 2e-4
        notes.update(reference='Independent double Cholesky on serialized float32 input; full lower triangle plus reconstruction',
                     condition_inf=condition_inf(a, lower), reconstruction_relative_inf_limit=2e-5)
    elif name == 'svm':
        p = cmsis / 'Testing/Patterns/DSP/SVM/SVMF32'
        dims = pattern(p / 'Dims1_s16.txt', False)
        params = pattern(p / 'Params1_f32.txt', True)
        samples = pattern(p / 'Samples1_f32.txt', True)
        labels = pattern(p / 'Reference1_s32.txt', False)
        kind, class0, class1, count, dim, sv = dims
        assert kind == 1 and len(params) == sv * dim + sv + 1
        assert len(samples) == count * dim and len(labels) == count
        support, dual, intercept = params[:sv * dim], params[sv * dim:-1], params[-1]
        # An independent linear weight vector folds the support vectors first.
        weights = [math.fsum(dual[k] * support[k * dim + j] for k in range(sv)) for j in range(dim)]
        decisions = [intercept + math.fsum(weights[j] * samples[i * dim + j] for j in range(dim)) for i in range(count)]
        expected = [class1 if x > 0 else class0 for x in decisions]
        assert expected == labels, 'Pinned SVM labels differ from independent double prediction'
        arrays = {'params': params, 'input': samples}
        dimensions = {'samples': count, 'dimension': dim, 'support_vectors': sv, 'class0': class0, 'class1': class1}
        atol, rtol = 0.0, 0.0
        notes.update(reference='Pinned upstream test-1 labels and independent folded-weight double decisions',
                     minimum_absolute_decision=min(map(abs, decisions)), decisions=decisions,
                     patterns='CMSIS-DSP Testing/Patterns/DSP/SVM/SVMF32/*1_*')
    else:
        raise ValueError(name)
    return {'name': name, 'dimensions': dimensions, 'arrays': arrays, 'expected_double': expected,
            'absolute_tolerance': atol, 'relative_tolerance': rtol, 'notes': notes}


def write_header(case, path):
    def literal(value):
        return f32(value).hex() + 'f'
    lines = ['/* Generated provisional data; see fixture.json for reference and tolerances. */',
             f'#define FP_NAME "{case["name"]}"',
             f'#define FP_ATOL {literal(case["absolute_tolerance"])}',
             f'#define FP_RTOL {literal(case["relative_tolerance"])}',
             f'#define FP_EXPECT_COUNT {len(case["expected_double"])}u']
    for name, value in case['dimensions'].items():
        lines.append(f'#define FX_{name.upper()} {value}u')
    for name, values in [*case['arrays'].items(), ('expected', case['expected_double'])]:
        lines.append(f'static const float fx_{name}[{len(values)}] = {{')
        for i in range(0, len(values), 6):
            lines.append('  ' + ', '.join(literal(x) for x in values[i:i + 6]) + ',')
        lines.append('};')
    path.write_text('\n'.join(lines) + '\n')
