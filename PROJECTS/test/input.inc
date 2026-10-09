; ============================================
; input.inc - MegaComp
; Tradução de teclado/gamepad para controle MD
; ============================================
;
; Gerado automaticamente por input.py.
; NÃO EDITAR MANUALMENTE.
;
; Estado exposto:
;   ctrl1_state_th0  - byte para leitura com TH=0
;   ctrl1_state_th1  - byte para leitura com TH=1
;   ctrl1_th         - estado atual do pino TH
;
; APIs usadas: GetAsyncKeyState (user32),
;              XInputGetState (xinput1_4)
; ============================================

extern GetAsyncKeyState:proc
extern XInputGetState:proc

.data

public ctrl1_state_th0
public ctrl1_state_th1
public ctrl1_th
public ctrl1_present
ctrl1_state_th0 db 0FFh
ctrl1_state_th1 db 0FFh
ctrl1_th        db 1
ctrl1_present   db 0

public ctrl2_state_th0
public ctrl2_state_th1
public ctrl2_th
public ctrl2_present
ctrl2_state_th0 db 0FFh
ctrl2_state_th1 db 0FFh
ctrl2_th        db 1
ctrl2_present   db 0

; buffer XINPUT_STATE (16 bytes)
xinput_state    db 16 dup(0)

.code

; ============================================
; poll_input - lê teclado e gamepad, atualiza
;   ctrl1_state_th0/th1. Chamar 1x por frame.
; ============================================
public poll_input
poll_input PROC
    push rbp
    mov rbp, rsp
    sub rsp, 64

    ; zera estado (todos soltos = 1)
    mov byte ptr [ctrl1_state_th0], 0FFh
    mov byte ptr [ctrl1_state_th1], 0FFh
    mov byte ptr [ctrl1_present], 0

    ; -------- TECLADO --------
    mov ecx, 26h
    call GetAsyncKeyState
    test ax, 8000h
    jz @@skip_kb_up
    and byte ptr [ctrl1_state_th0], FEh
    and byte ptr [ctrl1_state_th1], FEh
@@skip_kb_up:

    mov ecx, 28h
    call GetAsyncKeyState
    test ax, 8000h
    jz @@skip_kb_down
    and byte ptr [ctrl1_state_th0], FDh
    and byte ptr [ctrl1_state_th1], FDh
@@skip_kb_down:

    mov ecx, 25h
    call GetAsyncKeyState
    test ax, 8000h
    jz @@skip_kb_left
    and byte ptr [ctrl1_state_th0], FBh
    and byte ptr [ctrl1_state_th1], FBh
@@skip_kb_left:

    mov ecx, 27h
    call GetAsyncKeyState
    test ax, 8000h
    jz @@skip_kb_right
    and byte ptr [ctrl1_state_th0], F7h
    and byte ptr [ctrl1_state_th1], F7h
@@skip_kb_right:

    mov ecx, 5Ah
    call GetAsyncKeyState
    test ax, 8000h
    jz @@skip_kb_a
    and byte ptr [ctrl1_state_th1], EFh
@@skip_kb_a:

    mov ecx, 58h
    call GetAsyncKeyState
    test ax, 8000h
    jz @@skip_kb_b
    and byte ptr [ctrl1_state_th0], EFh
@@skip_kb_b:

    mov ecx, 43h
    call GetAsyncKeyState
    test ax, 8000h
    jz @@skip_kb_c
    and byte ptr [ctrl1_state_th0], DFh
@@skip_kb_c:

    mov ecx, 0Dh
    call GetAsyncKeyState
    test ax, 8000h
    jz @@skip_kb_start
    and byte ptr [ctrl1_state_th1], DFh
@@skip_kb_start:

    ; -------- GAMEPAD (XInput) --------
    xor ecx, ecx
    lea rdx, [xinput_state]
    call XInputGetState
    test eax, eax
    jnz @@no_gamepad
    mov byte ptr [ctrl1_present], 1
    movzx eax, word ptr [xinput_state + 4]

    test ax, 0001h
    jz @@skip_gp_up
    and byte ptr [ctrl1_state_th0], FEh
    and byte ptr [ctrl1_state_th1], FEh
@@skip_gp_up:

    test ax, 0002h
    jz @@skip_gp_down
    and byte ptr [ctrl1_state_th0], FDh
    and byte ptr [ctrl1_state_th1], FDh
@@skip_gp_down:

    test ax, 0004h
    jz @@skip_gp_left
    and byte ptr [ctrl1_state_th0], FBh
    and byte ptr [ctrl1_state_th1], FBh
@@skip_gp_left:

    test ax, 0008h
    jz @@skip_gp_right
    and byte ptr [ctrl1_state_th0], F7h
    and byte ptr [ctrl1_state_th1], F7h
@@skip_gp_right:

    test ax, 1000h
    jz @@skip_gp_a
    and byte ptr [ctrl1_state_th1], EFh
@@skip_gp_a:

    test ax, 2000h
    jz @@skip_gp_b
    and byte ptr [ctrl1_state_th0], EFh
@@skip_gp_b:

    test ax, 4000h
    jz @@skip_gp_c
    and byte ptr [ctrl1_state_th0], DFh
@@skip_gp_c:

    test ax, 0010h
    jz @@skip_gp_start
    and byte ptr [ctrl1_state_th1], DFh
@@skip_gp_start:

@@no_gamepad:

    mov rsp, rbp
    pop rbp
    ret
poll_input ENDP

; ============================================
; read_io_byte - lê $A10000..$A1001F
;   entrada: ecx = offset
;   saída:   al
; ============================================
public read_io_byte
read_io_byte PROC
    and ecx, 1Fh
    cmp ecx, 01h
    je @@ver
    cmp ecx, 03h
    je @@ctrl1_data
    cmp ecx, 05h
    je @@ctrl2_data
    xor eax, eax
    ret

@@ver:
    ; version register: bit7=1, bit6=1 (PAL), bits0-3 versão
    mov al, 0A0h
    ret

@@ctrl1_data:
    mov al, [ctrl1_th]
    test al, al
    jz @@ctrl1_th0
    mov al, [ctrl1_state_th1]
    or al, 80h
    ret
@@ctrl1_th0:
    mov al, [ctrl1_state_th0]
    or al, 80h
    ret

@@ctrl2_data:
    mov al, [ctrl2_th]
    test al, al
    jz @@ctrl2_th0
    mov al, [ctrl2_state_th1]
    or al, 80h
    ret
@@ctrl2_th0:
    mov al, [ctrl2_state_th0]
    or al, 80h
    ret
read_io_byte ENDP

; ============================================
; write_io_byte - escreve $A10000..$A1001F
;   entrada: ecx = offset, dl = valor
; ============================================
public write_io_byte
write_io_byte PROC
    and ecx, 1Fh
    cmp ecx, 03h
    je @@ctrl1_write
    cmp ecx, 05h
    je @@ctrl2_write
    ret

@@ctrl1_write:
    test dl, 40h
    jz @@ctrl1_th0_set
    mov byte ptr [ctrl1_th], 1
    ret
@@ctrl1_th0_set:
    mov byte ptr [ctrl1_th], 0
    ret

@@ctrl2_write:
    test dl, 40h
    jz @@ctrl2_th0_set
    mov byte ptr [ctrl2_th], 1
    ret
@@ctrl2_th0_set:
    mov byte ptr [ctrl2_th], 0
    ret
write_io_byte ENDP
