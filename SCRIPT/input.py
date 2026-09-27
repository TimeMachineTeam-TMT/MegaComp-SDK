"""
MegaComp - Input translation module

Traduz teclado e gamepad para o formato do controle de Mega Drive,
gerando o arquivo MASM `input.inc` que o runtime inclui.

Uso:
    from input import generate
    generate(project_dir)

Ou pela linha de comando:
    python input.py <project_dir>
"""

from pathlib import Path


# ============================================================
# Layout do controle de Mega Drive
# ============================================================
#
# Bit 7 (unused) lê sempre 1.
# Bit 6 é o estado TH refletido.
# Bits 0..5 dependem do TH:
#
#   TH = 1:  bit0=Up  bit1=Down  bit2=Left  bit3=Right  bit4=A  bit5=Start
#   TH = 0:  bit0=Up  bit1=Down  bit2=Left  bit3=Right  bit4=B  bit5=C
#
# Bits são ativos em nível BAIXO (0 = pressionado).

MD_UP    = 0x01
MD_DOWN  = 0x02
MD_LEFT  = 0x04
MD_RIGHT = 0x08
MD_A     = 0x10   # TH=1
MD_B     = 0x10   # TH=0
MD_START = 0x20   # TH=1
MD_C     = 0x20   # TH=0

MD_DIRECTIONS = {
    "up":    MD_UP,
    "down":  MD_DOWN,
    "left":  MD_LEFT,
    "right": MD_RIGHT,
}


# ============================================================
# Virtual key codes (Windows)
# ============================================================
# https://learn.microsoft.com/windows/win32/inputdev/virtual-key-codes

VK = {
    "up":     0x26,
    "down":   0x28,
    "left":   0x25,
    "right":  0x27,
    "z":      0x5A,
    "x":      0x58,
    "c":      0x43,
    "enter":  0x0D,
    "space":  0x20,
    "escape": 0x1B,
}


# ============================================================
# XInput button bits
# ============================================================
# https://learn.microsoft.com/windows/win32/api/xinput/ns-xinput-xinput_gamepad

XINPUT = {
    "up":     0x0001,
    "down":   0x0002,
    "left":   0x0004,
    "right":  0x0008,
    "start":  0x0010,
    "back":   0x0020,
    "lthumb": 0x0040,
    "rthumb": 0x0080,
    "lb":     0x0100,
    "rb":     0x0200,
    "a":      0x1000,
    "b":      0x2000,
    "x":      0x4000,
    "y":      0x8000,
}


# ============================================================
# Mapeamentos default
# ============================================================
#
# Estrutura: "botao_md" -> "tecla_ou_botao_fisico"
#
# Botões do MD: up, down, left, right, a, b, c, start.
#
# Teclado: Z=jump(A), X=roll(B), C=jump(C), Enter=pause.
# Gamepad: A=A, B=B, X=C, Start=Start, D-pad=direções.

DEFAULT_KEYBOARD_MAP = {
    "up":    "up",
    "down":  "down",
    "left":  "left",
    "right": "right",
    "a":     "z",
    "b":     "x",
    "c":     "c",
    "start": "enter",
}

DEFAULT_GAMEPAD_MAP = {
    "up":    "up",
    "down":  "down",
    "left":  "left",
    "right": "right",
    "a":     "a",     # Xbox A -> MD A
    "b":     "b",     # Xbox B -> MD B
    "c":     "x",     # Xbox X -> MD C
    "start": "start",
}


# ============================================================
# Helpers de geração de MASM
# ============================================================


def _clear_bit_lines(labels, bit):
    """Gera linhas MASM para limpar um bit em uma ou mais variáveis."""
    mask = (~bit) & 0xFF
    return [
        f"    and byte ptr [{lbl}], {mask:02X}h"
        for lbl in labels
    ]


def _gen_keyboard_for_button(md_button, vk_code, kb_map):
    """
    Gera o bloco MASM que checa uma tecla e atualiza as variáveis
    de estado do controle 1.
    """
    lines = []
    label_id = f"kb_{md_button}"

    lines.append(f"    mov ecx, {vk_code:02X}h")
    lines.append("    call GetAsyncKeyState")
    lines.append("    test ax, 8000h")
    lines.append(f"    jz @@skip_{label_id}")

    if md_button in MD_DIRECTIONS:
        bit = MD_DIRECTIONS[md_button]
        # Direções afetam os dois estados (TH=0 e TH=1)
        lines += _clear_bit_lines(
            ["ctrl1_state_th0", "ctrl1_state_th1"], bit
        )
    elif md_button == "a":
        lines += _clear_bit_lines(["ctrl1_state_th1"], MD_A)
    elif md_button == "start":
        lines += _clear_bit_lines(["ctrl1_state_th1"], MD_START)
    elif md_button == "b":
        lines += _clear_bit_lines(["ctrl1_state_th0"], MD_B)
    elif md_button == "c":
        lines += _clear_bit_lines(["ctrl1_state_th0"], MD_C)

    lines.append(f"@@skip_{label_id}:")
    return lines


def _gen_gamepad_for_button(md_button, xinput_bit):
    """Gera o bloco MASM que checa um botão de gamepad."""
    lines = []
    label_id = f"gp_{md_button}"

    lines.append(f"    test ax, {xinput_bit:04X}h")
    lines.append(f"    jz @@skip_{label_id}")

    if md_button in MD_DIRECTIONS:
        bit = MD_DIRECTIONS[md_button]
        lines += _clear_bit_lines(
            ["ctrl1_state_th0", "ctrl1_state_th1"], bit
        )
    elif md_button == "a":
        lines += _clear_bit_lines(["ctrl1_state_th1"], MD_A)
    elif md_button == "start":
        lines += _clear_bit_lines(["ctrl1_state_th1"], MD_START)
    elif md_button == "b":
        lines += _clear_bit_lines(["ctrl1_state_th0"], MD_B)
    elif md_button == "c":
        lines += _clear_bit_lines(["ctrl1_state_th0"], MD_C)

    lines.append(f"@@skip_{label_id}:")
    return lines


# ============================================================
# Geração do input.inc
# ============================================================


def generate(project_dir, keyboard_map=None, gamepad_map=None):
    """
    Gera `input.inc` no diretório do projeto.

    keyboard_map / gamepad_map: dicts "botao_md" -> "tecla" (opcional).
    """

    project_dir = Path(project_dir)
    output_path = project_dir / "input.inc"

    kb_map = dict(DEFAULT_KEYBOARD_MAP)
    gp_map = dict(DEFAULT_GAMEPAD_MAP)

    if keyboard_map:
        kb_map.update(keyboard_map)
    if gamepad_map:
        gp_map.update(gamepad_map)

    # --------------------------------------------------------
    # Validação
    # --------------------------------------------------------

    valid_md = set(MD_DIRECTIONS) | {"a", "b", "c", "start"}

    for k in kb_map:
        if k not in valid_md:
            raise ValueError(f"botão MD inválido: {k}")
        if kb_map[k] not in VK:
            raise ValueError(f"tecla desconhecida: {kb_map[k]}")

    for k in gp_map:
        if k not in valid_md:
            raise ValueError(f"botão MD inválido: {k}")
        if gp_map[k] not in XINPUT:
            raise ValueError(f"botão XInput desconhecido: {gp_map[k]}")

    # --------------------------------------------------------
    # Cabeçalho
    # --------------------------------------------------------

    lines = []
    lines.append("; ============================================")
    lines.append("; input.inc - MegaComp")
    lines.append("; Tradução de teclado/gamepad para controle MD")
    lines.append("; ============================================")
    lines.append(";")
    lines.append("; Gerado automaticamente por input.py.")
    lines.append("; NÃO EDITAR MANUALMENTE.")
    lines.append(";")
    lines.append("; Estado exposto:")
    lines.append(";   ctrl1_state_th0  - byte para leitura com TH=0")
    lines.append(";   ctrl1_state_th1  - byte para leitura com TH=1")
    lines.append(";   ctrl1_th         - estado atual do pino TH")
    lines.append(";")
    lines.append("; APIs usadas: GetAsyncKeyState (user32),")
    lines.append(";              XInputGetState (xinput1_4)")
    lines.append("; ============================================")
    lines.append("")

    # --------------------------------------------------------
    # Externs e dados
    # --------------------------------------------------------

    lines.append("extern GetAsyncKeyState:proc")
    lines.append("extern XInputGetState:proc")
    lines.append("")

    lines.append(".data")
    lines.append("")

    lines.append("public ctrl1_state_th0")
    lines.append("public ctrl1_state_th1")
    lines.append("public ctrl1_th")
    lines.append("public ctrl1_present")
    lines.append("ctrl1_state_th0 db 0FFh")
    lines.append("ctrl1_state_th1 db 0FFh")
    lines.append("ctrl1_th        db 1")
    lines.append("ctrl1_present   db 0")
    lines.append("")

    lines.append("public ctrl2_state_th0")
    lines.append("public ctrl2_state_th1")
    lines.append("public ctrl2_th")
    lines.append("public ctrl2_present")
    lines.append("ctrl2_state_th0 db 0FFh")
    lines.append("ctrl2_state_th1 db 0FFh")
    lines.append("ctrl2_th        db 1")
    lines.append("ctrl2_present   db 0")
    lines.append("")

    lines.append("; buffer XINPUT_STATE (16 bytes)")
    lines.append("xinput_state    db 16 dup(0)")
    lines.append("")

    # --------------------------------------------------------
    # poll_input
    # --------------------------------------------------------

    lines.append(".code")
    lines.append("")
    lines.append("; ============================================")
    lines.append("; poll_input - lê teclado e gamepad, atualiza")
    lines.append(";   ctrl1_state_th0/th1. Chamar 1x por frame.")
    lines.append("; ============================================")
    lines.append("public poll_input")
    lines.append("poll_input PROC")
    lines.append("    push rbp")
    lines.append("    mov rbp, rsp")
    lines.append("    sub rsp, 64")
    lines.append("")
    lines.append("    ; zera estado (todos soltos = 1)")
    lines.append("    mov byte ptr [ctrl1_state_th0], 0FFh")
    lines.append("    mov byte ptr [ctrl1_state_th1], 0FFh")
    lines.append("    mov byte ptr [ctrl1_present], 0")
    lines.append("")

    # ---------- Teclado ----------
    lines.append("    ; -------- TECLADO --------")
    for md_button in ["up", "down", "left", "right", "a", "b", "c", "start"]:
        vk_name = kb_map.get(md_button)
        if vk_name is None:
            continue
        vk_code = VK[vk_name]
        lines += _gen_keyboard_for_button(md_button, vk_code, kb_map)
        lines.append("")

    # ---------- Gamepad ----------
    lines.append("    ; -------- GAMEPAD (XInput) --------")
    lines.append("    xor ecx, ecx")
    lines.append("    lea rdx, [xinput_state]")
    lines.append("    call XInputGetState")
    lines.append("    test eax, eax")
    lines.append("    jnz @@no_gamepad")
    lines.append("    mov byte ptr [ctrl1_present], 1")
    lines.append("    movzx eax, word ptr [xinput_state + 4]")
    lines.append("")

    for md_button in ["up", "down", "left", "right", "a", "b", "c", "start"]:
        gp_name = gp_map.get(md_button)
        if gp_name is None:
            continue
        xbit = XINPUT[gp_name]
        lines += _gen_gamepad_for_button(md_button, xbit)
        lines.append("")

    lines.append("@@no_gamepad:")
    lines.append("")
    lines.append("    mov rsp, rbp")
    lines.append("    pop rbp")
    lines.append("    ret")
    lines.append("poll_input ENDP")
    lines.append("")

    # --------------------------------------------------------
    # read_io_byte
    # --------------------------------------------------------
    # Entrada: ecx = offset dentro de $A10000 (0..1F)
    # Saída:   al  = valor lido

    lines.append("; ============================================")
    lines.append("; read_io_byte - lê $A10000..$A1001F")
    lines.append(";   entrada: ecx = offset")
    lines.append(";   saída:   al")
    lines.append("; ============================================")
    lines.append("public read_io_byte")
    lines.append("read_io_byte PROC")
    lines.append("    and ecx, 1Fh")
    lines.append("    cmp ecx, 01h")
    lines.append("    je @@ver")
    lines.append("    cmp ecx, 03h")
    lines.append("    je @@ctrl1_data")
    lines.append("    cmp ecx, 05h")
    lines.append("    je @@ctrl2_data")
    lines.append("    xor eax, eax")
    lines.append("    ret")
    lines.append("")
    lines.append("@@ver:")
    lines.append("    ; version register: bit7=1, bit6=1 (PAL), bits0-3 versão")
    lines.append("    mov al, 0A0h")
    lines.append("    ret")
    lines.append("")
    lines.append("@@ctrl1_data:")
    lines.append("    mov al, [ctrl1_th]")
    lines.append("    test al, al")
    lines.append("    jz @@ctrl1_th0")
    lines.append("    mov al, [ctrl1_state_th1]")
    lines.append("    or al, 80h")
    lines.append("    ret")
    lines.append("@@ctrl1_th0:")
    lines.append("    mov al, [ctrl1_state_th0]")
    lines.append("    or al, 80h")
    lines.append("    ret")
    lines.append("")
    lines.append("@@ctrl2_data:")
    lines.append("    mov al, [ctrl2_th]")
    lines.append("    test al, al")
    lines.append("    jz @@ctrl2_th0")
    lines.append("    mov al, [ctrl2_state_th1]")
    lines.append("    or al, 80h")
    lines.append("    ret")
    lines.append("@@ctrl2_th0:")
    lines.append("    mov al, [ctrl2_state_th0]")
    lines.append("    or al, 80h")
    lines.append("    ret")
    lines.append("read_io_byte ENDP")
    lines.append("")

    # --------------------------------------------------------
    # write_io_byte
    # --------------------------------------------------------
    # Entrada: ecx = offset dentro de $A10000, dl = valor
    # Só bit 6 (TH) tem efeito.

    lines.append("; ============================================")
    lines.append("; write_io_byte - escreve $A10000..$A1001F")
    lines.append(";   entrada: ecx = offset, dl = valor")
    lines.append("; ============================================")
    lines.append("public write_io_byte")
    lines.append("write_io_byte PROC")
    lines.append("    and ecx, 1Fh")
    lines.append("    cmp ecx, 03h")
    lines.append("    je @@ctrl1_write")
    lines.append("    cmp ecx, 05h")
    lines.append("    je @@ctrl2_write")
    lines.append("    ret")
    lines.append("")
    lines.append("@@ctrl1_write:")
    lines.append("    test dl, 40h")
    lines.append("    jz @@ctrl1_th0_set")
    lines.append("    mov byte ptr [ctrl1_th], 1")
    lines.append("    ret")
    lines.append("@@ctrl1_th0_set:")
    lines.append("    mov byte ptr [ctrl1_th], 0")
    lines.append("    ret")
    lines.append("")
    lines.append("@@ctrl2_write:")
    lines.append("    test dl, 40h")
    lines.append("    jz @@ctrl2_th0_set")
    lines.append("    mov byte ptr [ctrl2_th], 1")
    lines.append("    ret")
    lines.append("@@ctrl2_th0_set:")
    lines.append("    mov byte ptr [ctrl2_th], 0")
    lines.append("    ret")
    lines.append("write_io_byte ENDP")
    lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"Input module criado: {output_path}")
    print(f"  Teclado:  {len(kb_map)} botões mapeados")
    print(f"  Gamepad:  {len(gp_map)} botões mapeados")

    return output_path


if __name__ == "__main__":
    import sys
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    generate(target)