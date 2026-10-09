; ==========================================
; input.inc - Controle Mega Drive
; ==========================================

.data

; Bitmask de botões PRESSIONADOS (1 = pressionado)
; bit 0 = Up, 1 = Down, 2 = Left, 3 = Right
; bit 4 = A,  5 = B,   6 = C,   7 = Start
public pad1_state
public pad2_state
pad1_state db 0
pad2_state db 0

public pad1_prev
public pad2_prev
pad1_prev db 0
pad2_prev db 0

; Último valor do TH (linha de seleção) por controle
; 0 = TH baixo, 1 = TH alto
public pad1_th
public pad2_th
pad1_th db 0
pad2_th db 0

; Versão do console (0x80 = export NTSC, 0x00 = Japan, 0xA0 = PAL)
VERSION_BYTE equ 080h

.code

; ==========================================
; update_input
;   Stub - preenche pad1_state / pad2_state
;   a partir do teclado ou gamepad do host.
;   Roda 1x por frame.
; ==========================================
public update_input
update_input PROC
    ; TODO: preencher com seu esquema
    ; bit 0 = Up, 1 = Down, 2 = Left, 3 = Right
    ; bit 4 = A,  5 = B,   6 = C,   7 = Start
    ; 1 = pressionado
    ret
update_input ENDP

; ==========================================
; read_io_byte
;   ecx = endereço (0xA10000..0xA1001F)
;   retorna eax = byte
; ==========================================
public read_io_byte
read_io_byte PROC
    mov eax, ecx
    and eax, 0FFh                 ; offset dentro da área de I/O
    cmp al, 00h
    je @@ver_hi
    cmp al, 01h
    je @@ver_lo
    cmp al, 03h
    je @@p1_data
    cmp al, 05h
    je @@p2_data
    cmp al, 09h
    je @@p1_ctrl
    cmp al, 0Bh
    je @@p2_ctrl
    ; endereço não mapeado
    xor eax, eax
    ret

; --- Version register (0xA10000/0xA10001) ---
@@ver_hi:
    xor eax, eax
    ret
@@ver_lo:
    mov eax, VERSION_BYTE
    ret

; --- Data port 1 ---
@@p1_data:
    movzx eax, byte ptr [pad1_state]
    mov cl, [pad1_th]
    test cl, cl
    jnz @@p1_th1
    ; TH=0: Up Down Left Right B C
    ; estado: 0-3 = UDLR, 5 = B, 6 = C
    mov edx, eax
    and edx, 00Fh                  ; UDLR
    mov ecx, eax
    and ecx, 060h                  ; B, C
    shr ecx, 1                     ; -> bits 4, 5
    or  edx, ecx
    mov eax, edx
    not eax
    and eax, 03Fh
    or  eax, 0C0h                  ; bits 6-7 = 1
    ret
@@p1_th1:
    ; TH=1: Up Down Left Right A Start
    ; estado: 0-3 = UDLR, 4 = A, 7 = Start
    mov edx, eax
    and edx, 00Fh                  ; UDLR
    mov ecx, eax
    and ecx, 010h                  ; A (bit 4)
    or  edx, ecx
    mov ecx, eax
    and ecx, 080h                  ; Start (bit 7)
    shr ecx, 2                     ; -> bit 5
    or  edx, ecx
    mov eax, edx
    not eax
    and eax, 03Fh
    or  eax, 0C0h
    ret

; --- Data port 2 (mesma lógica) ---
@@p2_data:
    movzx eax, byte ptr [pad2_state]
    mov cl, [pad2_th]
    test cl, cl
    jnz @@p2_th1
    mov edx, eax
    and edx, 00Fh
    mov ecx, eax
    and ecx, 060h
    shr ecx, 1
    or  edx, ecx
    mov eax, edx
    not eax
    and eax, 03Fh
    or  eax, 0C0h
    ret
@@p2_th1:
    mov edx, eax
    and edx, 00Fh
    mov ecx, eax
    and ecx, 010h
    or  edx, ecx
    mov ecx, eax
    and ecx, 080h
    shr ecx, 2
    or  edx, ecx
    mov eax, edx
    not eax
    and eax, 03Fh
    or  eax, 0C0h
    ret

; --- Control port 1 (retorna o último TH) ---
@@p1_ctrl:
    movzx eax, byte ptr [pad1_th]
    shl eax, 6
    or  eax, 0C0h
    ret

@@p2_ctrl:
    movzx eax, byte ptr [pad2_th]
    shl eax, 6
    or  eax, 0C0h
    ret
read_io_byte ENDP

; ==========================================
; write_io_byte
;   ecx = endereço, dl = valor
; ==========================================
public write_io_byte
write_io_byte PROC
    mov eax, ecx
    and eax, 0FFh
    cmp al, 09h
    je @@set_p1_th
    cmp al, 0Bh
    je @@set_p2_th
    ret

@@set_p1_th:
    mov eax, edx
    shr eax, 6                     ; bit 6 = TH
    and eax, 1
    mov [pad1_th], al
    ret

@@set_p2_th:
    mov eax, edx
    shr eax, 6
    and eax, 1
    mov [pad2_th], al
    ret
write_io_byte ENDP