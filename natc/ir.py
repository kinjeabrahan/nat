"""Typed three-address IR with explicit labels and conditional branches."""
from dataclasses import dataclass, asdict

@dataclass
class Instruction:
    op: str
    dest: str
    args: list
    type: str
    line: int
    column: int

class Lower:
    def __init__(self, symbols):
        self.code, self.types = [], {'v'+str(i):t for i,t in enumerate(symbols.values())}
        self.names = {s:'v'+str(i) for i,s in enumerate(symbols)}
        self.counter = 0
    def fresh(self, prefix='t'):
        self.counter += 1
        return prefix+str(self.counter)
    def emit(self, op, dest, args, typ, token):
        self.code.append(Instruction(op,dest,args,typ,token.line,token.column))
    def expr(self,n):
        if n.op == 'name':
            # Snapshot a variable at the expression's evaluation point.
            args, op = [self.names[n.value]], 'copy'
        elif n.op in ('literal','call'):
            args, op = [n.value], n.op
        elif n.op in ('y','o'):
            left = self.expr(n.args[0]); dest = self.fresh(); end = self.fresh('L')
            self.types[dest] = 'Bool'
            self.emit('copy',dest,[left],'Bool',n.token)
            self.emit('branch_false' if n.op=='y' else 'branch_true','',[left,end],'',n.token)
            right = self.expr(n.args[1])
            self.emit('copy',dest,[right],'Bool',n.token)
            self.emit('label',end,[],'',n.token)
            return dest
        else:
            args, op = [self.expr(x) for x in n.args], n.op
        dest = self.fresh(); self.types[dest] = n.type
        self.emit(op,dest,args,n.type,n.token)
        return dest
    def block(self, body):
        for n in body:
            if n.op == 'assign':
                value = self.expr(n.args[0])
                self.emit('copy',self.names[n.value],[value],n.type,n.token)
            elif n.op == 'print':
                value = self.expr(n.args[0])
                self.emit('print','',[value],n.args[0].type,n.token)
            else:
                start, end = self.fresh('L'), self.fresh('L')
                if n.op == 'mientras':
                    self.emit('label',start,[],'',n.token)
                condition = self.expr(n.args[0])
                self.emit('branch_false','',[condition,end],'',n.token)
                self.block(n.args[1])
                if n.op == 'mientras':
                    self.emit('jump','',[start],'',n.token)
                self.emit('label',end,[],'',n.token)
    def lower(self, body):
        self.block(body)
        return {'types':self.types,'instructions':[asdict(i) for i in self.code]}
