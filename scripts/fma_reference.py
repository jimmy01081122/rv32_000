"""Exact integer oracle for finite binary32 fused operations and five RISC-V RMs."""
import random


def unpack(word):
    exponent, fraction = (word >> 23) & 255, word & 0x7fffff
    if exponent == 255:
        raise ValueError('This oracle covers finite input operands only')
    return bool(word >> 31), (fraction | 0x800000 if exponent else fraction), (exponent - 150 if exponent else -149)


def fused(a, b, c, operation=0, rm=0):
    sa, ma, ea = unpack(a)
    sb, mb, eb = unpack(b)
    sc, mc, ec = unpack(c)
    sp = sa ^ sb ^ (operation in (2, 3))
    sc ^= operation in (1, 3)
    ep = ea + eb
    low = min(ep, ec)
    value = ((-1 if sp else 1) * ma * mb << (ep - low)) + ((-1 if sc else 1) * mc << (ec - low))
    if value == 0:
        sign = sp if ma * mb == 0 and mc == 0 and sp == sc else rm == 2
        return int(sign) << 31, 0
    sign = value < 0
    value = abs(value)
    top = value.bit_length() - 1 + low
    quantum = max(top - 23, -149)
    shift = quantum - low
    quotient, remainder = (value >> shift, value & ((1 << shift) - 1)) if shift > 0 else (value << -shift, 0)
    if remainder:
        half = 1 << (shift - 1)
        increment = ((remainder > half or (remainder == half and quotient & 1)) if rm == 0
                     else False if rm == 1 else sign if rm == 2 else not sign if rm == 3
                     else remainder >= half)
        quotient += int(increment)
    if quotient >= 1 << 24:
        quotient >>= 1
        quantum += 1
    if quotient >= 1 << 23 and quantum + 23 >= 128:
        infinity = rm in (0, 4) or (rm == 2 and sign) or (rm == 3 and not sign)
        return (int(sign) << 31) | (0x7f800000 if infinity else 0x7f7fffff), 5
    flags = int(bool(remainder))
    if quotient < 1 << 23:
        return (int(sign) << 31) | quotient, flags | (2 if remainder else 0)
    exponent = quantum + 23 + 127
    return (int(sign) << 31) | (exponent << 23) | (quotient & 0x7fffff), flags


def vectors():
    triples = [(0x3f800001, 0x3f7ffffe, 0xbf800000),
               (0x3f800001, 0x3f800000, 0xbf800000),
               (1, 0x3f800000, 0), (1, 0x3f000000, 0),
               (0x7fffff, 0x3f800000, 0), (0x7f7fffff, 0x40000000, 0),
               (0x3f800000, 0x3f800000, 0x33800000),
               (0, 0x80000000, 0x80000000), (0, 0, 0),
               (0x80000000, 0x3f800000, 0x80000000)]
    rng = random.Random(0x464d4132)
    for _ in range(64):
        triples.append(tuple((rng.randrange(2) << 31) | (rng.randrange(255) << 23) | rng.randrange(1 << 23) for _ in range(3)))
    for _ in range(64):
        a, b = [((rng.randrange(2) << 31) | (rng.randrange(100, 161) << 23) | rng.randrange(1 << 23)) for _ in range(2)]
        product, _ = fused(a, b, 0)
        triples.append((a, b, product ^ 0x80000000))
    exponents, fractions = (0, 1, 2, 125, 126, 127, 128, 252, 253, 254), (0, 1, 0x400000, 0x7ffffe, 0x7fffff)
    for _ in range(32):
        triples.append(tuple((rng.randrange(2) << 31) | (rng.choice(exponents) << 23) | rng.choice(fractions) for _ in range(3)))
    return [(operation, rm, a, b, c, *fused(a, b, c, operation, rm))
            for a, b, c in triples for operation in range(4) for rm in range(5)]
