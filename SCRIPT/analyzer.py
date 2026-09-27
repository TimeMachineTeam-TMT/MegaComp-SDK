from pathlib import Path
import re


CONDITIONAL_BRANCHES = {
    "BCC", "BCS", "BEQ", "BGE", "BGT", "BHI",
    "BLE", "BLT", "BLS", "BMI", "BNE", "BPL",
    "BVC", "BVS",
}

TERMINATORS = {"RTS", "RTE", "RTR", "JMP", "BRA"}

CALL_OPCODES = {"JSR", "BSR"}

DATA_OPCODES = {"DC.W", "DC.B", "DC.L", "DS.W", "DS.B", "DS.L", "INCBIN"}


# ============================================================
# Limites de tamanho por opcode (bytes)
# ============================================================
# Usado para truncar o size quando o próximo endereço está
# longe (caso típico: RTS seguido de dados ou nova função).

MAX_INSN_SIZE = {
    # 2 bytes
    "NOP": 2, "RTS": 2, "RTE": 2, "RTR": 2, "RESET": 2,
    "TRAPV": 2, "ILLEGAL": 2, "TRAP": 2, "SWAP": 2,
    "EXT.W": 2, "EXT.L": 2, "UNLK": 2, "MOVEQ": 2,
    # 4 bytes
    "LINK": 4, "STOP": 4,
    "BRA": 4, "BSR": 4,
    # branches condicionais curtos (2) ou longos (6)
    "BEQ": 6, "BNE": 6, "BCS": 6, "BCC": 6,
    "BMI": 6, "BPL": 6, "BVS": 6, "BVC": 6,
    "BLT": 6, "BGE": 6, "BLE": 6, "BGT": 6,
    "BHI": 6, "BLS": 6,
    # DBcc
    "DBEQ": 4, "DBNE": 4, "DBCS": 4, "DBCC": 4,
    "DBMI": 4, "DBPL": 4, "DBVS": 4, "DBVC": 4,
    "DBLT": 4, "DBGE": 4, "DBLE": 4, "DBGT": 4,
    "DBHI": 4, "DBLS": 4, "DBT": 4, "DBF": 4,
}


def parse_line(line):
    s = line.strip()
    if not s or s.startswith(";"):
        return None

    m = re.match(
        r"^([0-9A-Fa-f]+):\s+([A-Za-z][A-Za-z0-9.]*)(?:\s+(.*))?$",
        s,
    )
    if not m:
        return None

    return {
        "address": int(m.group(1), 16),
        "opcode": m.group(2).upper(),
        "operands": (m.group(3) or "").strip(),
    }


def parse_target(operands):
    if not operands:
        return None

    m = re.search(r"\$([0-9A-Fa-f]+)", operands)
    if not m:
        return None

    value = int(m.group(1), 16)
    if 0 <= value <= 0xFFFFFF:
        return value
    return None


def analyze(asm_path, bin_path=None):
    asm_path = Path(asm_path)
    print(f"Analisando: {asm_path}")

    text = asm_path.read_text(encoding="utf-8")

    # ==========================================================
    # PARSE: separa instruções de dados
    # ==========================================================

    instructions_by_addr = {}
    data_regions = []
    current_data_start = None
    initial_pc = None

    for line in text.splitlines():
        s = line.strip()

        m_pc = re.match(r"^Initial_PC:\s+dc\.l\s+\$([0-9A-Fa-f]+)", s)
        if m_pc:
            initial_pc = int(m_pc.group(1), 16)
            continue

        parsed = parse_line(line)
        if parsed is None:
            continue

        if parsed["opcode"] in DATA_OPCODES:
            if current_data_start is None:
                current_data_start = parsed["address"]
            continue

        if current_data_start is not None:
            data_regions.append((current_data_start, parsed["address"]))
            current_data_start = None

        instructions_by_addr[parsed["address"]] = parsed

    if current_data_start is not None:
        end = (
            max(instructions_by_addr) + 4
            if instructions_by_addr
            else current_data_start
        )
        data_regions.append((current_data_start, end))

    sorted_addrs = sorted(instructions_by_addr.keys())

    # ==========================================================
    # CALCULAR SIZE DE CADA INSTRUÇÃO
    # ==========================================================

    for i, addr in enumerate(sorted_addrs):
        insn = instructions_by_addr[addr]

        if i + 1 < len(sorted_addrs):
            next_addr = sorted_addrs[i + 1]
        else:
            next_addr = None
            for dstart, _ in data_regions:
                if dstart > addr:
                    next_addr = dstart
                    break
            if next_addr is None:
                next_addr = addr + 2

        raw_size = next_addr - addr

        max_size = MAX_INSN_SIZE.get(insn["opcode"])
        if max_size is not None and raw_size > max_size:
            raw_size = max_size
        elif raw_size > 12:
            raw_size = 2

        insn["size"] = raw_size

    # ==========================================================
    # IDENTIFICAR FUNÇÕES
    # ==========================================================

    function_entries = set()

    if initial_pc is not None:
        function_entries.add(initial_pc)

    if sorted_addrs:
        function_entries.add(sorted_addrs[0])

    for _, region_end in data_regions:
        if region_end in instructions_by_addr:
            function_entries.add(region_end)

    for addr in sorted_addrs:
        insn = instructions_by_addr[addr]
        if insn["opcode"] in CALL_OPCODES:
            target = parse_target(insn["operands"])
            if target is not None and target in instructions_by_addr:
                function_entries.add(target)

    for i, addr in enumerate(sorted_addrs[:-1]):
        if instructions_by_addr[addr]["opcode"] in TERMINATORS:
            next_addr = sorted_addrs[i + 1]
            function_entries.add(next_addr)

    for addr in sorted_addrs:
        insn = instructions_by_addr[addr]
        if insn["opcode"] == "JMP":
            target = parse_target(insn["operands"])
            if target is not None and target in instructions_by_addr:
                function_entries.add(target)

    functions = sorted(function_entries)

    # ==========================================================
    # BRANCHES E JUMPS
    # ==========================================================

    branches = []
    jumps = []

    for addr in sorted_addrs:
        insn = instructions_by_addr[addr]
        opcode = insn["opcode"]

        if opcode in CALL_OPCODES:
            target = parse_target(insn["operands"])
            if target is not None:
                branches.append({
                    "source": addr, "target": target,
                    "type": "CALL", "opcode": opcode,
                })

        elif opcode == "JMP":
            target = parse_target(insn["operands"])
            if target is not None:
                jumps.append({
                    "source": addr, "target": target,
                    "type": "JUMP", "opcode": opcode,
                })

        elif opcode == "BRA":
            target = parse_target(insn["operands"])
            if target is not None:
                branches.append({
                    "source": addr, "target": target,
                    "type": "BRANCH", "opcode": opcode,
                })

        elif opcode in CONDITIONAL_BRANCHES:
            target = parse_target(insn["operands"])
            if target is not None:
                branches.append({
                    "source": addr, "target": target,
                    "type": "CONDITIONAL", "opcode": opcode,
                    "condition": opcode[1:],
                })

    # ==========================================================
    # LABELS
    # ==========================================================

    label_targets = set(function_entries)
    for b in branches:
        label_targets.add(b["target"])
    for j in jumps:
        label_targets.add(j["target"])

    labels = {t: f"loc_{t:06X}" for t in sorted(label_targets)}
    for fn in functions:
        labels[fn] = f"func_{fn:06X}"

    # ==========================================================
    # RESULTADO
    # ==========================================================

    instructions = [instructions_by_addr[a] for a in sorted_addrs]

    analysis = {
        "asm_path": asm_path,
        "bin_path": Path(bin_path) if bin_path else None,
        "instructions": instructions,
        "instructions_by_addr": instructions_by_addr,
        "sorted_addrs": sorted_addrs,
        "data_regions": data_regions,
        "functions": functions,
        "branches": branches,
        "jumps": jumps,
        "labels": labels,
    }

    print()
    print("Análise concluída.")
    print(f"Instruções: {len(instructions)}")
    print(f"Regiões de dados: {len(data_regions)}")
    print(f"Funções: {len(functions)}")
    print(f"Branches: {len(branches)}")
    print(f"Jumps: {len(jumps)}")
    print(f"Labels: {len(labels)}")

    return analysis