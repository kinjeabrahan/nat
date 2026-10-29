"""Resolve lexical bindings and typed signatures once, before either backend."""
from dataclasses import dataclass, field
from .model import Error

MIN, MAX = -(2**63), 2**63-1
TYPES = {'Int', 'Bool', 'Texto'}
BUILTINS = {'entrada_entero': ((), 'Int'), 'leer_byte': ((), 'Int')}

@dataclass
class Binding:
    id: str
    name: str
    type: str

@dataclass
class Function:
    name: str
    params: list
    return_type: str
    body: list
    token: object
    locals: list = field(default_factory=list)

@dataclass
class Program:
    entry: Function
    functions: list


def analyze(body):
    definitions = [n for n in body if n.op == 'function']
    signatures = dict(BUILTINS)
    for n in definitions:
        name = n.token.text
        if name in signatures or name == '__nat_main':
            raise Error(n.token, 'Nombre de funcion duplicado o reservado: '+name)
        params = n.value['params']; result = n.value['return_type']
        if len(params) > 6: raise Error(n.token, 'Este destino admite hasta seis parametros.')
        if result not in TYPES or any(t not in TYPES for _,t in params):
            raise Error(n.token, 'Tipo no soportado; usa Int, Bool o Texto.')
        if len({p.text for p,_ in params}) != len(params):
            raise Error(n.token, 'Parametro duplicado.')
        signatures[name] = (tuple(t for _,t in params), result)

    def check(function, declared_params):
        scopes = [{}]
        def bind(name, typ, token):
            if name in signatures: raise Error(token, 'Nombre reservado para una funcion: '+name)
            binding = Binding('v'+str(len(function.locals)), name, typ)
            scopes[-1][name] = binding; function.locals.append(binding)
            return binding
        def lookup(name):
            return next((s[name] for s in reversed(scopes) if name in s), None)
        for token,typ in declared_params:
            function.params.append(bind(token.text, typ, token))
        def expr(n):
            if n.op == 'literal':
                if n.type == 'Int' and not MIN <= n.value <= MAX:
                    raise Error(n.token, 'Literal fuera de Int64.')
            elif n.op == 'name':
                binding = lookup(n.value)
                if binding is None: raise Error(n.token, 'Variable no definida: '+n.value)
                n.binding, n.type = binding.id, binding.type
            elif n.op == 'call':
                if n.value not in signatures: raise Error(n.token, 'Funcion no definida: '+n.value)
                params, result = signatures[n.value]
                if len(n.args) != len(params): raise Error(n.token, 'Cantidad de argumentos incorrecta para '+n.value)
                actual = tuple(expr(arg) for arg in n.args)
                if actual != params: raise Error(n.token, f'Tipos de argumentos incorrectos: {actual}; se esperaba {params}.')
                n.type = result
            else:
                types = [expr(x) for x in n.args]
                required = 'Bool' if n.op in ('y','o','no') else 'Int'
                if n.op in ('==','!='):
                    if len(set(types)) != 1: raise Error(n.token, 'Igualdad requiere operandos del mismo tipo.')
                elif any(t != required for t in types):
                    raise Error(n.token, f'{n.op} requiere {required}, recibio {types}.')
                n.type = 'Bool' if n.op in ('==','!=','<','<=','>','>=','y','o','no') else 'Int'
            return n.type
        def block(nodes, nested=False):
            if nested: scopes.append({})
            guaranteed = False
            for n in nodes:
                if guaranteed: raise Error(n.token, 'Codigo inalcanzable tras un retorno.')
                if n.op == 'assign':
                    typ = expr(n.args[0]); binding = lookup(n.value)
                    if binding is None: binding = bind(n.value, typ, n.token)
                    elif binding.type != typ: raise Error(n.token, 'Una variable no puede cambiar de tipo.')
                    n.binding, n.type = binding.id, typ
                elif n.op == 'print': expr(n.args[0])
                elif n.op == 'return':
                    if function.return_type == 'Unidad': raise Error(n.token, 'retornar solo puede usarse dentro de una funcion.')
                    if expr(n.args[0]) != function.return_type: raise Error(n.token, 'Tipo de retorno incorrecto.')
                    n.type = function.return_type; guaranteed = True
                else:
                    if expr(n.args[0]) != 'Bool': raise Error(n.token, 'La condicion requiere Bool.')
                    first = block(n.args[1], True)
                    second = block(n.args[2], True) if len(n.args) == 3 else False
                    guaranteed = n.op == 'si' and first and second
            if nested: scopes.pop()
            return guaranteed
        returns = block(function.body)
        if function.return_type != 'Unidad' and not returns:
            raise Error(function.token, 'No todas las rutas retornan un valor.')
        return function

    functions = [check(Function(n.token.text, [], n.value['return_type'], n.args[0], n.token), n.value['params']) for n in definitions]
    entry_body = [n for n in body if n.op != 'function']
    from .model import Token
    entry_token = body[0].token if body else Token('EOF','',1,1,'<entrada>')
    entry = check(Function('__nat_main', [], 'Unidad', entry_body, entry_token), [])
    return Program(entry, functions)
