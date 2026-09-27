from pathlib import Path


# ============================================================
# MegaComp - Motorola 68000 Disassembler
# ============================================================
#
# Este módulo transforma palavras/opcodes 68000 em Assembly
# legível pelo Analyzer.
#
# O decoder é incremental: novas instruções podem ser
# adicionadas sem alterar o pipeline principal.
# ============================================================


CONDITIONS = {
    0x0: "T",
    0x1: "F",
    0x2: "HI",
    0x3: "LS",
    0x4: "CC",
    0x5: "CS",
    0x6: "NE",
    0x7: "EQ",
    0x8: "VC",
    0x9: "VS",
    0xA: "PL",
    0xB: "MI",
    0xC: "GE",
    0xD: "LT",
    0xE: "GT",
    0xF: "LE",
}


SIZE_NAMES = {
    0: "B",
    1: "W",
    2: "L",
}


def read_word(data, offset):
    """Lê uma word Motorola 68000 em big-endian."""

    if offset + 1 >= len(data):
        return None

    return int.from_bytes(
        data[offset:offset + 2],
        byteorder="big",
    )


def read_long(data, offset):
    """Lê um longword Motorola 68000 em big-endian."""

    if offset + 3 >= len(data):
        return None

    return int.from_bytes(
        data[offset:offset + 4],
        byteorder="big",
    )


def sign_extend(value, bits):
    """Converte um valor com sinal para Python."""

    mask = 1 << (bits - 1)

    if value & mask:
        value -= 1 << bits

    return value


def format_hex(value, digits=4):
    """Formata hexadecimal no padrão do MegaComp."""

    return f"${value & ((1 << (digits * 4)) - 1):0{digits}X}"


# ============================================================
# Effective Address
# ============================================================


def decode_ea(mode, reg, size, data, offset):
    """
    Decodifica um Effective Address do 68000.

    Retorna:

        texto
        número de bytes extras consumidos
    """

    # Dn
    if mode == 0:
        return f"D{reg}", 0

    # An
    if mode == 1:
        return f"A{reg}", 0

    # (An)
    if mode == 2:
        return f"(A{reg})", 0

    # (An)+
    if mode == 3:
        return f"(A{reg})+", 0

    # -(An)
    if mode == 4:
        return f"-(A{reg})", 0

    # d16(An)
    if mode == 5:
        value = read_word(data, offset)

        if value is None:
            return "???", 0

        value = sign_extend(value, 16)

        return f"{value:+d}(A{reg})", 2

    # d8(An, Xn)
    if mode == 6:
        value = read_word(data, offset)

        if value is None:
            return "???", 0

        value = sign_extend(value & 0xFF, 8)

        index_reg = (value >> 12) & 0x7

        return (
            f"{value:+d}(A{reg},D{index_reg})",
            2,
        )

    # Mode 7
    if mode == 7:

        # Absolute short
        if reg == 0:

            value = read_word(data, offset)

            if value is None:
                return "???", 0

            value = sign_extend(value, 16)

            return format_hex(value, 4), 2

        # Absolute long
        if reg == 1:

            value = read_long(data, offset)

            if value is None:
                return "???", 0

            return format_hex(value, 8), 4

        # Immediate
        if reg == 4:

            if size == "L":

                value = read_long(data, offset)

                if value is None:
                    return "#???", 0

                return f"#{format_hex(value, 8)}", 4

            value = read_word(data, offset)

            if value is None:
                return "#???", 0

            if size == "B":
                value &= 0xFF

            return f"#{format_hex(value, 4)}", 2

    return "???", 0


# ============================================================
# Decoder principal
# ============================================================


def decode_instruction(data, address):
    """
    Decodifica uma instrução 68000.

    Retorna:

        {
            "address": endereço,
            "size": tamanho em bytes,
            "opcode": mnemonic,
            "operands": operandos,
            "bytes": bytes consumidos
        }

    ou None se a instrução ainda não for suportada.
    """

    word = read_word(data, address)

    if word is None:
        return None

    # ========================================================
    # NOP
    # ========================================================

    if word == 0x4E71:
        return {
            "address": address,
            "size": 2,
            "opcode": "NOP",
            "operands": "",
            "bytes": data[address:address + 2],
        }

    # ========================================================
    # RTS
    # ========================================================

    if word == 0x4E75:
        return {
            "address": address,
            "size": 2,
            "opcode": "RTS",
            "operands": "",
            "bytes": data[address:address + 2],
        }

    # ========================================================
    # RTE
    # ========================================================

    if word == 0x4E73:
        return {
            "address": address,
            "size": 2,
            "opcode": "RTE",
            "operands": "",
            "bytes": data[address:address + 2],
        }

    # ========================================================
    # RTR
    # ========================================================

    if word == 0x4E77:
        return {
            "address": address,
            "size": 2,
            "opcode": "RTR",
            "operands": "",
            "bytes": data[address:address + 2],
        }

    # ========================================================
    # RESET
    # ========================================================

    if word == 0x4E70:
        return {
            "address": address,
            "size": 2,
            "opcode": "RESET",
            "operands": "",
            "bytes": data[address:address + 2],
        }

    # ========================================================
    # STOP
    # ========================================================

    if (word & 0xFFFF) == 0x4E72:

        value = read_word(data, address + 2)

        if value is not None:
            return {
                "address": address,
                "size": 4,
                "opcode": "STOP",
                "operands": f"#{format_hex(value)}",
                "bytes": data[address:address + 4],
            }

    # ========================================================
    # TRAP
    # ========================================================

    if (word & 0xFFF0) == 0x4E40:

        vector = word & 0xF

        return {
            "address": address,
            "size": 2,
            "opcode": "TRAP",
            "operands": f"#{vector}",
            "bytes": data[address:address + 2],
        }

    # ========================================================
    # LINK
    # ========================================================

    if (word & 0xFFF8) == 0x4E50:

        reg = word & 0x7

        displacement = read_word(data, address + 2)

        if displacement is not None:

            displacement = sign_extend(
                displacement,
                16,
            )

            return {
                "address": address,
                "size": 4,
                "opcode": "LINK",
                "operands": f"A{reg},#{displacement}",
                "bytes": data[address:address + 4],
            }

    # ========================================================
    # UNLK
    # ========================================================

    if (word & 0xFFF8) == 0x4E58:

        reg = word & 0x7

        return {
            "address": address,
            "size": 2,
            "opcode": "UNLK",
            "operands": f"A{reg}",
            "bytes": data[address:address + 2],
        }

    # ========================================================
    # JSR
    # ========================================================

    if (word & 0xFFC0) == 0x4E80:

        mode = (word >> 3) & 0x7
        reg = word & 0x7

        ea, extra = decode_ea(
            mode,
            reg,
            "L",
            data,
            address + 2,
        )

        return {
            "address": address,
            "size": 2 + extra,
            "opcode": "JSR",
            "operands": ea,
            "bytes": data[address:address + 2 + extra],
        }

    # ========================================================
    # JMP
    # ========================================================

    if (word & 0xFFC0) == 0x4EC0:

        mode = (word >> 3) & 0x7
        reg = word & 0x7

        ea, extra = decode_ea(
            mode,
            reg,
            "L",
            data,
            address + 2,
        )

        return {
            "address": address,
            "size": 2 + extra,
            "opcode": "JMP",
            "operands": ea,
            "bytes": data[address:address + 2 + extra],
        }

    # ========================================================
    # BRA / Bcc / BSR
    # ========================================================

    if (word & 0xF000) == 0x6000:

        condition = (word >> 8) & 0xF
        displacement = word & 0xFF

        if displacement == 0:

            extension = read_word(
                data,
                address + 2,
            )

            if extension is None:
                return None

            displacement = sign_extend(
                extension,
                16,
            )

            instruction_size = 4

        else:

            displacement = sign_extend(
                displacement,
                8,
            )

            instruction_size = 2

        target = address + instruction_size + displacement

        condition_name = CONDITIONS[condition]

        if condition == 0:
            mnemonic = "BRA"

        elif condition == 1:
            mnemonic = "BSR"

        else:
            mnemonic = f"B{condition_name}"

        return {
            "address": address,
            "size": instruction_size,
            "opcode": mnemonic,
            "operands": format_hex(target, 6),
            "target": target,
            "bytes": data[address:address + instruction_size],
        }

    # ========================================================
    # MOVEQ
    # ========================================================

    if (word & 0xF100) == 0x7000:

        register = (word >> 9) & 0x7
        value = word & 0xFF

        value = sign_extend(value, 8)

        return {
            "address": address,
            "size": 2,
            "opcode": "MOVEQ",
            "operands": f"#{value},D{register}",
            "bytes": data[address:address + 2],
        }

    # ========================================================
    # MOVE
    # ========================================================

    move_top = word & 0xC000

    if move_top in (0x0000, 0x4000, 0x8000):

        size_code = (word >> 12) & 0x3

        if size_code in (1, 2, 3):

            if size_code == 1:
                size = "B"
            elif size_code == 2:
                size = "L"
            else:
                size = "W"

            destination_reg = (word >> 9) & 0x7
            destination_mode = (word >> 6) & 0x7
            source_mode = (word >> 3) & 0x7
            source_reg = word & 0x7

            source, source_extra = decode_ea(
                source_mode,
                source_reg,
                size,
                data,
                address + 2,
            )

            destination, destination_extra = decode_ea(
                destination_mode,
                destination_reg,
                size,
                data,
                address + 2 + source_extra,
            )

            total_size = (
                2
                + source_extra
                + destination_extra
            )

            return {
                "address": address,
                "size": total_size,
                "opcode": f"MOVE.{size}",
                "operands": f"{source},{destination}",
                "bytes": data[address:address + total_size],
            }

    # ========================================================
    # ADDQ / SUBQ
    # ========================================================

    if (word & 0xF000) in (0x5000,):

        operation = "SUBQ" if (word & 0x0100) else "ADDQ"

        value = (word >> 9) & 0x7

        if value == 0:
            value = 8

        size_code = (word >> 6) & 0x3

        if size_code in SIZE_NAMES:

            size = SIZE_NAMES[size_code]

            mode = (word >> 3) & 0x7
            reg = word & 0x7

            ea, extra = decode_ea(
                mode,
                reg,
                size,
                data,
                address + 2,
            )

            return {
                "address": address,
                "size": 2 + extra,
                "opcode": f"{operation}.{size}",
                "operands": f"#{value},{ea}",
                "bytes": data[address:address + 2 + extra],
            }

    # ========================================================
    # TST
    # ========================================================

    if (word & 0xFF00) == 0x4A00:

        size_code = (word >> 6) & 0x3

        if size_code in SIZE_NAMES:

            size = SIZE_NAMES[size_code]

            mode = (word >> 3) & 0x7
            reg = word & 0x7

            ea, extra = decode_ea(
                mode,
                reg,
                size,
                data,
                address + 2,
            )

            return {
                "address": address,
                "size": 2 + extra,
                "opcode": f"TST.{size}",
                "operands": ea,
                "bytes": data[address:address + 2 + extra],
            }

    # ========================================================
    # CLR
    # ========================================================

    if (word & 0xFF00) == 0x4200:

        size_code = (word >> 6) & 0x3

        if size_code in SIZE_NAMES:

            size = SIZE_NAMES[size_code]

            mode = (word >> 3) & 0x7
            reg = word & 0x7

            ea, extra = decode_ea(
                mode,
                reg,
                size,
                data,
                address + 2,
            )

            return {
                "address": address,
                "size": 2 + extra,
                "opcode": f"CLR.{size}",
                "operands": ea,
                "bytes": data[address:address + 2 + extra],
            }

    # ========================================================
    # Unknown opcode
    # ========================================================

    return {
        "address": address,
        "size": 2,
        "opcode": "DC.W",
        "operands": format_hex(word),
        "bytes": data[address:address + 2],
    }


# ============================================================
# Disassemble
# ============================================================


def disassemble(bin_path, project_dir):

    bin_path = Path(bin_path)
    project_dir = Path(project_dir)

    output_path = (
        project_dir /
        f"{bin_path.stem}_68000.asm"
    )

    data = bin_path.read_bytes()

    print(f"Disassemblando: {bin_path}")
    print(f"Tamanho: {len(data):,} bytes")

    lines = []

    # ========================================================
    # HEADER
    # ========================================================

    lines.append("; ========================================")
    lines.append("; MegaComp - Motorola 68000 Disassembly")
    lines.append("; ========================================")
    lines.append(f"; ROM: {bin_path.name}")
    lines.append(f"; Tamanho: {len(data):,} bytes")
    lines.append(";")
    lines.append("; Gerado pelo MegaComp")
    lines.append("; ========================================")
    lines.append("")

    # ========================================================
    # INITIAL VECTORS
    # ========================================================

    initial_pc = 0

    if len(data) >= 8:

        initial_sp = read_long(data, 0)
        initial_pc = read_long(data, 4)

        lines.append("; ----------------------------------------")
        lines.append("; Vetores iniciais")
        lines.append("; ----------------------------------------")

        lines.append(
            f"Initial_SP: dc.l ${initial_sp:08X}"
        )

        lines.append(
            f"Initial_PC: dc.l ${initial_pc:08X}"
        )

        lines.append("")

    # ========================================================
    # CODE
    # ========================================================

    lines.append("; ----------------------------------------")
    lines.append("; Código")
    lines.append("; ----------------------------------------")
    lines.append("")

    address = 0

    instruction_count = 0

    while address < len(data):

        instruction = decode_instruction(
            data,
            address,
        )

        if instruction is None:
            break

        opcode = instruction["opcode"]
        operands = instruction["operands"]

        lines.append(
            f"{address:06X}: "
            f"{opcode}"
            f"{(' ' + operands) if operands else ''}"
        )

        address += instruction["size"]

        instruction_count += 1

    # ========================================================
    # SAVE
    # ========================================================

    output_path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    print(
        f"Assembly criado: {output_path}"
    )

    print(
        f"Instruções decodificadas: "
        f"{instruction_count:,}"
    )

    return output_path