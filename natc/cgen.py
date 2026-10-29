from pathlib import Path

def cstring(value):
    return '"' + ''.join('\\%03o' % b for b in value.encode('utf-8')) + '"'

def generate(ir, path):
    types = ir['types']
    ctypes = {'Int':'int64_t','Bool':'bool','Texto':'const char *'}
    lines = ['static const char *nat_source = '+cstring(path)+';',
             Path(__file__).with_name('runtime.h').read_text(),
             'int main(int argc, char **argv) {', '(void)argc; (void)argv;']
    for name, typ in types.items():
        lines.append(f'{ctypes[typ]} {name} = '+('""' if typ=='Texto' else '0')+';')
    for ins in ir['instructions']:
        op,d,a,t = (ins[k] for k in ('op','dest','args','type'))
        loc = f"{ins['line']}, {ins['column']}"
        if op == 'label': lines.append(d+': ;'); continue
        if op == 'jump': lines.append('goto '+a[0]+';'); continue
        if op.startswith('branch_'):
            lines.append(f"if ({'!' if op=='branch_false' else ''}{a[0]}) goto {a[1]};"); continue
        if op == 'print':
            lines.append(f'printf("%" PRId64 "\\n", {a[0]});' if t=='Int' else
                         f'puts({a[0]});' if t=='Texto' else
                         f'puts({a[0]} ? "verdadero" : "falso");')
            continue
        if op == 'literal':
            value = a[0]
            rhs = (cstring(value) if t=='Texto' else 'true' if value is True else 'false' if value is False
                   else 'INT64_MIN' if value==-(2**63) else
                   ('-' if value<0 else '')+f'INT64_C({abs(value)})')
        elif op == 'call': rhs = f'nat_input(argc, argv, {loc})'
        elif op == 'copy': rhs = a[0]
        elif op == 'no': rhs = '!'+a[0]
        elif op in ('+','-','*','%'):
            args = ['INT64_C(0)',a[0]] if len(a)==1 else a
            rhs = f"nat_{ {'+':'add','-':'sub','*':'mul','%':'mod'}[op]}({args[0]}, {args[1]}, {loc})"
        elif op in ('==','!=') and types[a[0]]=='Texto':
            rhs = f'strcmp({a[0]}, {a[1]}) {op} 0'
        else: rhs = f'{a[0]} {op} {a[1]}'
        lines.append(f'{d} = {rhs};')
    lines.extend(f'(void){name};' for name in types)
    lines.extend(['return 0;', '}'])
    return '\n'.join(lines)+'\n'
