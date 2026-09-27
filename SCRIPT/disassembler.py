from pathlib import Path


# ============================================================
# MegaComp - Motorola 68000 Disassembler (rev 2)
# ============================================================
#
# Correções em relação à rev 1:
#   - decode_ea modo 6 (indexed) corrigido
#   - suporte a PC-relative (modo 7.2, 7.3)
#   - tabela de opcodes em vez de if-else
#   - recursive descent (só decodifica código alcançável)
#   - separação código/dados na saída
# ============================================================


CONDITIONS = {
    0x0: "T",  0x1: "F",  0x2: "HI", 0x3: "LS",
    0x4: "CC", 0x5: "CS", 0x6: "NE", 0x7: "EQ",
    0x8: "VC", 0x9: "VS", 0xA: "PL", 0xB: "MI",
    0xC: "GE", 0xD: "LT", 0xE: "GT", 0xF: "LE",
}

SIZE_NAMES = {0: "B", 1: "W", 2: "L"}


def read_word(data, offset):
    if offset < 0 or offset + 1 >= len(data):
        return None
    return int.from_bytes(data[offset:offset + 2], byteorder="big")


def read_long(data, offset):
    if offset < 0 or offset + 3 >= len(data):
        return None
    return int.from_bytes(data[offset:offset + 4], byteorder="big")


def sign_extend(value, bits):
    mask = 1 << (bits - 1)
    if value & mask:
        value -= 1 << bits
    return value


def format_hex(value, digits=4):
    mask = (1 << (digits * 4)) - 1
    return f"${value & mask:0{digits}X}"


# ============================================================
# Effective Address
# ============================================================


def decode_ea(mode, reg, size, data, offset, pc_base=None):
    """
    Decodifica um Effective Address do 68000.

    pc_base: endereço da word de extensão (base para modos PC-relativos).
             Se None, mostra o deslocamento cru.

    Retorna: (texto, bytes_extras)
    """

    if mode == 0:
        return f"D{reg}", 0
    if mode == 1:
        return f"A{reg}", 0
    if mode == 2:
        return f"(A{reg})", 0
    if mode == 3:
        return f"(A{reg})+", 0
    if mode == 4:
        return f"-(A{reg})", 0

    if mode == 5:
        value = read_word(data, offset)
        if value is None:
            return "???", 0
        return f"{sign_extend(value, 16):+d}(A{reg})", 2

    if mode == 6:
        value = read_word(data, offset)
        if value is None:
            return "???", 0
        # IMPORTANTE: extrair campos ANTES do sign_extend do displacement.
        disp = sign_extend(value & 0xFF, 8)
        idx_is_an = (value >> 15) & 1
        idx_reg = (value >> 12) & 0x7
        idx_size = (value >> 11) & 1
        idx_prefix = "A" if idx_is_an else "D"
        idx_suffix = ".L" if idx_size else ".W"
        return f"{disp:+d}(A{reg},{idx_prefix}{idx_reg}{idx_suffix})", 2

    if mode == 7:
        if reg == 0:  # abs.W
            value = read_word(data, offset)
            if value is None:
                return "???", 0
            return format_hex(sign_extend(value, 16) & 0xFFFFFF, 6), 2

        if reg == 1:  # abs.L
            value = read_long(data, offset)
            if value is None:
                return "???", 0
            return format_hex(value, 8), 4

        if reg == 2:  # (d16,PC)
            value = read_word(data, offset)
            if value is None:
                return "???", 0
            disp = sign_extend(value, 16)
            if pc_base is not None:
                return format_hex((pc_base + disp) & 0xFFFFFF, 6), 2
            return f"{disp:+d}(PC)", 2

        if reg == 3:  # (d8,PC,Xn)
            value = read_word(data, offset)
            if value is None:
                return "???", 0
            disp = sign_extend(value & 0xFF, 8)
            idx_is_an = (value >> 15) & 1
            idx_reg = (value >> 12) & 0x7
            idx_size = (value >> 11) & 1
            idx_prefix = "A" if idx_is_an else "D"
            idx_suffix = ".L" if idx_size else ".W"
            if pc_base is not None:
                target = (pc_base + disp) & 0xFFFFFF
                return f"{format_hex(target, 6)}(PC,{idx_prefix}{idx_reg}{idx_suffix})", 2
            return f"{disp:+d}(PC,{idx_prefix}{idx_reg}{idx_suffix})", 2

        if reg == 4:  # immediate
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


def ea_target(mode, reg, data, offset, pc_base=None):
    """Tenta resolver o endereço alvo estático de um EA."""
    if mode == 7:
        if reg == 0:
            v = read_word(data, offset)
            if v is None:
                return None
            return sign_extend(v, 16) & 0xFFFFFF
        if reg == 1:
            v = read_long(data, offset)
            if v is None:
                return None
            return v & 0xFFFFFF
        if reg == 2:
            v = read_word(data, offset)
            if v is None or pc_base is None:
                return None
            return (pc_base + sign_extend(v, 16)) & 0xFFFFFF
    return None


def _insn(address, size, opcode, operands, data, **extra):
    result = {
        "address": address,
        "size": size,
        "opcode": opcode,
        "operands": operands,
        "bytes": data[address:address + size],
    }
    result.update(extra)
    return result


# ============================================================
# Handlers
# ============================================================


def _h_simple(opcode):
    def h(word, data, address):
        return _insn(address, 2, opcode, "", data)
    return h


_h_nop = _h_simple("NOP")
_h_rts = _h_simple("RTS")
_h_rte = _h_simple("RTE")
_h_rtr = _h_simple("RTR")
_h_reset = _h_simple("RESET")
_h_trapv = _h_simple("TRAPV")
_h_illegal = _h_simple("ILLEGAL")


def _h_stop(word, data, address):
    v = read_word(data, address + 2)
    if v is None:
        return None
    return _insn(address, 4, "STOP", f"#{format_hex(v)}", data)


def _h_trap(word, data, address):
    return _insn(address, 2, "TRAP", f"#{word & 0xF}", data)


def _h_link(word, data, address):
    reg = word & 0x7
    disp = read_word(data, address + 2)
    if disp is None:
        return None
    return _insn(address, 4, "LINK", f"A{reg},#{sign_extend(disp, 16)}", data)


def _h_unlk(word, data, address):
    return _insn(address, 2, "UNLK", f"A{word & 0x7}", data)


def _h_swap(word, data, address):
    return _insn(address, 2, "SWAP", f"D{word & 0x7}", data)


def _h_ext(word, data, address):
    reg = word & 0x7
    if word & 0x0040:
        return _insn(address, 2, "EXT.L", f"D{reg}", data)
    return _insn(address, 2, "EXT.W", f"D{reg}", data)


def _h_pea(word, data, address):
    mode = (word >> 3) & 0x7
    reg = word & 0x7
    ea, extra = decode_ea(mode, reg, "L", data, address + 2, address + 2)
    return _insn(address, 2 + extra, "PEA", ea, data)


def _h_lea(word, data, address):
    dst = (word >> 9) & 0x7
    mode = (word >> 3) & 0x7
    reg = word & 0x7
    ea, extra = decode_ea(mode, reg, "L", data, address + 2, address + 2)
    return _insn(address, 2 + extra, "LEA", f"{ea},A{dst}", data)


def _h_jsr(word, data, address):
    mode = (word >> 3) & 0x7
    reg = word & 0x7
    ea, extra = decode_ea(mode, reg, "L", data, address + 2, address + 2)
    target = ea_target(mode, reg, data, address + 2, address + 2)
    return _insn(address, 2 + extra, "JSR", ea, data, target=target)


def _h_jmp(word, data, address):
    mode = (word >> 3) & 0x7
    reg = word & 0x7
    ea, extra = decode_ea(mode, reg, "L", data, address + 2, address + 2)
    target = ea_target(mode, reg, data, address + 2, address + 2)
    return _insn(address, 2 + extra, "JMP", ea, data, target=target)


def _h_branch(word, data, address):
    cond = (word >> 8) & 0xF
    disp = word & 0xFF
    if disp == 0:
        ext = read_word(data, address + 2)
        if ext is None:
            return None
        disp = sign_extend(ext, 16)
        size = 4
    else:
        disp = sign_extend(disp, 8)
        size = 2
    target = (address + size + disp) & 0xFFFFFF
    if cond == 0:
        mnem = "BRA"
    elif cond == 1:
        mnem = "BSR"
    else:
        mnem = f"B{CONDITIONS[cond]}"
    return _insn(address, size, mnem, format_hex(target, 6), data, target=target)


def _h_dbcc(word, data, address):
    cond = (word >> 8) & 0xF
    reg = word & 0x7
    ext = read_word(data, address + 2)
    if ext is None:
        return None
    disp = sign_extend(ext, 16)
    target = (address + 2 + disp) & 0xFFFFFF
    return _insn(
        address, 4, f"DB{CONDITIONS[cond]}",
        f"D{reg},{format_hex(target, 6)}", data, target=target
    )


def _h_scc(word, data, address):
    cond = (word >> 8) & 0xF
    mode = (word >> 3) & 0x7
    reg = word & 0x7
    ea, extra = decode_ea(mode, reg, "B", data, address + 2, address + 2)
    return _insn(address, 2 + extra, f"S{CONDITIONS[cond]}", ea, data)


def _h_moveq(word, data, address):
    reg = (word >> 9) & 0x7
    value = sign_extend(word & 0xFF, 8)
    return _insn(address, 2, "MOVEQ", f"#{value},D{reg}", data)


def _h_move(word, data, address):
    size_code = (word >> 12) & 0x3
    if size_code == 0:
        return None
    size = {1: "B", 2: "L", 3: "W"}[size_code]

    dst_reg = (word >> 9) & 0x7
    dst_mode = (word >> 6) & 0x7
    src_mode = (word >> 3) & 0x7
    src_reg = word & 0x7

    src, src_extra = decode_ea(
        src_mode, src_reg, size, data, address + 2, address + 2
    )
    dst, dst_extra = decode_ea(
        dst_mode, dst_reg, size, data,
        address + 2 + src_extra, address + 2 + src_extra
    )
    total = 2 + src_extra + dst_extra

    mnem = "MOVEA" if (dst_mode == 1 and size != "B") else "MOVE"
    return _insn(address, total, f"{mnem}.{size}", f"{src},{dst}", data)


def _h_movem(word, data, address):
    mode = (word >> 3) & 0x7
    reg = word & 0x7
    mask = read_word(data, address + 2)
    if mask is None:
        return None
    size = "L" if (word & 0x0040) else "W"
    to_mem = not (word & 0x0400)

    regs = []
    if to_mem and mode == 4:
        # pre-decrement: ordem invertida
        for i in range(15, -1, -1):
            if mask & (1 << i):
                regs.append(f"A{i - 8}" if i >= 8 else f"D{i}")
    else:
        for i in range(16):
            if mask & (1 << i):
                regs.append(f"D{i}" if i < 8 else f"A{i - 8}")

    reglist = "/".join(regs) if regs else "(none)"
    ea, extra = decode_ea(mode, reg, size, data, address + 4, address + 4)

    operands = f"{reglist},{ea}" if to_mem else f"{ea},{reglist}"
    return _insn(address, 4 + extra, f"MOVEM.{size}", operands, data)


def _h_ea_single(prefix):
    def h(word, data, address):
        size_code = (word >> 6) & 0x3
        if size_code not in SIZE_NAMES:
            return None
        size = SIZE_NAMES[size_code]
        mode = (word >> 3) & 0x7
        reg = word & 0x7
        ea, extra = decode_ea(mode, reg, size, data, address + 2, address + 2)
        return _insn(address, 2 + extra, f"{prefix}.{size}", ea, data)
    return h


_h_tst = _h_ea_single("TST")
_h_clr = _h_ea_single("CLR")
_h_neg = _h_ea_single("NEG")
_h_negx = _h_ea_single("NEGX")
_h_not = _h_ea_single("NOT")


def _h_addq_subq(word, data, address):
    is_sub = bool(word & 0x0100)
    value = (word >> 9) & 0x7
    if value == 0:
        value = 8
    size_code = (word >> 6) & 0x3
    if size_code not in SIZE_NAMES:
        return None
    size = SIZE_NAMES[size_code]
    mode = (word >> 3) & 0x7
    reg = word & 0x7
    ea, extra = decode_ea(mode, reg, size, data, address + 2, address + 2)
    op = "SUBQ" if is_sub else "ADDQ"
    return _insn(address, 2 + extra, f"{op}.{size}", f"#{value},{ea}", data)


def _h_immediate(prefix):
    def h(word, data, address):
        size_code = (word >> 6) & 0x3
        if size_code not in SIZE_NAMES:
            return None
        size = SIZE_NAMES[size_code]
        mode = (word >> 3) & 0x7
        reg = word & 0x7

        if size == "L":
            imm = read_long(data, address + 2)
            imm_size = 4
            imm_str = format_hex(imm, 8) if imm is not None else "???"
        else:
            imm = read_word(data, address + 2)
            imm_size = 2
            if imm is not None and size == "B":
                imm &= 0xFF
            imm_str = format_hex(imm, 4) if imm is not None else "???"

        if imm is None:
            return None

        ea, ea_extra = decode_ea(
            mode, reg, size, data,
            address + 2 + imm_size,
            address + 2 + imm_size
        )
        total = 2 + imm_size + ea_extra
        return _insn(address, total, f"{prefix}.{size}", f"#{imm_str},{ea}", data)
    return h


_h_ori = _h_immediate("ORI")
_h_andi = _h_immediate("ANDI")
_h_subi = _h_immediate("SUBI")
_h_addi = _h_immediate("ADDI")
_h_eori = _h_immediate("EORI")
_h_cmpi = _h_immediate("CMPI")


def _h_alu(op, opa):
    """
    Handler genérico para ADD, SUB, AND, OR.
    opa é usado para ADDA/SUBA (opmode 3 e 7).
    """
    def h(word, data, address):
        reg = (word >> 9) & 0x7
        opmode = (word >> 6) & 0x7
        mode = (word >> 3) & 0x7
        ea_reg = word & 0x7

        size_map = {0: "B", 1: "W", 2: "L"}

        if opmode in (0, 1, 2):
            size = size_map[opmode]
            ea, extra = decode_ea(mode, ea_reg, size, data, address + 2, address + 2)
            return _insn(address, 2 + extra, f"{op}.{size}", f"{ea},D{reg}", data)

        if opmode in (4, 5, 6):
            size = size_map[opmode - 4]
            ea, extra = decode_ea(mode, ea_reg, size, data, address + 2, address + 2)
            return _insn(address, 2 + extra, f"{op}.{size}", f"D{reg},{ea}", data)

        if opmode == 3:
            ea, extra = decode_ea(mode, ea_reg, "W", data, address + 2, address + 2)
            return _insn(address, 2 + extra, f"{opa}.W", f"{ea},A{reg}", data)

        if opmode == 7:
            ea, extra = decode_ea(mode, ea_reg, "L", data, address + 2, address + 2)
            return _insn(address, 2 + extra, f"{opa}.L", f"{ea},A{reg}", data)

        return None
    return h


_h_add = _h_alu("ADD", "ADDA")
_h_sub = _h_alu("SUB", "SUBA")


def _h_and(word, data, address):
    reg = (word >> 9) & 0x7
    opmode = (word >> 6) & 0x7
    mode = (word >> 3) & 0x7
    ea_reg = word & 0x7
    size_map = {0: "B", 1: "W", 2: "L"}
    if opmode in (0, 1, 2):
        size = size_map[opmode]
        ea, extra = decode_ea(mode, ea_reg, size, data, address + 2, address + 2)
        return _insn(address, 2 + extra, f"AND.{size}", f"{ea},D{reg}", data)
    if opmode in (4, 5, 6):
        size = size_map[opmode - 4]
        ea, extra = decode_ea(mode, ea_reg, size, data, address + 2, address + 2)
        return _insn(address, 2 + extra, f"AND.{size}", f"D{reg},{ea}", data)
    return None


def _h_or(word, data, address):
    reg = (word >> 9) & 0x7
    opmode = (word >> 6) & 0x7
    mode = (word >> 3) & 0x7
    ea_reg = word & 0x7
    size_map = {0: "B", 1: "W", 2: "L"}
    if opmode in (0, 1, 2):
        size = size_map[opmode]
        ea, extra = decode_ea(mode, ea_reg, size, data, address + 2, address + 2)
        return _insn(address, 2 + extra, f"OR.{size}", f"{ea},D{reg}", data)
    if opmode in (4, 5, 6):
        size = size_map[opmode - 4]
        ea, extra = decode_ea(mode, ea_reg, size, data, address + 2, address + 2)
        return _insn(address, 2 + extra, f"OR.{size}", f"D{reg},{ea}", data)
    return None


def _h_b000(word, data, address):
    """CMP / CMPA / CMPM / EOR (tudo em 0xBxxx)."""
    reg = (word >> 9) & 0x7
    opmode = (word >> 6) & 0x7
    mode = (word >> 3) & 0x7
    ea_reg = word & 0x7
    size_map = {0: "B", 1: "W", 2: "L"}

    if opmode in (0, 1, 2):
        size = size_map[opmode]
        ea, extra = decode_ea(mode, ea_reg, size, data, address + 2, address + 2)
        return _insn(address, 2 + extra, f"CMP.{size}", f"{ea},D{reg}", data)

    if opmode == 3:
        ea, extra = decode_ea(mode, ea_reg, "W", data, address + 2, address + 2)
        return _insn(address, 2 + extra, "CMPA.W", f"{ea},A{reg}", data)

    if opmode == 7:
        ea, extra = decode_ea(mode, ea_reg, "L", data, address + 2, address + 2)
        return _insn(address, 2 + extra, "CMPA.L", f"{ea},A{reg}", data)

    if opmode in (4, 5, 6):
        size = size_map[opmode - 4]
        if mode == 1:
            # CMPM (Ay)+,(Ax)+
            return _insn(
                address, 2, f"CMPM.{size}",
                f"(A{ea_reg})+,(A{reg})+", data
            )
        ea, extra = decode_ea(mode, ea_reg, size, data, address + 2, address + 2)
        return _insn(address, 2 + extra, f"EOR.{size}", f"D{reg},{ea}", data)

    return None


# ============================================================
# Tabela de opcodes
# ============================================================
#
# A ordem importa: padrões específicos primeiro.
# Handlers podem retornar None para cair no próximo.
# ============================================================

OPCODE_TABLE = [
    # --- Sem operandos ---
    (0xFFFF, 0x4E71, _h_nop),
    (0xFFFF, 0x4E75, _h_rts),
    (0xFFFF, 0x4E73, _h_rte),
    (0xFFFF, 0x4E77, _h_rtr),
    (0xFFFF, 0x4E70, _h_reset),
    (0xFFFF, 0x4E76, _h_trapv),
    (0xFFFF, 0x4AFC, _h_illegal),
    (0xFFFF, 0x4E72, _h_stop),

    # --- Específicos ---
    (0xFFF0, 0x4E40, _h_trap),
    (0xFFF8, 0x4E50, _h_link),
    (0xFFF8, 0x4E58, _h_unlk),
    (0xFFF8, 0x4880, _h_ext),
    (0xFFF8, 0x48C0, _h_ext),
    (0xFFF8, 0x4840, _h_swap),
    (0xFFC0, 0x4840, _h_pea),
    (0xF1C0, 0x41C0, _h_lea),

    # --- MOVEM (depois de EXT, que é mais específico) ---
    (0xFB80, 0x4880, _h_movem),
    (0xFB80, 0x4C80, _h_movem),

    # --- Fluxo ---
    (0xFFC0, 0x4E80, _h_jsr),
    (0xFFC0, 0x4EC0, _h_jmp),
    (0xF000, 0x6000, _h_branch),
    (0xF0F8, 0x50C8, _h_dbcc),
    (0xF0C0, 0x50C0, _h_scc),

    # --- MOVEQ ---
    (0xF100, 0x7000, _h_moveq),

    # --- MOVE (B, L, W) ---
    (0xF000, 0x1000, _h_move),
    (0xF000, 0x2000, _h_move),
    (0xF000, 0x3000, _h_move),

    # --- ADDQ / SUBQ ---
    (0xF000, 0x5000, _h_addq_subq),

    # --- ALU Dn ---
    (0xF000, 0xD000, _h_add),
    (0xF000, 0x9000, _h_sub),
    (0xF000, 0xC000, _h_and),
    (0xF000, 0x8000, _h_or),
    (0xF000, 0xB000, _h_b000),  # CMP / CMPA / CMPM / EOR

    # --- TST / CLR / NEG / NEGX / NOT ---
    (0xFF00, 0x4A00, _h_tst),
    (0xFF00, 0x4200, _h_clr),
    (0xFF00, 0x4400, _h_neg),
    (0xFF00, 0x4000, _h_negx),
    (0xFF00, 0x4600, _h_not),

    # --- Immediate ---
    (0xFF00, 0x0000, _h_ori),
    (0xFF00, 0x0200, _h_andi),
    (0xFF00, 0x0400, _h_subi),
    (0xFF00, 0x0600, _h_addi),
    (0xFF00, 0x0A00, _h_eori),
    (0xFF00, 0x0C00, _h_cmpi),
]


def decode_instruction(data, address):
    """Decodifica uma instrução. Retorna dict ou None."""
    word = read_word(data, address)
    if word is None:
        return None

    for mask, value, handler in OPCODE_TABLE:
        if (word & mask) == value:
            result = handler(word, data, address)
            if result is not None:
                return result

    # Fallback: dado
    return {
        "address": address,
        "size": 2,
        "opcode": "DC.W",
        "operands": format_hex(word),
        "bytes": data[address:address + 2],
    }


# ============================================================
# Recursive descent
# ============================================================


def _collect_entry_points(data):
    """Extrai pontos de entrada dos vetores de reset e interrupção."""
    entries = set()
    if len(data) < 8:
        return entries

    pc = read_long(data, 4)
    if pc is not None and 0 <= pc < len(data):
        entries.add(pc)

    if len(data) >= 0x100:
        for i in range(0x008, 0x100, 4):
            target = read_long(data, i)
            if target is not None and 0 < target < len(data):
                entries.add(target)

    return entries


TERMINATORS = {"BRA", "JMP", "RTS", "RTE", "RTR"}


def recursive_descent(data, entries):
    """
    Marca endereços de código usando recursive descent.

    Retorna {address: instruction_dict}.
    """
    code = {}
    visited = set()
    worklist = list(entries)

    while worklist:
        addr = worklist.pop()

        while 0 <= addr < len(data):
            if addr in visited:
                break

            insn = decode_instruction(data, addr)
            if insn is None:
                break

            visited.add(addr)
            code[addr] = insn

            target = insn.get("target")
            if target is not None and 0 <= target < len(data):
                worklist.append(target)

            if insn["opcode"] in TERMINATORS:
                break

            addr += insn["size"]

    return code


# ============================================================
# Disassemble
# ============================================================


def _format_instruction_line(address, insn):
    opcode = insn["opcode"]
    operands = insn["operands"]
    line = f"{address:06X}: {opcode}"
    if operands:
        line += f" {operands}"
    return line


def _format_data_line(address, word):
    return f"{address:06X}: DC.W {format_hex(word)}"


def disassemble(bin_path, project_dir):
    bin_path = Path(bin_path)
    project_dir = Path(project_dir)
    output_path = project_dir / f"{bin_path.stem}_68000.asm"

    data = bin_path.read_bytes()

    print(f"Disassemblando: {bin_path}")
    print(f"Tamanho: {len(data):,} bytes")

    lines = []
    lines.append("; ========================================")
    lines.append("; MegaComp - Motorola 68000 Disassembly")
    lines.append("; ========================================")
    lines.append(f"; ROM: {bin_path.name}")
    lines.append(f"; Tamanho: {len(data):,} bytes")
    lines.append(";")
    lines.append("; Gerado pelo MegaComp")
    lines.append("; ========================================")
    lines.append("")

    # Vetores iniciais
    if len(data) >= 8:
        initial_sp = read_long(data, 0)
        initial_pc = read_long(data, 4)
        lines.append("; ----------------------------------------")
        lines.append("; Vetores iniciais")
        lines.append("; ----------------------------------------")
        lines.append(f"Initial_SP: dc.l ${initial_sp:08X}")
        lines.append(f"Initial_PC: dc.l ${initial_pc:08X}")
        lines.append("")

    # Recursive descent
    entries = _collect_entry_points(data)
    print(f"Pontos de entrada: {len(entries)}")

    code = recursive_descent(data, entries)
    print(f"Instruções de código: {len(code):,}")

    # Saída linear: código + dados
    lines.append("; ----------------------------------------")
    lines.append("; Código e dados")
    lines.append("; ----------------------------------------")
    lines.append("")

    address = 0
    total = len(data)

    while address < total:
        if address in code:
            insn = code[address]
            lines.append(_format_instruction_line(address, insn))
            address += insn["size"]
        else:
            word = read_word(data, address)
            if word is None:
                break
            lines.append(_format_data_line(address, word))
            address += 2

    output_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"Assembly criado: {output_path}")
    return output_path