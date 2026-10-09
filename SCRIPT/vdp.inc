; ==========================================================
; vdp.inc - VDP do Mega Drive
; ==========================================================

.const
VDP_BASE        equ 0C00000h
VDP_DATA        equ 0C00000h
VDP_CTRL        equ 0C00004h
VDP_HV          equ 0C00008h
VDP_PSG         equ 0C00011h

VDP_VRAM_SIZE   equ 10000h
VDP_CRAM_SIZE   equ 80h
VDP_VSRAM_SIZE  equ 50h

; CD codes (bits 15-14 do primeiro half do address write)
VDP_CD_VRAM_RD  equ 0
VDP_CD_VRAM_WR  equ 1
VDP_CD_CRAM_WR  equ 2
VDP_CD_VSRAM_WR equ 3

.data

public vdp_vram
public vdp_cram
public vdp_vsram
public vdp_regs
public vdp_status
public vdp_addr
public vdp_code
public vdp_frame

vdp_vram    db VDP_VRAM_SIZE  dup(0)
vdp_cram    db VDP_CRAM_SIZE  dup(0)
vdp_vsram   db VDP_VSRAM_SIZE dup(0)
vdp_regs    db 24 dup(0)

; Status: bit 3 = VBlank, bit 9 = FIFO empty
vdp_status  dw 0000h

; Address register: 17 bits
vdp_addr    dd 0

; CD code (0..3)
vdp_code    db 0

; Latch para endereço em duas metades
vdp_addr_lo_written db 0

vdp_frame   dd 0

.code

; ==========================================================
; vdp_write_ctrl  - edx = word escrito em $C00004
; ==========================================================
public vdp_write_ctrl
vdp_write_ctrl PROC
    movzx eax, dx

    ; Register write? bits 15-13 = 100
    mov ecx, eax
    shr ecx, 13
    cmp ecx, 4
    jne @@addr_write

    ; reg num = bits 12-8, value = bits 7-0
    mov ecx, eax
    shr ecx, 8
    and ecx, 01Fh
    cmp ecx, 24
    jae @@done
    lea r8, vdp_regs
    mov byte ptr [r8 + rcx], al
    ret

@@addr_write:
    cmp byte ptr [vdp_addr_lo_written], 0
    jne @@second_half

    ; Primeiro half: CD (bits 15-14) + addr low 14 bits
    mov ecx, eax
    shr ecx, 14
    and ecx, 3
    mov byte ptr [vdp_code], cl
    and eax, 03FFFh
    mov [vdp_addr], eax
    mov byte ptr [vdp_addr_lo_written], 1
    ret

@@second_half:
    ; Segundo half: bits 2-0 = addr high
    and eax, 7
    shl eax, 14
    mov ecx, [vdp_addr]
    and ecx, 03FFFh
    or  eax, ecx
    mov [vdp_addr], eax
    mov byte ptr [vdp_addr_lo_written], 0
    ret

@@done:
    ret
vdp_write_ctrl ENDP

; ==========================================================
; vdp_write_data  - edx = word escrito em $C00000
; ==========================================================
public vdp_write_data
vdp_write_data PROC
    push rbx
    push r12

    mov r12d, edx                   ; valor
    mov ebx, [vdp_addr]             ; endereço

    movzx eax, byte ptr [vdp_code]
    cmp eax, VDP_CD_VRAM_WR
    je  @@vram
    cmp eax, VDP_CD_CRAM_WR
    je  @@cram
    cmp eax, VDP_CD_VSRAM_WR
    je  @@vsram
    jmp @@advance                  ; VRAM read: ignora escrita

@@vram:
    and ebx, 0FFFFh
    lea r8, vdp_vram
    mov word ptr [r8 + rbx], r12w
    jmp @@advance

@@cram:
    and ebx, 07Eh                  ; CRAM tem 64 entradas de 2 bytes
    lea r8, vdp_cram
    mov word ptr [r8 + rbx], r12w
    jmp @@advance

@@vsram:
    and ebx, 07Eh
    lea r8, vdp_vsram
    mov word ptr [r8 + rbx], r12w
    jmp @@advance

@@advance:
    ; Auto-increment = reg 15
    movzx eax, byte ptr [vdp_regs + 15]
    add [vdp_addr], eax
    and dword ptr [vdp_addr], 1FFFFh

    pop r12
    pop rbx
    ret
vdp_write_data ENDP

; ==========================================================
; vdp_read_data  - retorna word de $C00000
; ==========================================================
public vdp_read_data
vdp_read_data PROC
    push rbx
    mov ebx, [vdp_addr]
    and ebx, 0FFFFh
    lea r8, vdp_vram
    movzx eax, word ptr [r8 + rbx]

    movzx ecx, byte ptr [vdp_regs + 15]
    add [vdp_addr], ecx
    and dword ptr [vdp_addr], 1FFFFh

    pop rbx
    ret
vdp_read_data ENDP

; ==========================================================
; vdp_read_ctrl  - retorna status em $C00004
; ==========================================================
public vdp_read_ctrl
vdp_read_ctrl PROC
    movzx eax, word ptr [vdp_status]
    ret
vdp_read_ctrl ENDP

; ==========================================================
; vdp_read_hv  - retorna HV counter em $C00008
; ==========================================================
public vdp_read_hv
vdp_read_hv PROC
    ; Devolve 0 por enquanto; adicione timing real depois
    xor eax, eax
    ret
vdp_read_hv ENDP

; ==========================================================
; vdp_begin_frame / vdp_end_frame - chamados pelo loop externo
; ==========================================================
public vdp_begin_frame
vdp_begin_frame PROC
    ; Seta VBlank no status (bit 3)
    or  word ptr [vdp_status], 0008h
    inc dword ptr [vdp_frame]
    ret
vdp_begin_frame ENDP

public vdp_end_frame
vdp_end_frame PROC
    ; Limpa VBlank
    and word ptr [vdp_status], 0FFF7h
    ret
vdp_end_frame ENDP