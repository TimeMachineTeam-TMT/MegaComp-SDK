; ==========================================
; window.inc - Win32 window + framebuffer + backdrop renderer
; ==========================================

EXTERN ExitProcess:PROC
EXTERN GetModuleHandleA:PROC
EXTERN RegisterClassExA:PROC
EXTERN CreateWindowExA:PROC
EXTERN ShowWindow:PROC
EXTERN UpdateWindow:PROC
EXTERN GetMessageA:PROC
EXTERN TranslateMessage:PROC
EXTERN DispatchMessageA:PROC
EXTERN DefWindowProcA:PROC
EXTERN PostQuitMessage:PROC
EXTERN GetDC:PROC
EXTERN ReleaseDC:PROC
EXTERN StretchDIBits:PROC
EXTERN ValidateRect:PROC

.const
SW_SHOW            equ 5
WS_OVERLAPPEDWINDOW equ 00CF0000h
CW_USEDEFAULT      equ 80000000h
WM_DESTROY         equ 2
WM_PAINT           equ 0Fh
DIB_RGB_COLORS     equ 0
BI_RGB             equ 0
SRCCOPY            equ 00CC0020h
MD_W               equ 320
MD_H               equ 224
FB_SIZE            equ MD_W * MD_H * 4

.data
public fb_pixels
fb_pixels      db FB_SIZE dup(0)
wnd_class      db 80 dup(0)
wnd_msg_buf    db 64 dup(0)
bmi            db 40 dup(0)
wnd_classname  db "MegaCompWnd", 0
wnd_title      db "MegaComp", 0
hInstance_mc   dq 0
hwnd_mc        dq 0

.code

; ==========================================
; mc_render_backdrop - preenche fb com cor do backdrop
; ==========================================
public mc_render_backdrop
mc_render_backdrop PROC
    movzx eax, byte ptr [vdp_regs + 7]
    and eax, 03Fh
    lea r8, vdp_cram
    movzx eax, word ptr [r8 + rax*2]

    ; MD: 0BBB0GGG0RRR0 -> 0x00RRGGBB
    mov r9d, eax
    shr r9d, 1
    and r9d, 7
    imul r9d, 36
    shl r9d, 16

    mov r10d, eax
    shr r10d, 5
    and r10d, 7
    imul r10d, 36
    shl r10d, 8

    mov r11d, eax
    shr r11d, 9
    and r11d, 7
    imul r11d, 36

    or r9d, r10d
    or r9d, r11d

    lea rdi, fb_pixels
    mov edx, r9d
    mov ecx, MD_W * MD_H
@@fill:
    mov dword ptr [rdi], edx
    add rdi, 4
    dec ecx
    jnz @@fill
    ret
mc_render_backdrop ENDP

; ==========================================
; mc_blit - framebuffer -> janela
; ==========================================
public mc_blit
mc_blit PROC
    push rbx
    push r12

    mov rcx, [hwnd_mc]
    call GetDC
    mov r12, rax

    lea rbx, bmi
    mov dword ptr [rbx + 0], 40
    mov dword ptr [rbx + 4], MD_W
    mov dword ptr [rbx + 8], -MD_H
    mov word ptr  [rbx + 12], 1
    mov word ptr  [rbx + 14], 32
    mov dword ptr [rbx + 16], 0
    mov dword ptr [rbx + 20], FB_SIZE
    mov dword ptr [rbx + 24], 0
    mov dword ptr [rbx + 28], 0
    mov dword ptr [rbx + 32], 0
    mov dword ptr [rbx + 36], 0

    sub rsp, 104
    mov dword ptr [rsp + 20h], MD_H
    mov qword ptr [rsp + 28h], 0
    mov qword ptr [rsp + 30h], 0
    mov dword ptr [rsp + 38h], MD_W
    mov dword ptr [rsp + 40h], MD_H
    lea rax, fb_pixels
    mov [rsp + 48h], rax
    lea rax, bmi
    mov [rsp + 50h], rax
    mov dword ptr [rsp + 58h], DIB_RGB_COLORS
    mov dword ptr [rsp + 60h], SRCCOPY

    mov rcx, r12
    xor edx, edx
    xor r8d, r8d
    mov r9d, MD_W
    call StretchDIBits
    add rsp, 104

    mov rcx, [hwnd_mc]
    mov rdx, r12
    call ReleaseDC

    pop r12
    pop rbx
    ret
mc_blit ENDP

; ==========================================
; mc_wndproc
; ==========================================
public mc_wndproc
mc_wndproc PROC
    push rbx
    mov rbx, rdx
    cmp edx, WM_PAINT
    je @@paint
    cmp edx, WM_DESTROY
    je @@destroy
    call DefWindowProcA
    pop rbx
    ret
@@paint:
    call mc_blit
    mov rcx, [hwnd_mc]
    xor edx, edx
    call ValidateRect
    xor eax, eax
    pop rbx
    ret
@@destroy:
    xor ecx, ecx
    call PostQuitMessage
    xor eax, eax
    pop rbx
    ret
mc_wndproc ENDP

; ==========================================
; mc_create_window
; ==========================================
public mc_create_window
mc_create_window PROC
    push rbx

    xor ecx, ecx
    call GetModuleHandleA
    mov [hInstance_mc], rax

    lea rbx, wnd_class
    mov dword ptr [rbx + 0], 80
    mov dword ptr [rbx + 4], 3
    lea rax, mc_wndproc
    mov [rbx + 8], rax
    mov dword ptr [rbx + 16], 0
    mov dword ptr [rbx + 20], 0
    mov rax, [hInstance_mc]
    mov [rbx + 24], rax
    mov qword ptr [rbx + 32], 0
    mov qword ptr [rbx + 40], 0
    mov qword ptr [rbx + 48], 6
    mov qword ptr [rbx + 56], 0
    lea rax, wnd_classname
    mov [rbx + 64], rax
    mov qword ptr [rbx + 72], 0

    lea rcx, wnd_class
    call RegisterClassExA

    sub rsp, 80
    mov dword ptr [rsp + 20h], CW_USEDEFAULT
    mov dword ptr [rsp + 28h], CW_USEDEFAULT
    mov dword ptr [rsp + 30h], 340
    mov dword ptr [rsp + 38h], 264
    mov qword ptr [rsp + 40h], 0
    mov qword ptr [rsp + 48h], 0
    mov rax, [hInstance_mc]
    mov [rsp + 50h], rax
    mov qword ptr [rsp + 58h], 0
    xor ecx, ecx
    lea rdx, wnd_classname
    lea r8, wnd_title
    mov r9d, WS_OVERLAPPEDWINDOW
    call CreateWindowExA
    add rsp, 80
    mov [hwnd_mc], rax

    mov rcx, rax
    mov edx, SW_SHOW
    call ShowWindow

    mov rcx, [hwnd_mc]
    call UpdateWindow

    pop rbx
    ret
mc_create_window ENDP

; ==========================================
; mc_message_loop
; ==========================================
public mc_message_loop
mc_message_loop PROC
@@loop:
    lea rcx, wnd_msg_buf
    xor edx, edx
    xor r8d, r8d
    xor r9d, r9d
    call GetMessageA
    test eax, eax
    jle @@done

    lea rcx, wnd_msg_buf
    call TranslateMessage

    lea rcx, wnd_msg_buf
    call DispatchMessageA
    jmp @@loop
@@done:
    ret
mc_message_loop ENDP