import re
import sys

def format_id(ident):
    ident = ident.strip()
    if ident.startswith('\\') and not ident.endswith(' '):
        return ident + ' '
    return ident

def legalize_netlist(filepath):
    print(f"Reading {filepath}...")
    with open(filepath, 'r') as f:
        lines = f.readlines()

    pat_auto = re.compile(r'^\s*reg\s+\\\$auto\$verilog_backend')
    pat_2d_mem = re.compile(r'^\s*(wire|reg)\s+\[\d+:\d+\].*\[\d+:\d+\]\s*;')
    pat_reg = re.compile(r'^(\s*)reg(\s+)')
    pat_assign = re.compile(r'^\s*assign\s+([^=;]+)\s*=\s*(.+)\s*;\s*$')
    pat_ternary_colon = re.compile(r'\s+:\s+')
    pat_always_start = re.compile(r'^\s*always\s*@')
    pat_always_end = re.compile(r'^\s*end\s*$')

    out_lines = []
    new_wires = []
    inv_count = 0
    and_count = 0
    or_count = 0
    xor_count = 0
    mux_count = 0
    dropped_count = 0
    in_always = False

    for line in lines:
        if pat_always_start.search(line):
            in_always = True
            dropped_count += 1
            continue
        if in_always:
            dropped_count += 1
            if pat_always_end.search(line):
                in_always = False
            continue

        if pat_auto.search(line):
            dropped_count += 1
            continue
        if pat_2d_mem.search(line):
            dropped_count += 1
            continue
        if pat_reg.search(line):
            line = pat_reg.sub(r'\1wire\2', line)
            
        m = pat_assign.match(line)
        if m:
            lhs_raw = m.group(1).strip()
            rhs_raw = m.group(2).strip()
            lhs = format_id(lhs_raw)

            # Check if ternary MUX
            if '?' in rhs_raw and ':' in rhs_raw:
                q_pos = rhs_raw.find('?')
                m_col = pat_ternary_colon.search(rhs_raw[q_pos:])
                if m_col:
                    mux_count += 1
                    c_start = q_pos + m_col.start()
                    c_end = q_pos + m_col.end()
                    sel = format_id(rhs_raw[:q_pos].strip())
                    in1 = format_id(rhs_raw[q_pos+1:c_start].strip())
                    in0 = format_id(rhs_raw[c_end:].strip())
                    inv_wire = f"_legal_nsel_{mux_count}"
                    new_wires.append(f"  wire {inv_wire};\n")
                    out_lines.append(f"  INVx1_ASAP7_75t_R _legal_minv_{mux_count} ( .A({sel}), .Y({inv_wire}) );\n")
                    out_lines.append(f"  AO22x1_ASAP7_75t_R _legal_mux_{mux_count} ( .A1({sel}), .A2({in1}), .B1({inv_wire}), .B2({in0}), .Y({lhs}) );\n")
                    continue

            # Check if NOT
            if rhs_raw.startswith('~') and not any(op in rhs_raw for op in ['&', '|', '^']):
                inv_count += 1
                rhs = format_id(rhs_raw[1:].strip())
                out_lines.append(f"  INVx1_ASAP7_75t_R _legal_inv_{inv_count} ( .A({rhs}), .Y({lhs}) );\n")
                continue

            # Check if XOR
            if '^' in rhs_raw and not any(op in rhs_raw for op in ['&', '|', '?']):
                xor_count += 1
                parts = rhs_raw.split('^')
                op0 = format_id(parts[0].strip())
                op1 = format_id(parts[1].strip())
                out_lines.append(f"  XOR2x1_ASAP7_75t_R _legal_xor_{xor_count} ( .A({op0}), .B({op1}), .Y({lhs}) );\n")
                continue

            # Check if AND
            if '&' in rhs_raw and not any(op in rhs_raw for op in ['|', '^', '?']):
                and_count += 1
                parts = rhs_raw.split('&')
                op0 = format_id(parts[0].strip())
                op1 = format_id(parts[1].strip())
                out_lines.append(f"  AND2x2_ASAP7_75t_R _legal_and_{and_count} ( .A({op0}), .B({op1}), .Y({lhs}) );\n")
                continue

            # Check if OR
            if '|' in rhs_raw and not any(op in rhs_raw for op in ['&', '^', '?']):
                or_count += 1
                parts = rhs_raw.split('|')
                op0 = format_id(parts[0].strip())
                op1 = format_id(parts[1].strip())
                out_lines.append(f"  OR2x2_ASAP7_75t_R _legal_or_{or_count} ( .A({op0}), .B({op1}), .Y({lhs}) );\n")
                continue

            # Simple alias: assign lhs = rhs;
            rhs = format_id(rhs_raw)
            out_lines.append(f"  assign {lhs} = {rhs};\n")
            continue

        # Format escaped identifiers in gate cell connection lines
        # e.g. .Y(\escaped.name) -> .Y(\escaped.name )
        line = re.sub(r'(\\[^\s,;()\[\]]+)\)', r'\1 )', line)
        line = re.sub(r'(\\[^\s,;()\[\]]+);', r'\1 ;', line)
        line = re.sub(r'(\\[^\s,;()\[\]]+),', r'\1 ,', line)
        out_lines.append(line)

    print(f"Legalized {filepath}: dropped {dropped_count}, {inv_count} INV, {and_count} AND, {or_count} OR, {xor_count} XOR, {mux_count} MUX.")
    
    # Write output
    with open(filepath, 'w') as f:
        inserted = False
        for l in out_lines:
            f.write(l)
            if not inserted and l.startswith('module '):
                f.writelines(new_wires)
                inserted = True

if __name__ == '__main__':
    legalize_netlist(sys.argv[1])
