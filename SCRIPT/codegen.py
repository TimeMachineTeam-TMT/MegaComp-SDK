from pathlib import Path


def generate(analysis, project_dir):
    """
    Gera Assembly x86-64 compatível com MASM (ml64.exe).

    Entrada:
        analysis  -> resultado do analyzer.py
        project_dir -> pasta do projeto

    Saída:
        Path do arquivo *_win.asm
    """

    project_dir = Path(project_dir)
    asm_path = Path(analysis["asm_path"])

    # Sonic1_68000.asm -> Sonic1_win.asm
    name = asm_path.stem.replace("_68000", "")
    output_path = project_dir / f"{name}_win.asm"

    instructions = analysis["instructions"]
    functions = analysis["functions"]
    branches = analysis["branches"]
    jumps = analysis["jumps"]

    lines = []

    # ==========================================
    # CABEÇALHO
    # ==========================================

    lines.append("; ========================================")
    lines.append("; MegaComp - x86-64 / MASM")
    lines.append("; ========================================")
    lines.append(f"; Source: {asm_path.name}")
    lines.append("; Target: Windows x86-64")
    lines.append("; Assembler: Microsoft MASM (ml64.exe)")
    lines.append("; ========================================")
    lines.append("")

    # ==========================================
    # SEGMENTO DE CÓDIGO
    # ==========================================

    lines.append(".code")
    lines.append("")

    # ==========================================
    # FUNÇÕES DETECTADAS
    # ==========================================

    for address in functions:

        lines.append("; ----------------------------------------")
        lines.append(f"; 68000 function ${address:06X}")
        lines.append("; ----------------------------------------")

        lines.append(
            f"function_{address:06X} PROC"
        )

        lines.append(
            "    ; TODO: código recompilado"
        )

        lines.append(
            "    ret"
        )

        lines.append(
            f"function_{address:06X} ENDP"
        )

        lines.append("")

    # ==========================================
    # CÓDIGO RECOMPILADO
    # ==========================================

    lines.append("; ========================================")
    lines.append("; Código recompilado")
    lines.append("; ========================================")
    lines.append("")

    for instruction in instructions:

        address = instruction["address"]
        opcode = instruction["opcode"]
        operands = instruction["operands"]

        # Comentário preservando a instrução original
        lines.append(
            f"; 68000: {address:06X}: "
            f"{opcode} {operands}"
        )

        # --------------------------------------
        # NOP
        # --------------------------------------

        if opcode == "NOP":

            lines.append(
                "    nop"
            )

        # --------------------------------------
        # RTS
        # --------------------------------------

        elif opcode == "RTS":

            lines.append(
                "    ret"
            )

        # --------------------------------------
        # JSR
        # --------------------------------------

        elif opcode == "JSR":

            lines.append(
                "    ; TODO: traduzir JSR"
            )

        # --------------------------------------
        # JMP
        # --------------------------------------

        elif opcode == "JMP":

            lines.append(
                "    ; TODO: traduzir JMP"
            )

        # --------------------------------------
        # BRA
        # --------------------------------------

        elif opcode == "BRA":

            lines.append(
                "    ; TODO: traduzir BRA"
            )

        # --------------------------------------
        # Branches condicionais
        # --------------------------------------

        elif opcode in {
            "BCC", "BCS",
            "BEQ", "BGE",
            "BGT", "BHI",
            "BLE", "BLT",
            "BLS", "BMI",
            "BNE", "BPL",
            "BVC", "BVS",
        }:

            lines.append(
                "    ; TODO: traduzir branch condicional"
            )

        # --------------------------------------
        # Outras instruções
        # --------------------------------------

        else:

            lines.append(
                "    ; TODO: traduzir instrução 68000"
            )

        lines.append("")

    # ==========================================
    # ENTRY POINT
    # ==========================================

    lines.append("; ========================================")
    lines.append("; Entry point")
    lines.append("; ========================================")
    lines.append("")

    lines.append("MegaComp_Main PROC")
    lines.append("    xor rax, rax")
    lines.append("    ret")
    lines.append("MegaComp_Main ENDP")
    lines.append("")

    # ==========================================
    # ESTATÍSTICAS
    # ==========================================

    lines.append("; ========================================")
    lines.append("; Analysis information")
    lines.append("; ========================================")
    lines.append(
        f"; Instructions: {len(instructions)}"
    )
    lines.append(
        f"; Functions:    {len(functions)}"
    )
    lines.append(
        f"; Branches:     {len(branches)}"
    )
    lines.append(
        f"; Jumps:        {len(jumps)}"
    )
    lines.append("")

    # ==========================================
    # FIM DO ARQUIVO MASM
    # ==========================================

    lines.append("END")

    # ==========================================
    # SALVAR
    # ==========================================

    output_path.write_text(
        "\n".join(lines),
        encoding="utf-8"
    )

    print(
        f"Assembly MASM criado: {output_path}"
    )

    return output_path