import json
from .model import Node, Error

PRECEDENCE = {'o':1, 'y':2, '==':3, '!=':3, '<':4, '<=':4, '>':4, '>=':4, '+':5, '-':5, '*':6, '%':6}
RESERVED = {'si','mientras','imprimir','verdadero','falso','y','o','no','func','retornar','leer','sino'}

class Parser:
    def __init__(self, tokens):
        self.tokens, self.pos = tokens, 0
    def peek(self):
        return self.tokens[self.pos]
    def take(self, kind=None):
        t = self.peek()
        if kind is not None and t.kind != kind:
            raise Error(t, f'Se esperaba {kind}; se encontro {t.text or t.kind}.')
        self.pos += 1
        return t
    def expr(self, minimum=0):
        t = self.take()
        if t.kind == 'INT':
            if len(t.text) > 20:
                raise Error(t, 'Literal fuera de Int64.')
            node = Node('literal', t, value=int(t.text), type='Int')
        elif t.kind == 'STRING':
            try:
                value = json.loads(t.text)
                value.encode('utf-8')
                if '\0' in value:
                    raise ValueError()
            except (ValueError, UnicodeError):
                raise Error(t, 'Cadena UTF-8/escape no valido; NUL no admitido.')
            node = Node('literal', t, value=value, type='Texto')
        elif t.text in ('verdadero', 'falso'):
            node = Node('literal', t, value=t.text == 'verdadero', type='Bool')
        elif t.text in ('-', 'no'):
            operand = self.expr(7)
            if t.text == '-' and operand.op == 'literal' and operand.type == 'Int':
                node = Node('literal', t, value=-operand.value, type='Int')
            else:
                node = Node(t.text, t, [operand])
        elif t.kind == '(':
            node = self.expr()
            self.take(')')
        elif t.kind == 'NAME' and t.text not in RESERVED:
            if self.peek().kind == '(':
                self.take('(')
                self.take(')')
                node = Node('call', t, value=t.text)
            else:
                node = Node('name', t, value=t.text)
        else:
            raise Error(t, 'Expresion no valida.')
        while PRECEDENCE.get(self.peek().text, -1) >= minimum:
            op = self.take()
            node = Node(op.text, op, [node, self.expr(PRECEDENCE[op.text]+1)])
        return node
    def block(self, nested=False):
        nodes = []
        while self.peek().kind not in ('EOF', 'DEDENT'):
            t = self.take('NAME')
            if t.text in RESERVED and self.peek().kind == '=':
                raise Error(t, 'No puedes asignar a una palabra reservada.')
            if t.text in ('si', 'mientras'):
                condition = self.expr()
                self.take(':'); self.take('NEWLINE'); self.take('INDENT')
                body = self.block(True)
                self.take('DEDENT')
                nodes.append(Node(t.text, t, [condition, body]))
            elif t.text == 'imprimir':
                nodes.append(Node('print', t, [self.expr()]))
                self.take('NEWLINE')
            elif t.text not in RESERVED:
                self.take('=')
                nodes.append(Node('assign', t, [self.expr()], t.text))
                self.take('NEWLINE')
            else:
                raise Error(t, 'Instruccion aun no soportada por natc.')
        if nested and not nodes:
            raise Error(self.peek(), 'Bloque vacio.')
        return nodes
    def parse(self):
        body = self.block()
        self.take('EOF')
        return body
