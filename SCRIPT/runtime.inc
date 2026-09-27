; ==========================================
; MegaComp Runtime
; ==========================================

include input.inc

.const
RAM_BASE equ 0FF0000h
IO_BASE  equ 0A10000h

.data

; --- D0-D7 ---
public reg_D0
public reg_D1
public reg_D2
public reg_D3
public reg_D4
public reg_D5
public reg_D6
public reg_D7
reg_D0 dd 0
reg_D1 dd 0
reg_D2 dd 0
reg_D3 dd 0
reg_D4 dd 0
reg_D5 dd 0
reg_D6 dd 0
reg_D7 dd 0

; --- A0-A7 ---
public reg_A0
public reg_A1
public reg_A2
public reg_A3
public reg_A4
public reg_A5
public reg_A6
public reg_A7
reg_A0 dd 0
reg_A1 dd 0
reg_A2 dd 0
reg_A3 dd 0
reg_A4 dd 0
reg_A5 dd 0
reg_A6 dd 0
reg_A7 dd 0

; --- Flags 68000 ---
public flag_X
public flag_N
public flag_Z
public flag_V
public flag_C
flag_X db 0
flag_N db 0
flag_Z db 0
flag_V db 0
flag_C db 0

; --- RAM ---
public md_ram
md_ram db 65536 dup(0)

; --- ROM (definida pelo codegen) ---
extern rom_data:byte
extern rom_size:qword

.code

; ==========================================
; Memória
; ==========================================

public read_byte
read_byte PROC
    mov rax, rcx
    and rax, 0FFFFFFh
    cmp rax, IO_BASE
    jb @@not_io
    cmp rax, IO_BASE + 20h
    jae @@not_io
    push rcx
    mov ecx, eax
    call read_io_byte
    pop rcx
    ret
@@not_io:
    cmp rax, RAM_BASE
    jae @@ram
    lea rdx, rom_data
    movzx eax, byte ptr [rdx + rax]
    ret
@@ram:
    sub rax, RAM_BASE
    lea rdx, md_ram
    movzx eax, byte ptr [rdx + rax]
    ret
read_byte ENDP

public read_word
read_word PROC
    push rbx
    push r12
    mov rbx, rcx
    call read_byte
    mov r12d, eax
    lea rcx, [rbx + 1]
    call read_byte
    shl r12d, 8
    movzx eax, al
    or eax, r12d
    pop r12
    pop rbx
    ret
read_word ENDP

public read_long
read_long PROC
    push rbx
    push r12
    mov rbx, rcx
    call read_word
    mov r12d, eax
    lea rcx, [rbx + 2]
    call read_word
    shl r12d, 16
    movzx eax, ax
    or eax, r12d
    pop r12
    pop rbx
    ret
read_long ENDP

public write_byte
write_byte PROC
    mov rax, rcx
    and rax, 0FFFFFFh
    cmp rax, IO_BASE
    jb @@not_io
    cmp rax, IO_BASE + 20h
    jae @@not_io
    push rcx
    mov ecx, eax
    call write_io_byte
    pop rcx
    ret
@@not_io:
    cmp rax, RAM_BASE
    jb @@done
    sub rax, RAM_BASE
    lea r8, md_ram
    mov byte ptr [r8 + rax], dl
@@done:
    ret
write_byte ENDP

public write_word
write_word PROC
    push rbx
    push r12
    mov rbx, rcx
    mov r12w, dx
    mov edx, r12d
    shr edx, 8
    call write_byte
    lea rcx, [rbx + 1]
    movzx edx, r12w
    and edx, 0FFh
    call write_byte
    pop r12
    pop rbx
    ret
write_word ENDP

public write_long
write_long PROC
    push rbx
    push r12
    mov rbx, rcx
    mov r12d, edx
    mov edx, r12d
    shr edx, 16
    call write_word
    lea rcx, [rbx + 2]
    movzx edx, r12w
    call write_word
    pop r12
    pop rbx
    ret
write_long ENDP

; ==========================================
; Stack 68000 (push/pop usam reg_A7)
; ==========================================

public push_long_68k
push_long_68k PROC
    ; edx = valor
    mov eax, [reg_A7]
    sub eax, 4
    mov [reg_A7], eax
    mov ecx, eax
    call write_long
    ret
push_long_68k ENDP

public pop_long_68k
pop_long_68k PROC
    ; retorna em eax
    mov ecx, [reg_A7]
    call read_long
    mov ecx, [reg_A7]
    add ecx, 4
    mov [reg_A7], ecx
    ret
pop_long_68k ENDP

; ==========================================
; Helpers de flags
; ==========================================

; build_flags_add
;   esi = operando A (já mascarado ao tamanho)
;   edi = operando B (já mascarado ao tamanho)
;   eax = resultado (já mascarado ao tamanho)
;   r8b = 'B' | 'W' | 'L'
; Preserva eax
public build_flags_add
build_flags_add PROC
    push rbx
    push rcx
    push rdx

    test eax, eax
    setz byte ptr [flag_Z]

    mov ebx, eax
    cmp r8b, 'B'
    jne @@n_w
    shl ebx, 24
    jmp @@n_done
@@n_w:
    cmp r8b, 'W'
    jne @@n_done
    shl ebx, 16
@@n_done:
    shr ebx, 31
    mov [flag_N], bl

    mov ebx, esi
    add ebx, edi
    cmp r8b, 'B'
    jne @@c_w
    cmp ebx, 100h
    setae byte ptr [flag_C]
    jmp @@c_done
@@c_w:
    cmp r8b, 'W'
    jne @@c_l
    cmp ebx, 10000h
    setae byte ptr [flag_C]
    jmp @@c_done
@@c_l:
    cmp ebx, esi
    setb byte ptr [flag_C]
@@c_done:

    mov ebx, esi
    xor ebx, eax
    mov ecx, edi
    xor ecx, eax
    and ebx, ecx
    cmp r8b, 'B'
    jne @@v_w
    shl ebx, 24
    jmp @@v_done
@@v_w:
    cmp r8b, 'W'
    jne @@v_done
    shl ebx, 16
@@v_done:
    shr ebx, 31
    mov [flag_V], bl

    mov bl, [flag_C]
    mov [flag_X], bl

    pop rdx
    pop rcx
    pop rbx
    ret
build_flags_add ENDP

; build_flags_sub
;   esi = A, edi = B, eax = R = A - B
public build_flags_sub
build_flags_sub PROC
    push rbx
    push rcx
    push rdx

    test eax, eax
    setz byte ptr [flag_Z]

    mov ebx, eax
    cmp r8b, 'B'
    jne @@n_w
    shl ebx, 24
    jmp @@n_done
@@n_w:
    cmp r8b, 'W'
    jne @@n_done
    shl ebx, 16
@@n_done:
    shr ebx, 31
    mov [flag_N], bl

    ; C = borrow: A < B (unsigned, no tamanho)
    cmp esi, edi
    setb byte ptr [flag_C]

    ; V = (A^B) & (A^R) no MSB do tamanho
    mov ebx, esi
    xor ebx, edi
    mov ecx, esi
    xor ecx, eax
    and ebx, ecx
    cmp r8b, 'B'
    jne @@v_w
    shl ebx, 24
    jmp @@v_done
@@v_w:
    cmp r8b, 'W'
    jne @@v_done
    shl ebx, 16
@@v_done:
    shr ebx, 31
    mov [flag_V], bl

    mov bl, [flag_C]
    mov [flag_X], bl

    pop rdx
    pop rcx
    pop rbx
    ret
build_flags_sub ENDP

; build_flags_logic - após AND/OR/EOR
;   eax = resultado mascarado
public build_flags_logic
build_flags_logic PROC
    test eax, eax
    setz byte ptr [flag_Z]
    mov ecx, eax
    shr ecx, 31
    mov [flag_N], cl
    mov byte ptr [flag_V], 0
    mov byte ptr [flag_C], 0
    ret
build_flags_logic ENDP

; build_flags_move - após MOVE
;   eax = valor mascarado
public build_flags_move
build_flags_move PROC
    test eax, eax
    setz byte ptr [flag_Z]
    mov ecx, eax
    shr ecx, 31
    mov [flag_N], cl
    mov byte ptr [flag_V], 0
    mov byte ptr [flag_C], 0
    ret
build_flags_move ENDP

public build_flags_clr
build_flags_clr PROC
    mov byte ptr [flag_Z], 1
    mov byte ptr [flag_N], 0
    mov byte ptr [flag_V], 0
    mov byte ptr [flag_C], 0
    ret
build_flags_clr ENDP