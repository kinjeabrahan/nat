# Linux x86-64 runtime. All callable helpers preserve SysV callee-saved regs.
# r12 is process-entry stack context, set once by _start and never modified here.
.section .bss
.balign 8
.N_depth: .skip 8
.N_byte: .skip 1
.N_number: .skip 32
.section .rodata
.N_newline: .byte 10
.N_output_error: .ascii "Error de salida.\n"
.set .N_output_error_len, . - .N_output_error
.section .text
.N_write:
    test %rdx, %rdx
    jz .N_write_done
.N_write_loop:
    mov $1, %eax
    mov $1, %edi
    syscall
    cmp $-4, %rax
    je .N_write_loop
    test %rax, %rax
    jle .N_output_failed
    add %rax, %rsi
    sub %rax, %rdx
    jnz .N_write_loop
.N_write_done:
    ret
.N_output_failed:
    lea .N_output_error(%rip), %rsi
    mov $.N_output_error_len, %edx
    jmp .N_fail
.N_fail:
    mov $1, %eax
    mov $2, %edi
    syscall
    mov $60, %eax
    mov $1, %edi
    syscall
.N_print_int:
    lea .N_number+32(%rip), %rsi
    dec %rsi
    movb $10, (%rsi)
    mov $1, %r8d
    xor %r9d, %r9d
    test %rax, %rax
    jns .N_digits
    mov $1, %r9d
    neg %rax
.N_digits:
    mov $10, %r10d
.N_digit_loop:
    xor %edx, %edx
    div %r10
    add $48, %dl
    dec %rsi
    mov %dl, (%rsi)
    inc %r8
    test %rax, %rax
    jnz .N_digit_loop
    test %r9, %r9
    jz .N_digits_done
    dec %rsi
    movb $45, (%rsi)
    inc %r8
.N_digits_done:
    mov %r8, %rdx
    jmp .N_write
.N_print_text:
    mov %rax, %rsi
    xor %edx, %edx
.N_text_length:
    cmpb $0, (%rsi,%rdx)
    je .N_text_write
    inc %rdx
    jmp .N_text_length
.N_text_write:
    sub $8, %rsp
    call .N_write
    add $8, %rsp
    lea .N_newline(%rip), %rsi
    mov $1, %edx
    jmp .N_write
.N_strcmp:
    movzbl (%rdi), %eax
    movzbl (%rsi), %edx
    cmp %edx, %eax
    jne .N_strcmp_end
    test %eax, %eax
    jz .N_strcmp_end
    inc %rdi
    inc %rsi
    jmp .N_strcmp
.N_strcmp_end:
    sub %edx, %eax
    ret
.N_read_byte:
    xor %eax, %eax
    xor %edi, %edi
    lea .N_byte(%rip), %rsi
    mov $1, %edx
    syscall
    cmp $-4, %rax
    je .N_read_byte
    test %rax, %rax
    js .N_input_fail
    jz .N_eof
    movzbl .N_byte(%rip), %eax
    ret
.N_eof:
    mov $-1, %rax
    ret
.N_input_fail:
    mov %r8, %rsi
    mov %r9, %rdx
    jmp .N_fail
.N_input_int:
    cmpq $2, (%r12)
    jne .N_input_fail
    mov 16(%r12), %rsi
    xor %edi, %edi
    movabs $0x7fffffffffffffff, %r10
    cmpb $45, (%rsi)
    jne .N_input_first
    inc %rsi
    mov $1, %edi
    movabs $0x8000000000000000, %r10
.N_input_first:
    cmpb $0, (%rsi)
    je .N_input_fail
    xor %eax, %eax
    mov $10, %r11d
.N_input_loop:
    movzbl (%rsi), %ecx
    test %ecx, %ecx
    jz .N_input_done
    sub $48, %ecx
    cmp $9, %ecx
    ja .N_input_fail
    mul %r11
    test %rdx, %rdx
    jnz .N_input_fail
    add %rcx, %rax
    jc .N_input_fail
    cmp %r10, %rax
    ja .N_input_fail
    inc %rsi
    jmp .N_input_loop
.N_input_done:
    test %edi, %edi
    jz .N_input_return
    neg %rax
.N_input_return:
    ret
.section .note.GNU-stack,"",@progbits
