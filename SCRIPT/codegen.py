from pathlib import Path
import re


CONDITIONAL_BRANCHES = {
    "BCC", "BCS", "BEQ", "BGE", "BGT", "BHI",
    "BLE", "BLT", "BLS", "BMI", "BNE", "BPL",
    "BVC", "BVS",
}

BCC_TO_JCC = {
    "BEQ": "je",  "BNE": "jne",
    "BCS": "jb",  "BCC": "jae",
    "BMI": "js",  "BPL": "jns",
    "BVS": "jo",  "BVC": "jno",
    "BLT": "jl",  "BGE": "jge",
    "BLE": "jle", "BGT": "jg",
    "BHI": "ja",  "BLS": "jbe",
}

DATA_OPCODES = {"DC.W", "DC.B", "DC.L"}

SIZE_TO_RD = {"B": "byte", "W": "word", "L": "long"}
SIZE_TO_SHIFT = {"B": 24, "W": 16, "L": 0}


def _split(operands):
    parts, depth, cur = [], 0, ""
    for ch in operands:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur.strip())
    return parts


def _parse_imm(s):
    s = s.strip()
    if s.startswith("#"):
        s = s[1:]
    if s.startswith("$"):
        return int(s[1:], 16)
    return int(s)


def _target(operands):
    m = re.search(r"\$([0-9A-Fa-f]+)", operands)
    if not m:
        return None
    v = int(m.group(1), 16)
    return v if 0 <= v <= 0xFFFFFF else None


def _mask_for(size):
    return {"B": 0xFF, "W": 0xFFFF, "L": 0xFFFFFFFF}[size]


def _read_fn(size):
    return {"B": "read_byte", "W": "read_word", "L": "read_long"}[size]


def _write_fn(size):
    return {"B": "write_byte", "W": "write_word", "L": "write_long"}[size]


# ============================================================
# Emissão de EA (load / store)
# ============================================================

def emit_load_ea(ea, size):
    """Carrega EA em eax, retorna lista de linhas."""
    ea = ea.strip()
    read = _read_fn(size)

    if ea.startswith("#"):
        imm = _parse_imm(ea)
        return [f"    mov eax, {imm}"]

    if re.match(r"^D[0-7]$", ea):
        return [f"    mov eax, [reg_{ea}]"]

    if re.match(r"^A[0-7]$", ea):
        return [f"    mov eax, [reg_{ea}]"]

    if re.match(r"^\$[0-9A-Fa-f]+$", ea):
        addr = int(ea[1:], 16)
        return [f"    mov ecx, {addr}", f"    call {read}"]

    m = re.match(r"^\(A([0-7])\)$", ea)
    if m:
        return [
            f"    mov ecx, [reg_A{m.group(1)}]",
            f"    call {read}",
        ]

    m = re.match(r"^\(A([0-7])\)\+$", ea)
    if m:
        inc = {"B": 1, "W": 2, "L": 4}[size]
        return [
            f"    mov ecx, [reg_A{m.group(1)}]",
            f"    call {read}",
            f"    add dword ptr [reg_A{m.group(1)}], {inc}",
        ]

    m = re.match(r"^-\(A([0-7])\)$", ea)
    if m:
        dec = {"B": 1, "W": 2, "L": 4}[size]
        return [
            f"    sub dword ptr [reg_A{m.group(1)}], {dec}",
            f"    mov ecx, [reg_A{m.group(1)}]",
            f"    call {read}",
        ]

    # d16(An), d8(An,Xn)
    m = re.match(
        r"^([+-]?\d+)\(A([0-7])(?:,([DA])([0-7])(\.W|\.L)?)?\)$",
        ea,
    )
    if m:
        disp = int(m.group(1))
        an = m.group(2)
        idx_t, idx_r, idx_sz = m.group(3), m.group(4), (m.group(5) or ".W")
        lines = [f"    mov ecx, [reg_A{an}]"]
        if disp:
            op = "add" if disp > 0 else "sub"
            lines.append(f"    {op} ecx, {abs(disp)}")
        if idx_t:
            lines.append(f"    mov edx, [reg_{idx_t}{idx_r}]")
            if idx_sz == ".W":
                lines.append("    movsx edx, dx")
            lines.append("    add ecx, edx")
        lines.append(f"    call {read}")
        return lines

    return [f"    ; TODO load EA: {ea}"]


def emit_store_ea(ea, size):
    """Grava eax no EA, retorna lista de linhas."""
    ea = ea.strip()
    write = _write_fn(size)

    if re.match(r"^D[0-7]$", ea):
        if size == "L":
            return [f"    mov [reg_{ea}], eax"]
        mask = _mask_for(size)
        inv = (~mask) & 0xFFFFFFFF
        return [
            f"    and eax, {mask}",
            f"    mov edx, [reg_{ea}]",
            f"    and edx, {inv}",
            f"    or eax, edx",
            f"    mov [reg_{ea}], eax",
        ]

    if re.match(r"^A[0-7]$", ea):
        return [f"    mov [reg_{ea}], eax"]

    if re.match(r"^\$[0-9A-Fa-f]+$", ea):
        addr = int(ea[1:], 16)
        return [
            f"    mov ecx, {addr}",
            f"    mov edx, eax",
            f"    call {write}",
        ]

    m = re.match(r"^\(A([0-7])\)$", ea)
    if m:
        return [
            f"    mov ecx, [reg_A{m.group(1)}]",
            f"    mov edx, eax",
            f"    call {write}",
        ]

    m = re.match(r"^\(A([0-7])\)\+$", ea)
    if m:
        inc = {"B": 1, "W": 2, "L": 4}[size]
        return [
            f"    mov ecx, [reg_A{m.group(1)}]",
            f"    mov edx, eax",
            f"    call {write}",
            f"    add dword ptr [reg_A{m.group(1)}], {inc}",
        ]

    m = re.match(r"^-\(A([0-7])\)$", ea)
    if m:
        dec = {"B": 1, "W": 2, "L": 4}[size]
        return [
            f"    sub dword ptr [reg_A{m.group(1)}], {dec}",
            f"    mov ecx, [reg_A{m.group(1)}]",
            f"    mov edx, eax",
            f"    call {write}",
        ]

    m = re.match(
        r"^([+-]?\d+)\(A([0-7])(?:,([DA])([0-7])(\.W|\.L)?)?\)$",
        ea,
    )
    if m:
        disp = int(m.group(1))
        an = m.group(2)
        idx_t, idx_r, idx_sz = m.group(3), m.group(4), (m.group(5) or ".W")
        lines = [f"    mov ecx, [reg_A{an}]"]
        if disp:
            op = "add" if disp > 0 else "sub"
            lines.append(f"    {op} ecx, {abs(disp)}")
        if idx_t:
            lines.append(f"    mov edx, [reg_{idx_t}{idx_r}]")
            if idx_sz == ".W":
                lines.append("    movsx edx, dx")
            lines.append("    add ecx, edx")
        lines.append("    mov edx, eax")
        lines.append(f"    call {write}")
        return lines

    return [f"    ; TODO store EA: {ea}"]


# ============================================================
# Emissão de instrução
# ============================================================

def emit_instruction(insn, labels):
    op = insn["opcode"]
    ops = insn["operands"]
    addr = insn["address"]
    lines = [f"    ; 68000: {addr:06X}: {op} {ops}"]

    if addr in labels:
        lines.insert(0, f"{labels[addr]}:")

    # --- NOP ---
    if op == "NOP":
        lines.append("    nop")
        return lines

    # --- RTS / RTE / RTR ---
    if op in ("RTS", "RTE", "RTR"):
        lines.append("    ret")
        return lines

    # --- MOVEQ ---
    if op == "MOVEQ":
        parts = _split(ops)
        if len(parts) == 2:
            imm = _parse_imm(parts[0])
            dst = parts[1]
            lines.append(f"    mov eax, {imm & 0xFFFFFFFF}")
            lines.append(f"    mov [reg_{dst}], eax")
            lines.append(f"    call build_flags_move")
        return lines

    # --- MOVE / MOVEA ---
    if op.startswith("MOVE"):
        size = op.split(".")[-1] if "." in op else "W"
        parts = _split(ops)
        if len(parts) == 2:
            src, dst = parts
            lines += emit_load_ea(src, size)
            lines.append(f"    and eax, {_mask_for(size)}")
            # Salva valor mascarado para flags antes do store
            lines.append("    mov r9d, eax")
            lines += emit_store_ea(dst, size)
            lines.append("    mov eax, r9d")
            if not op.startswith("MOVEA"):
                lines.append("    call build_flags_move")
        return lines

    # --- LEA ---
    if op == "LEA":
        parts = _split(ops)
        if len(parts) == 2:
            src, dst = parts
            # LEA carrega o endereço efetivo
            if src.startswith("$"):
                a = int(src[1:], 16)
                lines.append(f"    mov eax, {a}")
            else:
                m = re.match(r"^([+-]?\d+)\(A([0-7])(?:,([DA])([0-7])(\.W|\.L)?)?\)$", src)
                if m:
                    disp = int(m.group(1))
                    an = m.group(2)
                    lines.append(f"    mov eax, [reg_A{an}]")
                    if disp:
                        o = "add" if disp > 0 else "sub"
                        lines.append(f"    {o} eax, {abs(disp)}")
                    if m.group(3):
                        lines.append(f"    mov edx, [reg_{m.group(3)}{m.group(4)}]")
                        if (m.group(5) or ".W") == ".W":
                            lines.append("    movsx edx, dx")
                        lines.append("    add eax, edx")
            lines.append(f"    mov [reg_{dst}], eax")
        return lines

    # --- ADD / SUB / AND / OR / CMP ---
    base = op.split(".")[0]
    if base in ("ADD", "SUB", "AND", "OR", "CMP", "ADDA", "SUBA", "CMPA"):
        parts = _split(ops)
        size = op.split(".")[-1] if "." in op else "W"
        if len(parts) == 2:
            src, dst = parts
            lines += emit_load_ea(src, size)
            lines.append(f"    and eax, {_mask_for(size)}")
            lines.append("    mov edi, eax")           # B (source)
            lines.append(f"    mov esi, [reg_{dst}]") if dst.startswith(("D", "A")) else None
            if dst.startswith(("D", "A")):
                lines.append(f"    and esi, {_mask_for(size)}")
                lines.append("    mov eax, esi")
                arith = {
                    "ADD": "add", "ADDA": "add",
                    "SUB": "sub", "SUBA": "sub",
                    "AND": "and", "OR": "or",
                    "CMP": "cmp", "CMPA": "cmp",
                }[base]
                lines.append(f"    {arith} eax, edi")
                lines.append(f"    and eax, {_mask_for(size)}")
                if base not in ("CMP", "CMPA"):
                    # Preserva upper bits do dst
                    lines.append("    mov r9d, eax")
                    lines += emit_store_ea(dst, size)
                    lines.append("    mov eax, r9d")
                lines.append(f"    mov r8b, '{size}'")
                if base in ("AND", "OR"):
                    lines.append("    call build_flags_logic")
                elif base == "SUB" or base == "SUBA":
                    lines.append("    call build_flags_sub")
                else:
                    lines.append("    call build_flags_add")
            else:
                lines.append(f"    ; TODO {base} com dst memória: {dst}")
        return lines

    # --- ADDQ / SUBQ ---
    if base in ("ADDQ", "SUBQ"):
        parts = _split(ops)
        size = op.split(".")[-1]
        if len(parts) == 2:
            imm = _parse_imm(parts[0])
            dst = parts[1]
            lines.append(f"    mov edi, {imm}")
            if dst.startswith(("D", "A")):
                lines.append(f"    mov esi, [reg_{dst}]")
                lines.append(f"    and esi, {_mask_for(size)}")
                lines.append("    mov eax, esi")
                arith = "add" if base == "ADDQ" else "sub"
                lines.append(f"    {arith} eax, edi")
                lines.append(f"    and eax, {_mask_for(size)}")
                lines.append("    mov r9d, eax")
                lines += emit_store_ea(dst, size)
                lines.append("    mov eax, r9d")
                lines.append(f"    mov r8b, '{size}'")
                if base == "ADDQ":
                    lines.append("    call build_flags_add")
                else:
                    lines.append("    call build_flags_sub")
        return lines

    # --- TST ---
    if op.startswith("TST"):
        size = op.split(".")[-1]
        lines += emit_load_ea(ops, size)
        lines.append(f"    and eax, {_mask_for(size)}")
        lines.append("    test eax, eax")
        lines.append(f"    mov r8b, '{size}'")
        lines.append("    mov esi, 0")
        lines.append("    mov edi, 0")
        lines.append("    call build_flags_sub")
        return lines

    # --- CLR ---
    if op.startswith("CLR"):
        size = op.split(".")[-1]
        lines.append("    xor eax, eax")
        lines += emit_store_ea(ops, size)
        lines.append("    call build_flags_clr")
        return lines

    # --- EXT.W / EXT.L ---
    if op == "EXT.W":
        dst = ops.strip()
        lines.append(f"    movsx eax, byte ptr [reg_{dst}]")
        lines.append(f"    mov [reg_{dst}], eax")
        lines.append("    call build_flags_move")
        return lines
    if op == "EXT.L":
        dst = ops.strip()
        lines.append(f"    movsx eax, word ptr [reg_{dst}]")
        lines.append(f"    mov [reg_{dst}], eax")
        lines.append("    call build_flags_move")
        return lines

    # --- SWAP ---
    if op == "SWAP":
        dst = ops.strip()
        lines.append(f"    mov eax, [reg_{dst}]")
        lines.append("    rol eax, 16")
        lines.append(f"    mov [reg_{dst}], eax")
        lines.append("    call build_flags_move")
        return lines

    # --- LINK ---
    if op == "LINK":
        parts = _split(ops)
        if len(parts) == 2:
            an = parts[0].strip()
            disp = _parse_imm(parts[1])
            lines.append("    sub dword ptr [reg_A7], 4")
            lines.append("    mov ecx, [reg_A7]")
            lines.append(f"    mov edx, [reg_{an}]")
            lines.append("    call write_long")
            lines.append("    mov eax, [reg_A7]")
            lines.append(f"    mov [reg_{an}], eax")
            if disp:
                o = "add" if disp > 0 else "sub"
                lines.append(f"    {o} dword ptr [reg_A7], {abs(disp)}")
        return lines

    # --- UNLK ---
    if op == "UNLK":
        an = ops.strip()
        lines.append(f"    mov eax, [reg_{an}]")
        lines.append("    mov [reg_A7], eax")
        lines.append("    mov ecx, eax")
        lines.append("    call read_long")
        lines.append(f"    mov [reg_{an}], eax")
        lines.append("    add dword ptr [reg_A7], 4")
        return lines

    # --- PEA ---
    if op == "PEA":
        src = ops.strip()
        # Calcula endereço efetivo (não valor)
        if src.startswith("$"):
            a = int(src[1:], 16)
            lines.append(f"    mov edx, {a}")
        else:
            m = re.match(r"^([+-]?\d+)\(A([0-7])\)$", src)
            if m:
                disp = int(m.group(1))
                lines.append(f"    mov edx, [reg_A{m.group(2)}]")
                if disp:
                    o = "add" if disp > 0 else "sub"
                    lines.append(f"    {o} edx, {abs(disp)}")
        lines.append("    call push_long_68k")
        return lines

    # --- BRA ---
    if op == "BRA":
        t = _target(ops)
        if t is not None and t in labels:
            lines.append(f"    jmp {labels[t]}")
        return lines

    # --- Bcc ---
    if op in CONDITIONAL_BRANCHES:
        t = _target(ops)
        if t is not None and t in labels:
            jcc = BCC_TO_JCC[op]
            lines.append(f"    {jcc} {labels[t]}")
        return lines

    # --- JSR / BSR ---
    if op in ("JSR", "BSR"):
        t = _target(ops)
        if t is not None:
            lines.append(f"    call function_{t:06X}")
        else:
            lines.append(f"    ; TODO JSR indireto: {ops}")
        return lines

    # --- JMP ---
    if op == "JMP":
        t = _target(ops)
        if t is not None and t in labels:
            lines.append(f"    jmp {labels[t]}")
        else:
            lines.append(f"    ; TODO JMP indireto: {ops}")
        return lines

    # --- MOVEM (formato simples: registrador list) ---
    if op.startswith("MOVEM"):
        lines.append(f"    ; TODO MOVEM: {ops}")
        return lines

    if op in DATA_OPCODES:
        lines.append(f"    ; {op} {ops}")
        return lines

    lines.append(f"    ; TODO: {op} {ops}")
    return lines


# ============================================================
# Entry point e ROM
# ============================================================

def _emit_rom_data(lines, bin_path):
    data = Path(bin_path).read_bytes()
    lines.append("public rom_data")
    lines.append("public rom_size")
    lines.append("rom_data:")
    for i in range(0, len(data), 16):
        chunk = data[i:i + 16]
        hexs = ", ".join(f"{b:02X}h" for b in chunk)
        lines.append(f"    db {hexs}")
    lines.append(f"rom_size dq {len(data)}")
    lines.append("")


def generate(analysis, project_dir, embed_rom=True):
    project_dir = Path(project_dir)
    asm_path = Path(analysis["asm_path"])
    bin_path = analysis.get("bin_path")
    name = asm_path.stem.replace("_68000", "")
    output_path = project_dir / f"{name}_win.asm"

    instructions_by_addr = analysis["instructions_by_addr"]
    sorted_addrs = analysis["sorted_addrs"]
    functions = set(analysis["functions"])
    labels = analysis.get("labels", {})

    lines = []
    lines.append("; ============================================")
    lines.append("; MegaComp - x86-64 / MASM")
    lines.append("; ============================================")
    lines.append(f"; Source: {asm_path.name}")
    lines.append("; ============================================")
    lines.append("")
    lines.append("include runtime.inc")
    lines.append("")

    if embed_rom and bin_path:
        lines.append(".data")
        lines.append("")
        _emit_rom_data(lines, bin_path)

    lines.append(".code")
    lines.append("")

    function_starts = sorted(functions)
    if not function_starts and sorted_addrs:
        function_starts = [sorted_addrs[0]]

    for idx, start in enumerate(function_starts):
        end = function_starts[idx + 1] if idx + 1 < len(function_starts) else None

        lines.append(f"; função ${start:06X}")
        lines.append(f"public function_{start:06X}")
        lines.append(f"function_{start:06X} PROC")

        addr = start
        visited = set()
        while addr in instructions_by_addr and addr not in visited:
            visited.add(addr)
            if end is not None and addr >= end:
                break
            insn = instructions_by_addr[addr]
            lines += emit_instruction(insn, labels)
            lines.append("")
            addr += insn["size"]

        lines.append(f"function_{start:06X} ENDP")
        lines.append("")

    # Entry point
    lines.append("; ============================================")
    lines.append("; Entry point")
    lines.append("; ============================================")
    lines.append("public MegaComp_Main")
    lines.append("MegaComp_Main PROC")
    lines.append("    mov dword ptr [reg_A7], 00FFFE00h")
    if functions:
        entry = functions[0]
        lines.append(f"    call function_{entry:06X}")
    lines.append("    ret")
    lines.append("MegaComp_Main ENDP")
    lines.append("")
    lines.append("END")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"MASM: {output_path}")
    return output_path