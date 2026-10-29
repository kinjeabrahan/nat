from .model import Error

MIN, MAX = -(2**63), 2**63-1

def analyze(body):
    symbols = {}
    def expr(n):
        if n.op == 'literal':
            if n.type == 'Int' and not MIN <= n.value <= MAX:
                raise Error(n.token, 'Literal fuera de Int64.')
        elif n.op == 'name':
            if n.value not in symbols:
                raise Error(n.token, f'Variable no definida: {n.value}.')
            n.type = symbols[n.value]
        elif n.op == 'call':
            if n.value != 'entrada_entero':
                raise Error(n.token, 'Solo entrada_entero() esta disponible; lee argv[1].')
            n.type = 'Int'
        else:
            types = [expr(x) for x in n.args]
            required = 'Bool' if n.op in ('y','o','no') else 'Int'
            if n.op in ('==','!='):
                if len(set(types)) != 1:
                    raise Error(n.token, 'Igualdad requiere operandos del mismo tipo.')
            elif any(t != required for t in types):
                raise Error(n.token, f'{n.op} requiere {required}, recibio {types}.')
            n.type = 'Bool' if n.op in ('==','!=','<','<=','>','>=','y','o','no') else 'Int'
        return n.type
    def statements(nodes, nested=False):
        for n in nodes:
            if n.op == 'assign':
                typ = expr(n.args[0])
                if n.value not in symbols and nested:
                    raise Error(n.token, 'Declara la variable antes del bloque en este primer subconjunto.')
                if n.value in symbols and symbols[n.value] != typ:
                    raise Error(n.token, 'Una variable no puede cambiar de tipo.')
                symbols[n.value] = n.type = typ
            elif n.op == 'print':
                expr(n.args[0])
            else:
                if expr(n.args[0]) != 'Bool':
                    raise Error(n.token, 'La condicion requiere Bool.')
                statements(n.args[1], True)
    statements(body)
    return symbols
