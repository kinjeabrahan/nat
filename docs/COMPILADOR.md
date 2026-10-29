# Nat, entrega 2: compilador AOT experimental

## Qué existe ahora

`python3 -m natc build programa.nat -o ejecutable` produce un ejecutable nativo
mediante C generado y GCC. La ejecución del resultado no lanza Python ni el
intérprete de Nat. El compilador de arranque está escrito en Python 3.12;
el runtime generado es C con libc. No hay self-hosting.

La primera entrega se verificó antes de editar: su parche se aplica a la
instantánea original y reproduce el `nat.c` local. Las 41 pruebas anteriores
pasaron normalmente y bajo ASan/UBSan. GitHub `main` sigue en
`0ef1d60775ed96ac6901049092d26a125b9ccc5e`. Los cambios de ambas entregas
siguen siendo locales; esta carpeta no es un clon Git autenticado.

## Backend elegido

| Opción | Decisión para esta entrega |
| --- | --- |
| IR → C → GCC/Clang | Elegida, probada con GCC 13.3.0 en Linux x86_64. Toolchain disponible, ABI/objetos/optimizador existentes, C inspeccionable |
| LLVM directo | Viable después; no hay LLVM/Clang instalado aquí. Añade integración y dependencia sin resolver primero tipos o frontend |
| Backend propio | Requeriría registros, ABI, enlazado y formato de objetos; no aporta una ventaja comprobada para este hito |
| VM/JIT | No cumple el hito de ejecutable AOT con menor trabajo; supondría otro runtime |

La decisión es concreta: mantener la IR propia y el emisor C. No hay un backend
LLVM implementado. Las comprobaciones aritméticas usan extensiones documentadas
`__builtin_*_overflow` de GCC, también presentes en Clang pero no probado aquí.
Por ello este backend no se anuncia como C11 puro portable a cualquier compilador.
Referencias primarias: [LLVM frontend](https://llvm.org/docs/tutorial/MyFirstLanguageFrontend/)
y [overflow de GCC](https://gcc.gnu.org/onlinedocs/gcc/Integer-Overflow-Builtins.html).

## Etapas y archivos

| Archivo | Responsabilidad nueva o cambio |
| --- | --- |
| `natc/model.py` | Tokens con archivo/línea/columna, nodos AST y diagnósticos |
| `natc/lexer.py` | Lexer completo de la fuente; comentarios, literales e INDENT/DEDENT |
| `natc/parser.py` | Parser de sentencias y expresiones con precedencia; produce AST |
| `natc/sema.py` | Resolución de nombres, inferencia local y comprobación de tipos |
| `natc/ir.py` | IR de tres direcciones tipada, temporales, etiquetas y saltos explícitos |
| `natc/cgen.py` | Emite C desde la IR; no vuelve a analizar texto Nat |
| `natc/runtime.h` | Aritmética comprobada e input decimal; se integra en el C generado |
| `natc/__main__.py`, `natc/__init__.py` | CLI check/emit-ir/emit-c/build; invocación del compilador sin shell |
| `tests/test_compiler.py` | 18 pruebas nuevas, con subcasos y comprobación diferencial |
| `examples/compiled/suma.nat` | Programa que suma enteros y demuestra Int/Bool/Texto |
| `benchmarks/native_kernel.{nat,c,py,rs}` | Algoritmo equivalente; C++ compila el fuente C en modo C++17 |
| `benchmarks/native_run.py` | Construye los programas, verifica salida y mide por separado |
| `Makefile` | `test` ejecuta las dos suites; nuevos test-compiler/native-example/benchmark-native |
| `README.md` | Punto de entrada actualizado; documentos de primera entrega conservados |
| `docs/results/compiled/` | Logs y muestras reales de esta entrega |

No se cambió `nat.c`, ningún ejemplo anterior ni el parche de la primera entrega.
El frontend nuevo es independiente y no comparte el parser textual del intérprete;
la migración conserva el ejecutor anterior como modo de compatibilidad separado.

## Semántica implementada

- Int: entero con signo de 64 bits, almacenado como `int64_t`, sin cajas ni texto.
  `+`, `-` binario/unario y `*` comprueban desbordamiento también con `-O2`.
  `%` es resto truncado hacia cero, con signo del dividendo: `-7 % 3 = -1`.
  Resto por cero termina con diagnóstico; `INT64_MIN % -1` da cero sin UB.
- Bool: `verdadero`, `falso`, `no`, `y`, `o`; `y/o` tienen cortocircuito.
  Condiciones exigen Bool. Comparaciones ordenadas requieren Int; igualdad
  requiere tipos idénticos. No hay conversiones implícitas Int/Bool/Texto.
- Texto: literales UTF-8 inmutables, asignación, impresión e igualdad por bytes.
  Los literales tienen almacenamiento estático en el ejecutable; se guardan
  referencias `const char *`. Se rechaza NUL y escapes JSON inválidos. No hay
  concatenación, texto dinámico ni índices, por lo que no se introduce heap/RC.
- Variables: tipo inferido al inicializar y fijo en reasignaciones. En este
  subconjunto se declaran a nivel superior antes de usarlas dentro de bloques.
  Declaraciones nuevas dentro de bloques se rechazan explícitamente hasta
  implementar ámbitos y flujo de inicialización. Las ramas falsas se analizan.
- Sentencias: asignación, `imprimir`, `si`, `mientras`; bloques de cuatro espacios.
  Operandos evaluados de izquierda a derecha. Precedencia: paréntesis/unarios,
  `* %`, `+ -`, orden, igualdad, `y`, `o`; `no (a == b)` requiere esos paréntesis.
- `entrada_entero()` lee el único argumento de ejecución `argv[1]`: decimal con
  signo menos opcional, sin espacios, validando rango. Permite inputs de benchmark
  en ejecución para no convertir toda la carga en una constante de compilación.

Aún no hay listas, Float, funciones del usuario, retornos, `sino`, `/`, módulos
ni biblioteca de cadenas. El compilador los rechaza. El intérprete anterior
sigue ejecutando sus programas de cadenas/módulos. Las colecciones se aplazan
hasta implementar propietario, longitud y capacidad y probar sus operaciones;
no se presentan como valores disponibles en esta entrega.

Los errores estáticos incluyen archivo, línea y columna. Los chequeos de
runtime conservan la posición de la operación en la IR. El fallo de compilación
no reemplaza un ejecutable anterior. La traducción evita interpolar nombres o
texto del usuario como código C: usa IDs internos y literales escapados.
Esto no constituye una demostración de seguridad de memoria de todo Nat.

## Comandos exactos, desde la carpeta fuente

```sh
make test
make test-sanitize ASAN_OPTIONS=detect_leaks=0:halt_on_error=1
python3 -m natc check examples/compiled/suma.nat
python3 -m natc emit-ir examples/compiled/suma.nat -o build/suma.ir.json
python3 -m natc emit-c examples/compiled/suma.nat -o build/suma.c
python3 -m natc build examples/compiled/suma.nat -o build/suma
./build/suma 100
python3 benchmarks/native_run.py --output build/native-benchmark.json
```

Salida del ejemplo: `4950`, `verdadero`, `Nat compilado`, una por línea.
El último comando reproduce el benchmark; no descarga herramientas.
`--opt 0` y `--sanitize` permiten construir otra variante del ejecutable.
Los sanitizers del código generado también se ejecutan dentro de la suite nueva.
LeakSanitizer sigue pendiente: el detector falla al inspeccionar `/proc` aquí.

## Pruebas y resultados

59 pruebas pasan en `make test`: 41 anteriores y 18 nuevas. Los subcasos nuevos
incluyen lexer/posiciones, AST/precedencia, símbolos/tipos, IR/saltos, ejecutables,
cortocircuito, errores en ramas muertas, Unicode/escapes, entrada inválida,
bordes Int64, desbordamientos y preservación de salida al fallar. Además,
40 expresiones generadas con semilla 42 se contrastan con resultados calculados
en Python en tres configuraciones: O0, O2 y O2 con ASan/UBSan. Las cinco pruebas
de operaciones inválidas de runtime también usan ASan/UBSan. Las 41 anteriores
pasan de nuevo instrumentadas. No se detectó regresión en ese corpus.

La prueba inicial de negación del mínimo entero esperaba runtime, pero el
plegado de un literal lo rechazó correctamente al compilar. Se cambió el caso
a negar una variable Int64 mínima para ejercitar la comprobación de runtime.

Benchmark: 2.000.000 iteraciones de `x = (17*x + i) % 1000003`, `x=1`,
`i=0..n-1`. Datos suministrados al ejecutar, resultado verificado en cada corrida.
C/C++ y Nat incluyen checks de suma/producto; Python usa enteros arbitrarios,
pero los valores de esta carga caben en Int64. Rust usa checked_add/checked_mul.
Dos calentamientos y nueve muestras intercaladas con orden barajado, semilla 42.
Tiempo de pared con arranque incluido. Host AMD EPYC 9V74, Linux x86_64,
GCC/G++ 13.3.0 y Python 3.12.14; sin afinidad ni frecuencia controladas.
Las muestras, desviación, mínimos/máximos, hashes y opciones están en JSON.
Compilar Python aquí significa generar bytecode .pyc, no código máquina.
La compilación de Nat se desglosa entre frontend y GCC; cada tiempo de
compilación es una sola muestra y no permite comparar su variabilidad.


### Resultados medidos de esta corrida

| Implementación | Compilación, s | Ejecución mediana, ms | Desv. estándar, ms |
| --- | ---: | ---: | ---: |
| Nat | 0.090946 | 10.326 | 1.549 |
| C | 0.048048 | 10.572 | 1.011 |
| C++ | 0.065976 | 10.761 | 1.196 |
| Rust | No disponible | No medido | — |
| Python | 0.034648 | 282.491 | 23.445 |

Estos resultados describen una sola carga; no demuestran superioridad general.

## Qué falta y siguiente paso

La cadena Nat → AST tipado → IR → C → enlazado → ejecutable está implementada
para el subconjunto anterior. GCC aporta optimizaciones y generación de máquina;
Nat aún no implementa optimizaciones propias, objetos/ABI propios ni LLVM.
La portabilidad más allá del host y la seguridad global no se han demostrado.

Siguiente unidad concreta: ámbitos léxicos y funciones con parámetros/retorno
Int/Bool/Texto anotados; añadir instrucciones call/return a la IR y pruebas de
recursión, inicialización y vida útil. Después, colecciones con representación
explícita y pruebas de límites/propiedad, antes de ampliar el runtime dinámico.
