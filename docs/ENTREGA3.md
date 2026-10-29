# Entrega 3: semántica del intérprete de compatibilidad

**Completado:** corrección de nombres, literales, reconocimiento de instrucciones,
validación estructural de bloques y rutas. No se declara terminado el plan
maestro ni implementadas funciones, distribución Windows o autocompilación.

## Estado comprobado antes de editar

GitHub avanzó a `fd64d424e604eec93ef2bf0f6cc235d76ffbb210`, mensaje `nat V1.0`.
Contiene las dos entregas previas. Se inspeccionaron árbol, historial, fuentes,
README, pruebas y Makefile; los hashes coinciden con la copia de trabajo salvo
los finales de línea de `nat.c`. Se conserva una base exacta del commit para
verificar el parche. No hay AGENTS.md en el árbol recibido.

`nat.c` es el intérprete activo de compatibilidad, con valores de texto, tabla
global compartida por archivos y límites de recursos. `nat_v01.c` es histórico.
`natc/` es el compilador de arranque Python con AST, tipos, IR, emisor C y GCC.
Ambos pertenecen al mismo proyecto. **La base principal para nuevas capacidades
es `natc/`; el intérprete queda como compatibilidad**, sin promesa de equivalencia
de todos los programas entre ambos modos.

Se reprodujeron antes del arreglo: identificador inexistente impreso como texto,
comilla sin cerrar aceptada, dos literales adyacentes unidos, diagnóstico incorrecto
de `a==b` y sangría adicional ejecutada sin un bloque. El JSON previo conserva
entradas, salidas y códigos reales. Un identificador con prefijo `imprimirx`
ya funcionaba: se conserva como control de no regresión, no se anuncia como bug.

## Archivos y cambios

| Archivo | Motivo |
| --- | --- |
| `legacy_lex.h` (nuevo) | Tokens de identificadores, palabras reservadas, enteros decimales, cadenas y delimitadores; validación y decodificación de escapes |
| `nat.c` | Despacho por tokens completos; resolución estricta; validación de sangría/cadenas antes de ejecutar cada archivo; rutas no vacías; checks de formato; `_Noreturn` en diagnósticos; retirada de include innecesario |
| `natc/parser.py` | Diagnóstico explícito de destinos reservados también en el compilador principal |
| `tests/test_nat.py` | 16 pruebas semánticas nuevas con subcasos; se mantienen las 41 anteriores |
| `tests/test_compiler.py` | Prueba nueva para los 12 destinos reservados |
| `Makefile` | El header nuevo forma parte de las dependencias, también para sanitizers |
| `README.md`, `docs/COMPILADOR.md` | Identifican la implementación principal y actualizan el estado Git antes descrito como local |
| `docs/ENTREGA3.md`, `docs/results/semantics/` | Entrega breve, reproducciones y resultados |

No se eliminó ningún archivo ni se reescribió el compilador. El C modificado usa
LF como la revisión remota actual, evitando cambios de finales de línea en el parche.

## Semántica que ahora funciona

Las palabras reservadas son `si mientras imprimir verdadero falso y o no func
retornar leer sino`, coincidentes con el conjunto del parser principal. Ninguna
puede ser destino de asignación. Un prefijo como `imprimirx` sigue siendo un
identificador normal. Las comparaciones `==` y `!=` no se confunden con `=`.

Un nombre debe estar definido antes de leerse durante la ejecución del intérprete.
`imprimir nombr` falla indicando el nombre, archivo y línea. Las cadenas necesitan
comillas; no hay fallback a texto para expresiones desconocidas. Se conserva el
caso de enteros decimales `-?[0-9]+` y constantes `verdadero/falso` como texto en
el modo legado: no se les atribuyen tipos nativos en ese modo.

Se comprueba el cierre del literal y se rechaza contenido sobrante. Escapes
admitidos por compatibilidad: `\"`, `\\`, `\n`, `\t`; otros escapes fallan.
Se conserva el contenido decodificado y el límite de 255 bytes del valor, sin
truncar. Los tokens de ruta tienen capacidad separada del valor, manteniendo las
rutas que caben en una línea fuente. Rutas vacías o con LF/tab decodificados se
rechazan antes de abrir archivos. Los fallos de apertura siguen siendo distintos
de los de lectura y los de análisis.

Los bloques requieren exactamente cuatro espacios adicionales tras `si/mientras`.
Los tabuladores de sangría y niveles no múltiplos de cuatro se rechazan; los
comentarios y blancos no forman cuerpos. Se detectan bloques sin cuerpo y
sangría adicional sin cabecera. Las cadenas y la estructura se revisan antes de
los efectos de cada archivo, incluso en ramas que no se ejecutan.

**Cambios intencionales de compatibilidad:** texto sin comillas, escapes desconocidos,
comillas mal formadas y sangría antes tolerada ahora son errores. Los programas
que utilizaban tabs para sangrar deben convertirlos a cuatro espacios. El
compilador principal ya exigía espacios; su conjunto de escapes JSON es más
amplio que el legado y no se ha reducido en esta entrega. Ambos comparten los
cuatro escapes anteriores. Las diferencias son explícitas y el legado no se
ampliará para mantener dos gramáticas en paralelo.

## Validación reproducible

Desde `fuente/`:

```sh
make test
make test-sanitize ASAN_OPTIONS=detect_leaks=0:halt_on_error=1
gcc -std=c11 -Wall -Wextra -Wpedantic -Werror -fanalyzer -c nat.c -o build/nat-analyzer.o
python3 -m natc build examples/compiled/suma.nat -o build/suma
./build/suma 100
```

Resultados reales: **57 pruebas del intérprete y 19 del compilador pasan** (76
métodos, con subcasos). Las 57 del intérprete pasan también con ASan/UBSan.
La suite del compilador conserva sus ejecuciones nativas instrumentadas.
GCC `-fanalyzer -Werror` terminó con código 0 y sin diagnósticos. No se detectó
regresión en el corpus anterior. LeakSanitizer sigue sin poder ejecutarse por
la restricción conocida de `/proc`; no se afirma ausencia de fugas.

No se repitieron los benchmarks: este hito corrige semántica y no anuncia
mejora de velocidad. Las cifras anteriores no miden el intérprete corregido.
La prevalidación y el lexer añaden trabajo cuyo coste no se ha medido aquí.

## Pendiente y siguiente paso

La estructura del legado sigue siendo ejecución directa; no tiene análisis de
nombres estático de todas las ramas, AST ni tipos reales. Los módulos legados
comparten variables globales. La validación previa de un archivo incluido ocurre
cuando se lo carga, no se preanaliza todo el grafo de inclusiones. Permanece la
limitación conocida de una última línea de exactamente 511 bytes sin LF. No se
promete recuperación de errores ni seguridad de memoria global.

El backend principal conserva la cadena Python (compilador) → C emitido → GCC →
ejecutable; este último necesita libc y no Python. Windows x64 es el objetivo
solicitado de distribución, pero este host es Linux y no tiene MinGW ni un
entorno Windows de pruebas: no se entrega un binario Windows sin verificar.
No se ha implementado instalador, CLI nueva, módulos nativos ni backend propio.

Siguiente unidad: ámbitos léxicos y funciones tipadas en `natc/`, con parámetros,
retorno e instrucciones call/return en la IR, antes de colecciones dinámicas.
Los programas nuevos deben dirigirse a ese compilador. La transición a funciones
no se hará añadiendo otro reconocimiento textual al intérprete legado.

Los cambios de esta entrega permanecen locales: no se crearon commits, pushes,
publicaciones ni modificaciones remotas.
