"""Black-box CLI tests. Only the baseline group must pass before the fix."""
import argparse
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
NAT = ROOT / "build/nat"


class NatCase(unittest.TestCase):
    def run_source(self, source, files=None):
        with tempfile.TemporaryDirectory(prefix="nat-test-") as directory:
            root = Path(directory)
            path = root / "main.nat"
            path.write_bytes(source.encode("utf-8") if isinstance(source, str) else source)
            for name, content in (files or {}).items():
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
            return subprocess.run(
                [str(NAT), str(path)], cwd=ROOT, capture_output=True,
                text=True, encoding="utf-8", timeout=15,
            )

    def assert_success(self, source, expected, files=None):
        result = self.run_source(source, files)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, expected)
        self.assertEqual(result.stderr, "")

    def assert_error(self, source, expected, line=1, files=None):
        result = self.run_source(source, files)
        self.assertGreater(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertIn(expected, result.stderr)
        if line is not None:
            self.assertIn(f"main.nat:{line}:", result.stderr)
        for marker in ("AddressSanitizer", "LeakSanitizer", "runtime error:"):
            self.assertNotIn(marker, result.stderr)


class BaselineTests(NatCase):
    def test_existing_loop(self):
        self.assert_success((ROOT / "pruebas/bucle.nat").read_text(),
                            "Entrando al ciclo de Nat\nCiclo finalizado\n")

    def test_existing_strings(self):
        self.assert_success((ROOT / "pruebas/cadenas.nat").read_text(),
                            "3\na\n1\n-1\nLongitud correcta\n")

    def test_existing_module(self):
        self.assert_success((ROOT / "pruebas/interprete.nat").read_text(),
                            "[Nat-Core] Sistema cargado\nEntrando al ciclo de Nat\n"
                            "Ciclo finalizado\nPrograma principal finalizado\n",
                            {"bucle.nat": (ROOT / "pruebas/bucle.nat").read_text()})

    def test_hello_module(self):
        self.assert_success((ROOT / "holamundo.nat").read_text(),
                            "Ejecutandose desde el archivo secundario leido por Nat\n",
                            {"subprograma.nat": (ROOT / "subprograma.nat").read_text()})

    def test_assignment_and_copy(self):
        self.assert_success('a = "Nat"\nb = a\na = "nuevo"\nimprimir b\nimprimir a\n',
                            "Nat\nnuevo\n")

    def test_comments_and_escapes(self):
        self.assert_success('# comentario\nimprimir "a#b" # fin\n'
                            'imprimir "a\\\"b\\\\c"\n', 'a#b\na"b\\c\n')

    def test_empty_string(self):
        self.assert_success('imprimir ""\nimprimir longitud("")\n', "\n0\n")

    def test_eof_without_newline(self):
        self.assert_success('imprimir "Nat"', "Nat\n")

    def test_crlf(self):
        self.assert_success(b'imprimir "Nat"\r\n', "Nat\n")

    def test_false_condition(self):
        self.assert_success('si "a" != "a":\n    imprimir "no"\nimprimir "si"\n', "si\n")

    def test_nested_blocks(self):
        self.assert_success('a = "0"\nmientras a == "0":\n'
                            '    si a == "0":\n        imprimir "dentro"\n'
                            '    a = "1"\nimprimir a\n', "dentro\n1\n")

    def test_nested_calls(self):
        self.assert_success('imprimir caracter("Nat", buscar("Nat", "a"))\n'
                            'imprimir longitud(caracter("Nat", 2))\n', "a\n1\n")

    def test_quoted_delimiters(self):
        self.assert_success('imprimir buscar("a,(b)", ",")\n'
                            'imprimir caracter("a,b", 1)\n', "1\n,\n")

    def test_relative_nested_modules(self):
        self.assert_success('leer "mod/a.nat"\nimprimir valor\n', "incluido\n",
                            {"mod/a.nat": 'leer "b.nat"\n',
                             "mod/b.nat": 'valor = "incluido"\n'})

    def test_index_out_of_bounds(self):
        self.assert_error('imprimir caracter("Nat", 3)\n', "Indice fuera del texto.")

    def test_negative_index(self):
        self.assert_error('imprimir caracter("Nat", -1)\n', "Indice de caracter no valido.")

    def test_invalid_indices(self):
        for value in ('"a"', '"9999999999999999999999999999999999999999"'):
            with self.subTest(value=value):
                self.assert_error(f'imprimir caracter("Nat", {value})\n',
                                  "Indice de caracter no valido.")

    def test_unknown_function(self):
        self.assert_error('imprimir desconocida("a", "b")\n',
                          "Funcion de cadenas desconocida.")

    def test_missing_argument(self):
        self.assert_error('imprimir buscar("Nat")\n', "Esta funcion necesita dos argumentos.")

    def test_empty_argument(self):
        self.assert_error('imprimir buscar("Nat", )\n', "Argumento vacio.")

    def test_missing_colon(self):
        self.assert_error('si "a" == "a"\n    imprimir "no"\n', "Falta ':' en el bloque.")

    def test_empty_block(self):
        self.assert_error('si "a" == "a":\n', "El bloque esta vacio.", line=2)

    def test_top_level_indentation(self):
        self.assert_error('    imprimir "no"\n', "Indentacion inesperada fuera de un bloque.")

    def test_mixed_indentation(self):
        self.assert_error('si "a" == "a":\n \timprimir "no"\n',
                          "No mezcles espacios y tabuladores", line=2)

    def test_variable_limit(self):
        self.assert_error("".join(f'v{i} = "x"\n' for i in range(101)),
                          "Limite de variables alcanzado.", line=101)

    def test_identifier_limit(self):
        self.assert_error("a" * 64 + ' = "x"\n', "Nombre de variable demasiado largo.")

    def test_value_boundary(self):
        self.assert_success('imprimir "' + "x" * 255 + '"\n', "x" * 255 + "\n")
        self.assert_error('imprimir "' + "x" * 256 + '"\n', "Cadena demasiado larga.")

    def test_line_limit(self):
        self.assert_error("#" * 600 + "\n", "La linea supera el limite permitido.")

    def test_file_line_limit(self):
        self.assert_error("#\n" * 501, "El archivo supera el limite de lineas.", line=501)

    def test_include_depth_limit(self):
        self.assert_error('leer "main.nat"\n', "Limite de archivos anidados alcanzado.", line=None)

    def test_global_iteration_limit(self):
        self.assert_error('mientras "x" == "x":\n    a = "x"\n',
                          "Limite global de iteraciones alcanzado.")

    def test_missing_file(self):
        self.assert_error('leer "ausente.nat"\n', "No se pudo abrir", line=None)

    def test_cli_usage(self):
        result = subprocess.run([str(NAT)], capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Uso: nat archivo.nat", result.stderr)


class SemanticTests(NatCase):
    def test_unknown_identifier(self):
        self.assert_error('imprimir nombr\n', 'Variable no definida: nombr.')

    def test_unknown_assignment_source(self):
        self.assert_error('nombre = nombr\n', 'Variable no definida: nombr.')

    def test_unknown_condition_operand(self):
        self.assert_error('si nombr == "x":\n    imprimir "no"\n', 'Variable no definida: nombr.')

    def test_reserved_destinations(self):
        for name in ('si','mientras','imprimir','verdadero','falso','y','o','no','func','retornar','leer','sino'):
            with self.subTest(name=name):
                self.assert_error(name+' = "x"\n', 'palabra reservada')

    def test_keyword_prefix_identifiers(self):
        self.assert_success('imprimirx = "bien"\nsino_otro = imprimirx\nimprimir sino_otro\n', 'bien\n')

    def test_keyword_separator_tab(self):
        self.assert_success('si\t"a" == "a":\n    imprimir\t"bien"\n', 'bien\n')

    def test_comparison_is_not_assignment(self):
        for op in ('==','!='):
            with self.subTest(op=op):
                self.assert_error('a'+op+'b\n', 'Una comparacion no es una asignacion')

    def test_invalid_strings(self):
        for value in ('"Nat', '"a" "b"', '"a"b"', '"a" basura', '"a\\q"', '"a\\'):
            with self.subTest(value=value):
                result=self.run_source('imprimir '+value+'\n')
                self.assertEqual(result.returncode,1)
                self.assertIn('main.nat:1:', result.stderr)
                self.assertEqual(result.stdout,'')
                self.assertNotIn('Sanitizer', result.stderr)

    def test_escape_contents(self):
        self.assert_success('imprimir "a\\nb\\tc\\\"d\\\\e#"\n', 'a\nb\tc"d\\e#\n')

    def test_no_text_fallback(self):
        for value in ('1 + 2','123abc','hola mundo'):
            with self.subTest(value=value):
                self.assert_error('imprimir '+value+'\n', 'Expresion no valida')

    def test_scalar_compatibility(self):
        self.assert_success('a = -12\nimprimir a\nimprimir verdadero\nimprimir falso\n', '-12\nverdadero\nfalso\n')

    def test_extra_indent(self):
        self.assert_error('si "a" == "a":\n    a = "x"\n        imprimir a\n', 'Indentacion inesperada', line=3)

    def test_bad_dedent(self):
        self.assert_error('si "a" == "a":\n    a = "x"\n  imprimir a\n', 'cuatro espacios', line=3)

    def test_lexical_error_in_dead_branch(self):
        self.assert_error('si "a" != "a":\n    imprimir "sin cerrar\n', 'Cadena sin cerrar.', line=2)

    def test_empty_and_malformed_paths(self):
        self.assert_error('leer ""\n', 'ruta no puede estar vacia')
        self.assert_error('leer "a" "b"\n', 'Sintaxis correcta')
        self.assert_error('leer "a\\nb"\n', 'ruta no puede contener')

    def test_long_line_and_empty_path_cli(self):
        self.assert_error('imprimir "'+'x'*256+'"\n', 'Cadena demasiado larga')
        result = subprocess.run([str(NAT), ''], capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode,1)
        self.assertIn('ruta no puede estar vacia',result.stderr)


class ArgumentLimitTests(NatCase):
    def test_third_literal_argument(self):
        self.assert_error('imprimir buscar("Nat", "a", "extra")\n', "Demasiados argumentos.")

    def test_third_identifier_argument(self):
        self.assert_error('imprimir caracter("Nat", 1, extra)\n', "Demasiados argumentos.")

    def test_third_nested_argument(self):
        self.assert_error('imprimir buscar("Nat", "a", longitud("Nat"))\n',
                          "Demasiados argumentos.")

    def test_third_argument_after_comma_in_string(self):
        self.assert_error('imprimir buscar("N,at", ",", "x")\n', "Demasiados argumentos.")

    def test_extra_argument_on_length(self):
        self.assert_error('imprimir longitud("Nat", "a", "extra")\n', "Demasiados argumentos.")

    def test_four_arguments(self):
        self.assert_error('imprimir buscar("Nat", "a", "b", "c")\n', "Demasiados argumentos.")

    def test_nested_overflow(self):
        self.assert_error('imprimir longitud(buscar("Nat", "a", "extra"))\n',
                          "Demasiados argumentos.")

    def test_trailing_comma_after_two(self):
        self.assert_error('imprimir buscar("Nat", "a",)\n', "Demasiados argumentos.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nat", type=Path, default=NAT)
    parser.add_argument("--group", choices=("baseline", "regression", "all"), default="all")
    args = parser.parse_args()
    NAT = args.nat.resolve()
    if not NAT.is_file():
        parser.error(f"Compile Nat first: {NAT}")
    groups = {"baseline": [BaselineTests], "regression": [ArgumentLimitTests],
              "all": [BaselineTests, ArgumentLimitTests, SemanticTests]}
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(cls)
                               for cls in groups[args.group])
    raise SystemExit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
