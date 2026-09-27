; ==========================================
; input.inc - stubs de I/O para teste
; ==========================================

EXTERN ExitProcess:PROC

.data
; mapa de botões (só placeholder por enquanto)
public pad_state
pad_state dd 0

.code

public read_io_byte
read_io_byte PROC
    ; ecx = endereço (dentro de IO_BASE)
    xor eax, eax
    ret
read_io_byte ENDP

public write_io_byte
write_io_byte PROC
    ; ecx = endereço, dl = valor
    ret
write_io_byte ENDP