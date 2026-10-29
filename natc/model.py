from dataclasses import dataclass, field

@dataclass
class Token:
    kind: str
    text: str
    line: int
    column: int
    path: str

class Error(Exception):
    def __init__(self, token, message):
        super().__init__(f'{token.path}:{token.line}:{token.column}: {message}')

@dataclass
class Node:
    op: str
    token: Token
    args: list = field(default_factory=list)
    value: object = None
    type: str = ''
