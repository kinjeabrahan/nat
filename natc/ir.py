"""Version 2: typed functions, lexical binding IDs, three-address code and CFG."""
from dataclasses import dataclass, asdict
from .sema import BUILTINS, TYPES
import re

@dataclass
class Instruction:
    op: str
    dest: str
    args: list
    type: str
    line: int
    column: int

class FunctionLower:
    def __init__(self, function):
        self.function = function
        self.code = []
        self.types = {b.id:b.type for b in function.locals}
        self.counter = 0
    def fresh(self, prefix='t'):
        self.counter += 1
        return prefix+str(self.counter)
    def emit(self, op, dest, args, typ, token):
        self.code.append(Instruction(op,dest,args,typ,token.line,token.column))
    def expr(self,n):
        if n.op == 'name': args, op = [n.binding], 'copy'
        elif n.op == 'literal': args, op = [n.value], n.op
        elif n.op == 'call': args, op = [n.value]+[self.expr(a) for a in n.args], 'call'
        elif n.op in ('y','o'):
            left = self.expr(n.args[0]); dest = self.fresh(); end = self.fresh('L')
            self.types[dest] = 'Bool'
            self.emit('copy',dest,[left],'Bool',n.token)
            self.emit('branch_false' if n.op=='y' else 'branch_true','',[left,end],'',n.token)
            right = self.expr(n.args[1]); self.emit('copy',dest,[right],'Bool',n.token)
            self.emit('label',end,[],'',n.token)
            return dest
        else: args, op = [self.expr(x) for x in n.args], n.op
        dest = self.fresh(); self.types[dest] = n.type
        self.emit(op,dest,args,n.type,n.token)
        return dest
    def block(self, body):
        for n in body:
            if n.op == 'assign':
                value = self.expr(n.args[0]); self.emit('copy',n.binding,[value],n.type,n.token)
            elif n.op in ('print','return'):
                value = self.expr(n.args[0]); self.emit(n.op,'',[value],n.args[0].type,n.token)
            else:
                start, alternate, end = self.fresh('L'), self.fresh('L'), self.fresh('L')
                if n.op == 'mientras': self.emit('label',start,[],'',n.token)
                condition = self.expr(n.args[0]); self.emit('branch_false','',[condition,alternate],'',n.token)
                self.block(n.args[1])
                if n.op == 'mientras': self.emit('jump','',[start],'',n.token)
                elif len(n.args)==3: self.emit('jump','',[end],'',n.token)
                self.emit('label',alternate,[],'',n.token)
                if len(n.args)==3:
                    self.block(n.args[2]); self.emit('label',end,[],'',n.token)
    def lower(self):
        self.block(self.function.body)
        if len(self.types)>512:
            from .model import Error
            raise Error(self.function.token, "Marco demasiado grande (maximo 512 valores).")
        return {'name':self.function.name,'params':[{'id':p.id,'type':p.type} for p in self.function.params],
                'return_type':self.function.return_type,'types':self.types,
                'line':self.function.token.line,'column':self.function.token.column,
                'instructions':[asdict(i) for i in self.code]}

class Lower:
    def __init__(self, program): self.program = program
    def lower(self):
        result = {'version':2,'entry':FunctionLower(self.program.entry).lower(),
                  'functions':[FunctionLower(f).lower() for f in self.program.functions]}
        validate(result)
        return result


def validate(program):
    """Shared structural/type/CFG contract. Backends never resolve source names."""
    def require(ok, message):
        if not ok: raise ValueError('IR invalida: '+message)
    require(program.get('version')==2,'version')
    functions = [program['entry'],*program['functions']]
    require(program['entry']['return_type']=='Unidad' and not program['entry']['params'],'entrada de programa')
    require(all(f['return_type'] in TYPES for f in program['functions']),'firma de funcion')
    signatures = dict(BUILTINS)
    for f in functions:
        require(f['name'] not in signatures,'funcion duplicada')
        require(len(f['params'])<=6,'demasiados parametros')
        require(f['return_type'] in TYPES|{'Unidad'},'retorno no valido')
        signatures[f['name']] = (tuple(p['type'] for p in f['params']), f['return_type'])
    for f in functions:
        types=f['types']; code=f['instructions']; labels={}
        require(len(types)<=512,'marco demasiado grande (maximo 512 valores)')
        require(all(t in TYPES for t in types.values()),'tipo no valido')
        require(all(re.fullmatch(r'[vt][0-9]+', name) for name in types),'ID de valor no valido')
        for p in f['params']:require(types.get(p['id'])==p['type'],'parametro sin binding')
        for i,n in enumerate(code):
            if n['op']=='label':
                require(re.fullmatch(r'L[0-9]+',n['dest']) is not None,'ID de etiqueta');
                require(n['dest'] not in labels,'etiqueta duplicada'); labels[n['dest']]=i
        for n in code:
            op,d,a,t=(n[k] for k in ('op','dest','args','type'))
            def operand(v):
                require(v in types,'operando sin declarar');return types[v]
            if op=='label': continue
            if op=='jump': require(a[0] in labels,'destino de salto');continue
            if op in ('branch_false','branch_true'):
                require(operand(a[0])=='Bool' and a[1] in labels,'rama');continue
            if op in ('return','print'):
                require(operand(a[0])==t,'tipo de salida')
                if op=='return':require(t==f['return_type'],'retorno incompatible')
                continue
            require(types.get(d)==t,'destino no tipado')
            if op=='literal':
                require((t=='Int' and type(a[0]) is int and -(2**63)<=a[0]<2**63) or
                        (t=='Bool' and type(a[0]) is bool) or
                        (t=='Texto' and isinstance(a[0],str) and '\0' not in a[0]),'literal')
            elif op=='copy':require(operand(a[0])==t,'copia')
            elif op=='call':
                require(a[0] in signatures,'funcion no definida')
                params,result=signatures[a[0]]
                require(tuple(operand(v) for v in a[1:])==params and result==t,'firma de llamada')
            elif op=='no':require(len(a)==1 and operand(a[0])==t=='Bool','no')
            elif op in ('+','-','*','%'):
                require(len(a)==2 or (op=='-' and len(a)==1),'aridad aritmetica')
                require(t=='Int' and all(operand(v)=='Int' for v in a),'aritmetica')
            elif op in ('==','!=','<','<=','>','>='):
                require(len(a)==2 and t=='Bool' and operand(a[0])==operand(a[1]),'comparacion')
                require(op in ('==','!=') or operand(a[0])=='Int','comparacion ordenada')
            else: require(False,'opcode '+op)
        pending=[0];seen=set()
        while pending:
            i=pending.pop()
            if i in seen:continue
            seen.add(i)
            if i==len(code):
                require(f['return_type']=='Unidad','caida sin retorno');continue
            n=code[i]
            if n['op']=='return':continue
            if n['op']=='jump':pending.append(labels[n['args'][0]])
            elif n['op'].startswith('branch_'):pending.extend([i+1,labels[n['args'][1]]])
            else:pending.append(i+1)
