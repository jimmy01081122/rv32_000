#!/usr/bin/env python3
"""Negative controls for the numerical evidence checker (no toolchain needed)."""
import json
from pathlib import Path
import struct
import tempfile
import unittest

from qualify_fp_balanced import validate


class NumericalEvidence(unittest.TestCase):
    def check_values(self, values, case=None, mutation=None):
        if case is None:
            case = {'name': 'pid', 'expected_double': [0.5, -1.0],
                    'absolute_tolerance': 1e-5, 'relative_tolerance': 1e-5}
        words = [struct.unpack('<I', struct.pack('<f', x))[0] for x in values]
        checksum = 2166136261
        for word in words:
            checksum = ((checksum ^ word) * 16777619) & 0xffffffff
        lines = [f'FP DATA {i:08x} {word:08x}' for i, word in enumerate(words)]
        lines.append(f'FP BALANCED PASS name={case["name"]} checksum={checksum:08x} cycles=00000001 checked={len(words):08x}')
        if mutation:
            lines = mutation(lines)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'output.log'
            path.write_text('\n'.join(lines) + '\n')
            result = validate(case, path)
        json.dumps(result, allow_nan=False)
        return result

    def test_correct_output(self):
        self.assertTrue(self.check_values([0.5, -1])['passed'])

    def test_wrong_value_with_valid_checksum(self):
        result = self.check_values([0.5, -0.75])
        self.assertTrue(result['checksum_verified'])
        self.assertFalse(result['passed'])

    def test_nan_and_infinity_are_failures(self):
        for value in (float('nan'), float('inf'), -float('inf')):
            with self.subTest(value=value):
                self.assertFalse(self.check_values([0.5, value])['passed'])

    def test_missing_and_duplicate_samples(self):
        self.assertFalse(self.check_values([0.5, -1], mutation=lambda lines: lines[1:])['passed'])
        def duplicate(lines):
            lines[1] = lines[1].replace('00000001', '00000000', 1)
            return lines
        self.assertFalse(self.check_values([0.5, -1], mutation=duplicate)['passed'])

    def test_svm_labels_require_exact_equality(self):
        case = {'name': 'svm', 'expected_double': [0, 1],
                'absolute_tolerance': 0, 'relative_tolerance': 0}
        self.assertFalse(self.check_values([0, 0], case)['passed'])

    def test_cholesky_residual_rejects_pointwise_acceptable_error(self):
        case = {'name': 'cholesky', 'expected_double': [1, 0, 1],
                'absolute_tolerance': 1e-4, 'relative_tolerance': 2e-4,
                'dimensions': {'n': 2}, 'arrays': {'A': [1, 0, 0, 1]},
                'notes': {'reconstruction_relative_inf_limit': 2e-5}}
        result = self.check_values([1.0001, 0, 1.0001], case)
        self.assertEqual(result['failed_indices'], [])
        self.assertFalse(result['passed'])
        self.assertFalse(self.check_values([1, 0, float('nan')], case)['passed'])


if __name__ == '__main__':
    unittest.main()
