from pathlib import Path
import re


# Branches condicionais do 68000
CONDITIONAL_BRANCHES = {
    "BCC", "BCS",
    "BEQ", "BGE",
    "BGT", "BHI",
    "BLE", "BLT",
    "BLS", "BMI",
    "BNE", "BPL",
    "BVC", "BVS",
}


def parse_instruction(line):
    """
    Extrai endereço, opcode e operandos de uma linha
    do Assembly gerado pelo disassembler.
    """

    pattern = re.match(
        r"^([0-9A-Fa-f]+):\s+([A-Za-z.]+)(?:\s+(.*))?$",
        line.strip()
    )

    if not pattern:
        return None

    address = int(pattern.group(1), 16)
    opcode = pattern.group(2).upper()
    operands = pattern.group(3) or ""

    return {
        "address": address,
        "opcode": opcode,
        "operands": operands.strip(),
    }


def parse_target(operands):
    """
    Tenta encontrar um endereço hexadecimal dentro
    dos operandos de uma instrução.
    """

    match = re.search(
        r"\$([0-9A-Fa-f]+)",
        operands
    )

    if not match:
        return None

    return int(match.group(1), 16)


def analyze(asm_path, bin_path=None):
    """
    Analisa o Assembly 68000 gerado pelo disassembler.

    Retorna um dicionário contendo a representação
    inicial do programa para o codegen.
    """

    asm_path = Path(asm_path)

    print(f"Analisando: {asm_path}")

    text = asm_path.read_text(
        encoding="utf-8"
    )

    instructions = []
    functions = set()
    branches = []
    jumps = []

    # ==========================================
    # PARSE DAS INSTRUÇÕES
    # ==========================================

    for line in text.splitlines():

        instruction = parse_instruction(line)

        if instruction is None:
            continue

        instructions.append(instruction)

    # ==========================================
    # ANÁLISE DO FLUXO
    # ==========================================

    for instruction in instructions:

        opcode = instruction["opcode"]
        operands = instruction["operands"]

        target = parse_target(operands)

        # --------------------------------------
        # JSR
        # --------------------------------------

        if opcode == "JSR":

            if target is not None:
                functions.add(target)

        # --------------------------------------
        # BSR
        # --------------------------------------

        elif opcode == "BSR":

            if target is not None:
                functions.add(target)
                branches.append({
                    "source": instruction["address"],
                    "target": target,
                    "type": "CALL",
                })

        # --------------------------------------
        # JMP
        # --------------------------------------

        elif opcode == "JMP":

            if target is not None:
                jumps.append({
                    "source": instruction["address"],
                    "target": target,
                    "type": "JUMP",
                })

        # --------------------------------------
        # BRA
        # --------------------------------------

        elif opcode == "BRA":

            if target is not None:
                branches.append({
                    "source": instruction["address"],
                    "target": target,
                    "type": "BRANCH",
                })

        # --------------------------------------
        # Branches condicionais
        # --------------------------------------

        elif opcode in CONDITIONAL_BRANCHES:

            if target is not None:
                branches.append({
                    "source": instruction["address"],
                    "target": target,
                    "type": "CONDITIONAL",
                    "condition": opcode,
                })

    # ==========================================
    # DETECTAR POSSÍVEIS FUNÇÕES
    # ==========================================

    functions = sorted(functions)

    # ==========================================
    # RESULTADO
    # ==========================================

    analysis = {
        "asm_path": asm_path,
        "bin_path": Path(bin_path) if bin_path else None,
        "instructions": instructions,
        "functions": functions,
        "branches": branches,
        "jumps": jumps,
    }

    # ==========================================
    # RELATÓRIO
    # ==========================================

    print()
    print("Análise concluída.")
    print(f"Instruções: {len(instructions)}")
    print(f"Funções encontradas: {len(functions)}")
    print(f"Branches: {len(branches)}")
    print(f"Jumps: {len(jumps)}")

    return analysis