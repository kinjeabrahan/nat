"""IR v2 -> Linux x86-64 GNU assembly, System V integer/pointer convention.

Values spill into per-activation stack slots. No user value survives a call
only in a caller-saved register. Frames are multiples of 16 bytes; the entry
push of rbp aligns rsp before every call. No C, libc, globals capturing locals,
register allocator, heap or FFI. Six word-sized parameters maximum.
"""
from pathlib import Path
from .ir import validate

REGISTERS = ('%rdi','%rsi','%rdx','%rcx','%r8','%r9')

def generate(program, path):
    validate(program)
    functions=[*program['functions'],program['entry']]
    names={f['name']:'.N_function_'+str(i) for i,f in enumerate(functions)}
    pool=[]; errors=[]; out=[]
    def emit(*lines):out.extend(lines)
    def string(value):
        data=value.encode('utf-8') if isinstance(value,str) else value
        label='.N_string_'+str(len(pool));pool.append((label,data));return label
    def diag(line,col,message):
        text=f'{path}:{line}:{col}: {message}\n'.encode('utf-8')
        return string(text),len(text)
    def fail(line,col,message):
        label='.N_error_'+str(len(errors));data,size=diag(line,col,message)
        errors.append((label,data,size));return label
    true,false=string('verdadero'),string('falso')
    emit('.section .text','.global _start','_start:','mov %rsp, %r12',
         'call '+names[program['entry']['name']],'mov %rax, %rdi','mov $60, %eax','syscall')
    for fn_index,f in enumerate(functions):
        types=f['types'];slots={name:8*(i+1) for i,name in enumerate(types)}
        frame=((len(slots)*8+15)//16)*16
        def mem(name):return f'-{slots[name]}(%rbp)'
        def label(name):return f'.N_f{fn_index}_{name}'
        end=f'.N_return_{fn_index}'
        depth=fail(f['line'],f['column'],'Limite de llamadas alcanzado (128).')
        emit(names[f['name']]+':','addq $1, .N_depth(%rip)','cmpq $128, .N_depth(%rip)',
             'ja '+depth,'push %rbp','mov %rsp, %rbp',f'sub ${frame}, %rsp')
        for param,register in zip(f['params'],REGISTERS):emit(f'mov {register}, {mem(param["id"])}')
        for index,n in enumerate(f['instructions']):
            op,d,a,t=(n[k] for k in ('op','dest','args','type'))
            if op=='label':emit(label(d)+':');continue
            if op=='jump':emit('jmp '+label(a[0]));continue
            if op.startswith('branch_'):
                emit(f'cmpq $0, {mem(a[0])}',('je ' if op=='branch_false' else 'jne ')+label(a[1]));continue
            if op=='return':emit(f'mov {mem(a[0])}, %rax','jmp '+end);continue
            if op=='print':
                emit(f'mov {mem(a[0])}, %rax')
                if t=='Int':emit('call .N_print_int')
                elif t=='Texto':emit('call .N_print_text')
                else:emit('test %rax, %rax',f'lea {false}(%rip), %rax',f'lea {true}(%rip), %rdx','cmovne %rdx, %rax','call .N_print_text')
                continue
            if op=='literal':
                if t=='Texto':emit('lea '+string(a[0])+'(%rip), %rax')
                else:emit(f'movabs ${int(a[0])}, %rax')
            elif op=='copy':emit(f'mov {mem(a[0])}, %rax')
            elif op=='call':
                if a[0] in ('entrada_entero','leer_byte'):
                    text,size=diag(n['line'],n['column'],'Entrada decimal Int64 no valida.' if a[0]=='entrada_entero' else 'Error de lectura de entrada.')
                    emit(f'lea {text}(%rip), %r8',f'mov ${size}, %r9',
                         'call '+('.N_input_int' if a[0]=='entrada_entero' else '.N_read_byte'))
                else:
                    for value,register in zip(a[1:],REGISTERS):emit(f'mov {mem(value)}, {register}')
                    emit('call '+names[a[0]])
            elif op=='no':emit(f'cmpq $0, {mem(a[0])}','sete %al','movzbq %al, %rax')
            elif op in ('+','-','*'):
                error=fail(n['line'],n['column'],'Desbordamiento Int64.')
                if len(a)==1:emit('xor %eax, %eax',f'sub {mem(a[0])}, %rax')
                else:emit(f'mov {mem(a[0])}, %rax',f"{ {'+':'add','-':'sub','*':'imul'}[op]} {mem(a[1])}, %rax")
                emit('jo '+error)
            elif op=='%':
                error=fail(n['line'],n['column'],'Resto por cero.')
                normal=label('mod_'+str(index));done=normal+'_done'
                emit(f'mov {mem(a[0])}, %rax',f'mov {mem(a[1])}, %r10','test %r10, %r10','jz '+error,
                     'movabs $0x8000000000000000, %rcx','cmp %rcx, %rax','jne '+normal,
                     'cmp $-1, %r10','jne '+normal,'xor %eax, %eax','jmp '+done,normal+':',
                     'cqto','idiv %r10','mov %rdx, %rax',done+':')
            elif op in ('==','!=','<','<=','>','>='):
                if types[a[0]]=='Texto':emit(f'mov {mem(a[0])}, %rdi',f'mov {mem(a[1])}, %rsi','call .N_strcmp','test %eax, %eax')
                else:emit(f'mov {mem(a[0])}, %rax',f'cmp {mem(a[1])}, %rax')
                cc={'==':'e','!=':'ne','<':'l','<=':'le','>':'g','>=':'ge'}[op]
                emit('set'+cc+' %al','movzbq %al, %rax')
            else:raise ValueError('IR opcode no implementado: '+op)
            emit(f'mov %rax, {mem(d)}')
        if f['return_type']=='Unidad':emit('xor %eax, %eax')
        else:emit('ud2') # A validated non-void CFG cannot reach this fallthrough.
        emit(end+':','subq $1, .N_depth(%rip)','leave','ret')
    for label,data,size in errors:emit(label+':',f'lea {data}(%rip), %rsi',f'mov ${size}, %rdx','jmp .N_fail')
    emit('.section .rodata')
    for label,data in pool:emit(label+':','.byte '+','.join(str(b) for b in data+b'\0'))
    emit(Path(__file__).with_name('asm_runtime.s').read_text())
    return '\n'.join(out)+'\n'
