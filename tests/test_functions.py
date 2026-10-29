import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from natc.__main__ import compile_source
from natc.ir import validate
from natc.model import Error

ROOT=Path(__file__).resolve().parents[1]
BACKENDS=('c','asm')

class FunctionTests(unittest.TestCase):
    def execute(self, source, data=b'', arguments=(), backend='asm', env=None, sanitize=False):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'test.nat';path.write_text(source)
            binary=Path(directory)/'program'
            command=[sys.executable,'-m','natc','build',str(path),'--backend',backend,'-o',str(binary)]
            if sanitize:command.append('--sanitize')
            build=subprocess.run(command,cwd=ROOT,capture_output=True,env=env)
            self.assertEqual(build.returncode,0,build.stderr.decode())
            return subprocess.run([str(binary),*map(str,arguments)],input=data,capture_output=True,timeout=5,
                env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0:halt_on_error=1','UBSAN_OPTIONS':'halt_on_error=1'})
    def both(self, source, expected, **kwargs):
        for backend in BACKENDS:
            with self.subTest(backend=backend):
                result=self.execute(source,backend=backend,**kwargs)
                self.assertEqual(result.returncode,0,result.stderr.decode())
                self.assertEqual(result.stdout,expected)
                self.assertEqual(result.stderr,b'')
    def test_nested_calls_six_parameters(self):
        self.both('''func doble(x: Int) -> Int:
    local = x * 2
    retornar local
func combinar(a: Int, b: Int, c: Int, d: Int, e: Int, f: Int) -> Int:
    local = a + b + c + d + e + f
    retornar local
local = 99
imprimir combinar(doble(1), doble(doble(2)), 3, 4, 5, 6)
imprimir local
''',b'28\n99\n')
    def test_recursion_and_mutual_recursion(self):
        self.both('''func fib(n: Int) -> Int:
    si n < 2:
        retornar n
    retornar fib(n - 1) + fib(n - 2)
func par(n: Int) -> Bool:
    si n == 0:
        retornar verdadero
    retornar impar(n - 1)
func impar(n: Int) -> Bool:
    si n == 0:
        retornar falso
    retornar par(n - 1)
imprimir fib(12)
imprimir par(18)
imprimir impar(18)
''',b'144\nverdadero\nfalso\n')
    def test_text_bool_and_else_returns(self):
        self.both('''func escoger(b: Bool, texto: Texto) -> Texto:
    si b:
        retornar texto
    sino:
        retornar "otro"
imprimir escoger(verdadero, "ñ")
imprimir escoger(falso, "Nat")
''','ñ\notro\n'.encode())
    def test_scope_loops_and_initialization(self):
        self.both('''func sumar(n: Int) -> Int:
    i = 0
    total = 0
    mientras i < n:
        parcial = i * 2
        total = total + parcial
        i = i + 1
    retornar total
si verdadero:
    temporal = 1
    imprimir temporal
imprimir sumar(5)
imprimir sumar(3)
''',b'1\n20\n6\n')
    def test_argument_order_and_byte_input(self):
        self.both('''func juntar(a: Int, b: Int) -> Int:
    retornar a * 1000 + b
imprimir juntar(leer_byte(), leer_byte())
imprimir leer_byte()
''',b'65255\n-1\n',data=bytes([65,255]))
    def test_input_inside_function_and_integer_boundaries(self):
        self.both('''func entrada() -> Int:
    retornar entrada_entero()
func identidad(n: Int) -> Int:
    retornar n
imprimir identidad(entrada())
imprimir -9223372036854775808 % -1
''',b'-9223372036854775808\n0\n',arguments=['-9223372036854775808'])
    def test_invalid_programs_before_codegen(self):
        sources=[
            'retornar 1\n',
            'func f(x: Int) -> Int:\n    retornar x\nimprimir f()\n',
            'func f(x: Int) -> Int:\n    retornar x\nimprimir f(verdadero)\n',
            'func f() -> Int:\n    retornar "no"\n',
            'func f(x: Int) -> Int:\n    si x > 0:\n        retornar x\n',
            'func f(x: Int, x: Bool) -> Int:\n    retornar 1\n',
            'func f() -> Otro:\n    retornar 1\n',
            'func f() -> Int:\n    retornar ausente\n',
            'func f() -> Int:\n    retornar 1\nfunc f() -> Int:\n    retornar 2\n',
            'x = 1\nfunc f() -> Int:\n    retornar x\n',
            'func f() -> Int:\n    si verdadero:\n        x = 1\n    retornar x\n',
            'imprimir desconocida(1)\n',
            'func f(a: Int,b: Int,c: Int,d: Int,e: Int,f: Int,g: Int) -> Int:\n    retornar a\n',
        ]
        for source in sources:
            with self.subTest(source=source):
                with self.assertRaises(Error) as result:compile_source(source,'invalid.nat')
                self.assertIn('invalid.nat:',str(result.exception))
    def test_shared_ir_contract(self):
        ir=compile_source('func f(x: Int) -> Int:\n    retornar x\nimprimir f(1)\n','ir.nat')
        self.assertEqual(ir['version'],2)
        self.assertEqual(ir['functions'][0]['params'],[{'id':'v0','type':'Int'}])
        json.dumps(ir)
        broken=copy.deepcopy(ir)
        call=next(n for n in broken['entry']['instructions'] if n['op']=='call')
        call['args'].append(call['args'][1])
        with self.assertRaises(ValueError):validate(broken)
        broken=copy.deepcopy(ir)
        broken['functions'][0]['instructions'][-1]['type']='Bool'
        with self.assertRaises(ValueError):validate(broken)
    def test_recursion_limit_and_runtime_errors(self):
        sources=[('func ciclo(n: Int) -> Int:\n    retornar ciclo(n + 1)\nimprimir ciclo(0)\n',b'Limite de llamadas'),
                 ('func fallo(x: Int) -> Int:\n    retornar x + 1\nimprimir fallo(9223372036854775807)\n',b'Desbordamiento')]
        for source,message in sources:
            for backend in BACKENDS:
                with self.subTest(backend=backend,message=message):
                    result=self.execute(source,backend=backend)
                    self.assertEqual(result.returncode,1)
                    self.assertIn(message,result.stderr)
                    self.assertIn(b'test.nat:',result.stderr)
    def test_native_no_gcc(self):
        with tempfile.TemporaryDirectory() as directory:
            for name in ('as','ld'):(Path(directory)/name).symlink_to(shutil.which(name))
            result=self.execute('func f(n: Int) -> Int:\n    retornar n * 2\nimprimir f(21)\n',env={**os.environ,'PATH':directory})
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(result.stdout,b'42\n')
    def test_sanitized_c_frames(self):
        result=self.execute('func f(n: Int) -> Int:\n    si n == 0:\n        retornar 0\n    local = n\n    retornar local + f(n - 1)\nimprimir f(30)\n',backend='c',sanitize=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stdout,b'465\n')
        self.assertEqual(result.stderr,b'')

if __name__=='__main__':unittest.main()
