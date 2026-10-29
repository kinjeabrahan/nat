import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest
from natc.__main__ import compile_source
from natc.lexer import lex
from natc.parser import Parser
from natc.sema import analyze
from natc.model import Error

ROOT=Path(__file__).resolve().parents[1]

class CompilerTests(unittest.TestCase):
    def execute(self, source, arguments=(), opt='2', sanitize=False):
        with tempfile.TemporaryDirectory() as directory:
            sourcefile=Path(directory)/'test.nat'; binary=Path(directory)/'native'
            sourcefile.write_text(source,encoding='utf-8')
            command=[sys.executable,'-m','natc','build',str(sourcefile),'-o',str(binary),'--opt',opt]
            if sanitize: command.append('--sanitize')
            build=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(build.returncode,0,build.stderr)
            # No Python or Nat interpreter is launched by this execution.
            result=subprocess.run([str(binary),*map(str,arguments)],capture_output=True,text=True,
                timeout=5,env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0:halt_on_error=1','UBSAN_OPTIONS':'halt_on_error=1'})
            self.assertNotIn('runtime error:',result.stderr)
            self.assertNotIn('AddressSanitizer',result.stderr)
            return result
    def good(self, source, expected, **kwargs):
        result=self.execute(source,**kwargs)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stdout,expected)
        self.assertEqual(result.stderr,'')
    def bad(self,source,message):
        with self.assertRaisesRegex(Error,message): compile_source(source,'case.nat')
    def test_lexer_positions(self):
        tokens=lex('si verdadero:\n    imprimir 2\n','x.nat')
        integer=next(t for t in tokens if t.kind=='INT')
        self.assertEqual((integer.line,integer.column),(2,14))
        self.assertIn('INDENT',[t.kind for t in tokens])
        self.assertIn('DEDENT',[t.kind for t in tokens])
    def test_ast_structure(self):
        ast=Parser(lex('a = 2 + 3 * 4\n')).parse()
        self.assertEqual(ast[0].args[0].op,'+')
        self.assertEqual(ast[0].args[0].args[1].op,'*')
    def test_semantic_representation(self):
        ast=Parser(lex('a = 1\nb = verdadero\nc = "Nat"\n')).parse()
        self.assertEqual({b.name:b.type for b in analyze(ast).entry.locals},{'a':'Int','b':'Bool','c':'Texto'})
    def test_ir_types_and_branches(self):
        ir=compile_source('i = 0\nmientras i < 3:\n    i = i + 1\n','ir.nat')
        json.dumps(ir)
        self.assertIn('Int',ir['entry']['types'].values())
        self.assertIn('Bool',ir['entry']['types'].values())
        self.assertIn('branch_false',[i['op'] for i in ir['entry']['instructions']])
    def test_arithmetic_precedence(self):
        self.good('imprimir 2 + 3 * 4\nimprimir (2 + 3) * 4\nimprimir -7 % 3\n','14\n20\n-1\n')
    def test_literals_and_text(self):
        self.good('x = "ñ\\\"\\\\#"\nimprimir x\nimprimir "a" == "a"\nimprimir falso\n','ñ"\\#\nverdadero\nfalso\n')
    def test_loop_and_nested_condition(self):
        self.good((ROOT/'examples/compiled/suma.nat').read_text(),'4950\nverdadero\nNat compilado\n',arguments=[100])
    def test_short_circuit(self):
        self.good('imprimir falso y (1 % 0 == 1)\nimprimir verdadero o (1 % 0 == 1)\nimprimir no falso\n','falso\nverdadero\nverdadero\n')
    def test_reserved_destinations(self):
        from natc.parser import RESERVED
        for name in RESERVED:
            with self.subTest(name=name):
                self.bad(name + ' = 1\n', 'palabra reservada')

    def test_type_errors(self):
        for source in ['a = 1\na = "x"\n','imprimir 1 + verdadero\n','imprimir 1 == "1"\n','si 1:\n    imprimir 1\n']:
            with self.subTest(source=source):
                with self.assertRaises(Error): compile_source(source,'type.nat')
    def test_undefined_even_in_dead_branch(self):
        self.bad('si falso:\n    imprimir ausente\n','no definida')
    def test_nested_declaration_does_not_escape(self):
        self.bad('si verdadero:\n    a = 1\nimprimir a\n','no definida')
    def test_invalid_syntax(self):
        for source in ['imprimir "ab\n','imprimir [1]\n','imprimir "a" "b"\n','imprimir 1 / 2\n','imprimir "\\u0000"\n','    imprimir 1\n','si verdadero:\n\timprimir 1\n','si verdadero:\n        imprimir 1\n']:
            with self.subTest(source=source):
                with self.assertRaises(Error): compile_source(source,'bad.nat')
    def test_out_of_range_literal(self):
        self.bad('imprimir 9223372036854775808\n','fuera de Int64')
        self.bad('imprimir -9223372036854775809\n','fuera de Int64')
    def test_min_max(self):
        self.good('imprimir -9223372036854775808\nimprimir 9223372036854775807\nimprimir -9223372036854775808 % -1\n', '-9223372036854775808\n9223372036854775807\n0\n')
    def test_overflow_and_zero(self):
        cases=[('9223372036854775807 + 1','Desbordamiento'),('-9223372036854775808 - 1','Desbordamiento'),('9223372036854775807 * 2','Desbordamiento'),('-x','Desbordamiento'),('1 % 0','cero')]
        for expression,message in cases:
            with self.subTest(expression=expression):
                result=self.execute('x = -9223372036854775808\nimprimir '+expression+'\n',sanitize=True)
                self.assertEqual(result.returncode,1)
                self.assertIn(message,result.stderr)
                self.assertRegex(result.stderr,r'test.nat:2:\d+:')
    def test_input_validation(self):
        for args in [[],['abc'],['9223372036854775808'],[' 1'],['-']]:
            with self.subTest(args=args):
                result=self.execute('imprimir entrada_entero()\n',arguments=args)
                self.assertEqual(result.returncode,1)
    def test_generated_arithmetic_differential(self):
        rng=random.Random(42)
        expressions=[]; expected=[]
        for _ in range(40):
            a,b,c=[rng.randint(-1000,1000) for _ in range(3)]
            expressions.append(f'imprimir ({a} + {b}) * {c}')
            expected.append(str((a+b)*c))
        source='\n'.join(expressions)+'\n'; output='\n'.join(expected)+'\n'
        for opt,sanitize in [('0',False),('2',False),('2',True)]:
            with self.subTest(opt=opt,sanitize=sanitize):
                self.good(source,output,opt=opt,sanitize=sanitize)
    def test_failed_build_preserves_output(self):
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'bad.nat'; output=Path(directory)/'existing'
            source.write_text('imprimir inexistente\n'); output.write_bytes(b'preservar')
            result=subprocess.run([sys.executable,'-m','natc','build',str(source),'-o',str(output)],cwd=ROOT,capture_output=True)
            self.assertEqual(result.returncode,1)
            self.assertEqual(output.read_bytes(),b'preservar')

if __name__=='__main__': unittest.main()
