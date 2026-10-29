import re
from .model import Token, Error

PATTERN = re.compile(r'(?P<SPACE> +)|(?P<COMMENT>\#.*)|(?P<STRING>"(?:[^"\\\r\n]|\\.)*")|(?P<INT>[0-9]+)|(?P<NAME>[A-Za-z_][A-Za-z_0-9]*)|(?P<OP>==|!=|<=|>=|[+*%<>=():-])')

def lex(source, path='<entrada>'):
    tokens = []
    stack = [0]
    for number, line in enumerate(source.splitlines(), 1):
        def token(kind, text, column=1):
            return Token(kind, text, number, column, path)
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        indent = len(line) - len(line.lstrip(' '))
        if '\t' in line[:indent+1] or indent % 4:
            raise Error(token('BAD', '', 1), 'Indentacion: usa cuatro espacios por nivel.')
        if indent > stack[-1]:
            if indent != stack[-1] + 4:
                raise Error(token('BAD', ''), 'Salto de indentacion no valido.')
            stack.append(indent)
            tokens.append(token('INDENT', ''))
        while indent < stack[-1]:
            stack.pop()
            tokens.append(token('DEDENT', ''))
        if indent != stack[-1]:
            raise Error(token('BAD', ''), 'Indentacion inconsistente.')
        pos = indent
        while pos < len(line):
            match = PATTERN.match(line, pos)
            if not match:
                raise Error(token('BAD', line[pos], pos+1), 'Token no valido o cadena sin cerrar.')
            kind = match.lastgroup
            if kind == 'COMMENT':
                break
            if kind != 'SPACE':
                text = match.group()
                tokens.append(token(text if kind == 'OP' else kind, text, pos+1))
            pos = match.end()
        tokens.append(token('NEWLINE', '', len(line)+1))
    end = Token('EOF', '', len(source.splitlines())+1, 1, path)
    while len(stack) > 1:
        stack.pop()
        tokens.append(Token('DEDENT', '', end.line, 1, path))
    tokens.append(end)
    return tokens
