from pathlib import Path


def disassemble(bin_path, project_dir):
    """
    Desmonta uma ROM Mega Drive (Motorola 68000)
    para Assembly 68000.

    Retorna:
        Path do arquivo .asm criado.
    """

    bin_path = Path(bin_path)
    project_dir = Path(project_dir)

    output_path = project_dir / f"{bin_path.stem}_68000.asm"

    data = bin_path.read_bytes()

    print(f"Disassemblando: {bin_path}")
    print(f"Tamanho: {len(data):,} bytes")

    # ==========================================
    # CABEÇALHO
    # ==========================================

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

    # ==========================================
    # VETOR INICIAL
    # ==========================================

    if len(data) >= 8:

        initial_sp = int.from_bytes(
            data[0:4],
            byteorder="big"
        )

        initial_pc = int.from_bytes(
            data[4:8],
            byteorder="big"
        )

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

    # ==========================================
    # DISASSEMBLY
    # ==========================================
    #
    # Por enquanto, esta etapa apenas percorre
    # os bytes. O decoder 68000 será implementado
    # aqui posteriormente.
    #

    lines.append("; ----------------------------------------")
    lines.append("; Código")
    lines.append("; ----------------------------------------")
    lines.append("")

    address = 0

    while address < len(data):

        # Lê uma word 68000
        if address + 1 < len(data):

            opcode = int.from_bytes(
                data[address:address + 2],
                byteorder="big"
            )

            lines.append(
                f"{address:06X}: dc.w ${opcode:04X}"
            )

            address += 2

        else:
            lines.append(
                f"{address:06X}: dc.b ${data[address]:02X}"
            )

            address += 1

    # ==========================================
    # SALVA ASM
    # ==========================================

    output_path.write_text(
        "\n".join(lines),
        encoding="utf-8"
    )

    print(f"Assembly criado: {output_path}")

    return output_path