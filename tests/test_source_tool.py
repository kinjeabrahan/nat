"""Independent references for the real Nat text tool and lexer byte classifier."""
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'herramientas/nat_fuente.nat'

class SourceToolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name);cls.binaries={}
        for backend in ('c','asm'):
            binary=cls.root/('tool-'+backend)
            r=subprocess.run([sys.executable,'-m','natc','build',str(SOURCE),'--backend',backend,'-o',str(binary)],cwd=ROOT,capture_output=True)
            if r.returncode:raise AssertionError(r.stderr.decode())
            cls.binaries[backend]=binary
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def test_statistics_against_independent_reference(self):
        for data in [b'',b'alpha beta_2\n123 + _x\n',b'a\r\nb\t c\v\f',b'final_sin_LF',bytes(range(256))*2,'ñ 日本 alfa_1\n'.encode()]:
            expected=(f"lineas\n{data.count(bytes([10]))}\npalabras\n{len(data.split())}\n"
                      f"identificadores_ascii\n{len(re.findall(rb'[A-Za-z_][A-Za-z_0-9]*',data))}\nbytes\n{len(data)}\n").encode()
            for backend,binary in self.binaries.items():
                with self.subTest(backend=backend,data=data[:20]):
                    result=subprocess.run([str(binary)],input=data,capture_output=True,timeout=5)
                    self.assertEqual(result.returncode,0,result.stderr)
                    self.assertEqual(result.stdout,expected)
                    self.assertEqual(result.stderr,b'')
    def test_classifier_all_bytes(self):
        # Compile the actual Nat helper definitions with an independent test driver.
        helpers=SOURCE.read_text().split('func analizar()')[0]
        driver='b = leer_byte()\nmientras b != -1:\n    imprimir clase_ascii(b)\n    b = leer_byte()\n'
        source=self.root/'classify.nat';source.write_text(helpers+driver)
        expected=[]
        for byte in range(256):
            character=bytes([byte])
            expected.append(0 if character in (b' ',b'\t',b'\n',b'\r',b'\v',b'\f') else
                            1 if re.fullmatch(rb'[A-Za-z_]',character) else
                            2 if re.fullmatch(rb'[0-9]',character) else 3)
        for backend in ('c','asm'):
            binary=self.root/('classify-'+backend)
            r=subprocess.run([sys.executable,'-m','natc','build',str(source),'--backend',backend,'-o',str(binary)],cwd=ROOT,capture_output=True)
            self.assertEqual(r.returncode,0,r.stderr)
            r=subprocess.run([str(binary)],input=bytes(range(256)),capture_output=True)
            self.assertEqual(r.returncode,0,r.stderr)
            self.assertEqual(list(map(int,r.stdout.splitlines())),expected)
    def test_io_errors_not_silent_success(self):
        def close_input():
            try:os.close(0)
            except OSError:pass
        for backend,binary in self.binaries.items():
            with self.subTest(backend=backend,error='read'):
                r=subprocess.run([str(binary)],capture_output=True,preexec_fn=close_input,timeout=5)
                self.assertEqual(r.returncode,1)
                self.assertIn(b'Error de lectura',r.stderr)
            if Path('/dev/full').exists():
                with self.subTest(backend=backend,error='write'), open('/dev/full','wb') as sink:
                    r=subprocess.run([str(binary)],input=b'a',stdout=sink,stderr=subprocess.PIPE)
                    self.assertEqual(r.returncode,1)
                    self.assertIn(b'Error de salida',r.stderr)

if __name__=='__main__':unittest.main()
