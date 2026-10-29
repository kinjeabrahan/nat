from pathlib import Path
from .ir import validate

CTYPES = {'Int':'int64_t','Bool':'bool','Texto':'const char *'}

def cstring(value):
    return '"' + ''.join('\\%03o' % b for b in value.encode('utf-8')) + '"'

def generate(ir, path):
    validate(ir)
    names={f['name']:'nat_f'+str(i) for i,f in enumerate(ir['functions'])}
    def signature(f):
        params=', '.join(CTYPES[p['type']]+' '+p['id'] for p in f['params']) or 'void'
        return 'static '+CTYPES[f['return_type']]+' '+names[f['name']]+'('+params+')'
    lines=['static const char *nat_source = '+cstring(path)+';',
           Path(__file__).with_name('runtime.h').read_text()]
    lines.extend(signature(f)+';' for f in ir['functions'])
    for f in [*ir['functions'],ir['entry']]:
        main=f['return_type']=='Unidad';types=f['types'];params={p['id'] for p in f['params']}
        lines.append('int main(int argc, char **argv) {' if main else signature(f)+' {')
        if main:
            lines.extend(['nat_argc = argc; nat_argv = argv;'])
            lines.extend('(void)&'+name+';' for name in names.values())
        lines.append(f"nat_enter({f['line']}, {f['column']});")
        for name,typ in types.items():
            if name not in params: lines.append(CTYPES[typ]+' '+name+' = '+('""' if typ=='Texto' else '0')+';')
            lines.append('(void)'+name+';')
        for n in f['instructions']:
            op,d,a,t=(n[k] for k in ('op','dest','args','type'))
            loc=f"{n['line']}, {n['column']}"
            if op=='label':lines.append(d+': ;');continue
            if op=='jump':lines.append('goto '+a[0]+';');continue
            if op.startswith('branch_'):
                lines.append(f"if ({'!' if op=='branch_false' else ''}{a[0]}) goto {a[1]};");continue
            if op=='return':lines.extend(['nat_depth--;','return '+a[0]+';']);continue
            if op=='print':
                lines.append(f'printf("%" PRId64 "\\n", {a[0]});' if t=='Int' else
                             f'puts({a[0]});' if t=='Texto' else f'puts({a[0]} ? "verdadero" : "falso");')
                continue
            if op=='literal':
                value=a[0]
                rhs=(cstring(value) if t=='Texto' else 'true' if value is True else 'false' if value is False
                     else 'INT64_MIN' if value==-(2**63) else ('-' if value<0 else '')+f'INT64_C({abs(value)})')
            elif op=='copy':rhs=a[0]
            elif op=='call':
                if a[0]=='entrada_entero':rhs=f'nat_input(nat_argc, nat_argv, {loc})'
                elif a[0]=='leer_byte':rhs=f'nat_read_byte({loc})'
                else:rhs=names[a[0]]+'('+', '.join(a[1:])+')'
            elif op=='no':rhs='!'+a[0]
            elif op in ('+','-','*','%'):
                args=['INT64_C(0)',a[0]] if len(a)==1 else a
                rhs=f"nat_{ {'+':'add','-':'sub','*':'mul','%':'mod'}[op]}({args[0]}, {args[1]}, {loc})"
            elif op in ('==','!=') and types[a[0]]=='Texto':rhs=f'strcmp({a[0]}, {a[1]}) {op} 0'
            else:rhs=f'{a[0]} {op} {a[1]}'
            lines.append(d+' = '+rhs+';')
        if main:lines.extend(['if (fflush(stdout) == EOF || ferror(stdout)) nat_fail(1, 1, "Error de salida.");','nat_depth--;','return 0;'])
        else:lines.append('nat_fail(%d, %d, "IR sin retorno.");' % (f["line"], f["column"]))
        lines.append('}')
    return '\n'.join(lines)+'\n'
