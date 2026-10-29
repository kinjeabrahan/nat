# Funciones tipadas y base nativa: misión implementada

## Estado inicial y Git

La inspección encontró `natc/` (Python → IR → C/GCC) y el intérprete de
compatibilidad `nat.c`; el remoto seguía en `fd64d424e604eec93ef2bf0f6cc235d76ffbb210`.
La carpeta local contenía las correcciones semánticas de la entrega 3, sin `.git`.
No estaban `asmgen.py`, `nat_wc.nat` ni `test-useful`; el intento de ejecutar ese
objetivo falló. Por eso la misión incorpora la ruta nativa disponible ahora y
no anuncia una reutilización de archivos que esta copia no tenía.

Se verificaron las 57 pruebas legadas y las 19 del compilador antes de modificar
código. No había AGENTS.md. La copia original quedó intacta. Se preparó un
repositorio local aislado con el objeto exacto del commit remoto y su árbol,
verificados por SHA, como historial superficial de profundidad uno. Un commit
separado `chore(snapshot): preserve pre-existing local Nat deliveries` conserva
el estado local previo; no atribuye esos cambios a la nueva funcionalidad.
El trabajo nuevo está en `feat/typed-functions`. No se ha configurado un remoto
para hacer push ni se ha escrito en GitHub. `.git/info/attributes` desactiva la
normalización local para conservar exactamente los blobs importados.

## Problema resuelto y archivos

La IR previa representaba un único cuerpo global, sin firmas, llamadas del
usuario ni ubicaciones independientes por activación. La IR v2 y el frontend
ahora representan funciones, parámetros, bindings léxicos, retornos y CFG.

| Archivos | Cambios |
| --- | --- |
| `natc/lexer.py`, `parser.py`, `model.py` | `func`, parámetros/retorno anotados, argumentos, `retornar`, `sino`; binding resuelto separado del nombre fuente |
| `natc/sema.py` | Firmas predeclaradas, recursión mutua, ámbitos por función/bloque, tipos y retorno en todas las rutas |
| `natc/ir.py` | Programa v2 con entrada y funciones; firmas, parámetros, tipos, call/return y etiquetas; validador común |
| `natc/cgen.py`, `runtime.h` | Funciones C y prototipos, contexto de entrada, límites de activación, lectura de bytes y errores de salida |
| `natc/asmgen.py`, `asm_runtime.s` | Código nativo Linux x86_64, marcos locales por llamada y runtime por syscalls sin C/libc |
| `natc/__main__.py` | `--backend asm`, `emit-asm`, as/ld, conservación atómica de ejecutables existentes |
| `tests/test_functions.py`, `test_compiler.py` | Pruebas de funciones, tipos, ABI, recursión, scopes y contrato IR; actualización de pruebas de la interfaz IR interna |
| `herramientas/nat_fuente.nat`, `examples/datos/fuente.txt` | Aplicación de preanálisis real y entrada reproducible |
| `tests/test_source_tool.py` | Referencias independientes para estadísticas y clasificación de los 256 bytes, más errores de E/S |
| `Makefile`, `README.md` | Comandos y documentación sincronizados |

El intérprete y la ruta C se conservan. Los documentos anteriores son históricos;
esta nota describe el comportamiento actual. No se reescribió otro lenguaje.

## Sintaxis y reglas implementadas

```nat
func es_blanco(b: Int) -> Bool:
    retornar b == 32 o (b >= 9 y b <= 13)

func es_inicio(b: Int) -> Bool:
    retornar (b >= 65 y b <= 90) o (b >= 97 y b <= 122) o b == 95
```

Los tipos disponibles de parámetros/retorno son Int64 (`Int`), Bool y Texto
inmutable. Hasta seis parámetros; se admiten llamadas anidadas, retorno de
Texto, recursión directa/mutua, `si/sino`, bucles y cortocircuito. Los argumentos
se evalúan de izquierda a derecha y sus resultados se guardan antes de llamar.
Las firmas se conocen antes de analizar cuerpos, por lo que no hacen falta
prototipos Nat ni ordenar funciones por dependencias.

Cada función posee sus variables. Los bloques introducen ámbitos léxicos; una
asignación actualiza un binding visible del mismo tipo o crea uno en el ámbito
actual. No existe una forma de ocultar deliberadamente un binding visible.
Los nombres creados dentro de un bloque no escapan de él. Las funciones no
capturan variables de módulo ni de otras funciones: los datos se pasan como
parámetros. No hay cierres, funciones anidadas, procedimientos Unidad del usuario,
sobrecarga, argumentos opcionales, más de seis parámetros, módulos o colecciones.
Los nombres de funciones/intrínsecas no se pueden usar como bindings de datos.

Se rechazan firmas/llamadas incorrectas, variables no inicializadas, tipos de
retorno incompatibles y caminos sin retorno. Los bucles no se consideran por sí
solos una prueba de retorno, aunque su condición sea una constante verdadera.
Las ramas se comprueban incluso si no se ejecutan. Cambió intencionalmente una
prueba anterior: declarar dentro de un bloque ahora es válido, pero leer ese
nombre fuera continúa siendo un error. La serialización IR cambió a versión 2;
no se ofrece un lector compatible de la IR v1.

## Contrato IR y generación

El programa contiene `version: 2`, `entry` y `functions`. Cada cuerpo contiene
`name`, `params` (IDs y tipos), `return_type`, `types` e `instructions` con
ubicaciones de origen. Los IDs vN representan bindings y tN temporales; son
locales a su función. `call` contiene nombre de destino y valores de argumentos;
`return` contiene un valor tipado. Las funciones no consultan nombres fuente
en los backends.

El validador compartido comprueba declaraciones/tipos, firmas y llamadas,
retornos, etiquetas únicas, destinos de salto y caída de caminos sin retorno.
El frontend comprueba la inicialización y los ámbitos; no se presenta este
validador como un verificador completo de IR arbitraria no confiable.

ASM usa el subconjunto entero/puntero de System V AMD64 para Linux: parámetros
en RDI, RSI, RDX, RCX, R8, R9 y resultado en RAX. Cada activación guarda RBP y
reserva un marco múltiplo de 16 bytes. Los valores se derraman a slots de ocho
bytes por activación; ninguna variable local depende de almacenamiento global.
RSP queda alineado a 16 antes de cada call; los helpers que anidan llamadas
ajustan la pila. Los registros callee-saved se preservan; R12 conserva el contexto
inmutable de arranque usado para `entrada_entero()`. No hay FFI exportada.
Referencia: [x86-64 psABI](https://gitlab.com/x86-psABIs/x86-64-ABI).

No hay asignador de registros ni optimizador propio. Se permiten como máximo
512 valores por cuerpo (4096 bytes de slots; el marco se redondea a 16), y 128
activaciones simultáneas incluyendo la entrada. El límite de profundidad produce
un diagnóstico en ambos backends. No constituye una garantía para cualquier
configuración de stack del sistema. No se promete seguridad de memoria global.
Texto solo procede de literales estáticos y sus copias/parámetros/retornos;
no se devuelven referencias a buffers locales ni se introduce heap.

## Demostración reproducida

`herramientas/nat_fuente.nat` tiene cinco funciones: clasificación de blancos,
inicios de identificador y dígitos, `clase_ascii`, y el analizador con contadores
locales. Procesa stdin hasta EOF, devuelve el total de bytes y muestra métricas.
El shell abre el archivo; Nat no tiene todavía una API `abrir(ruta)`.

Desde la raíz del repositorio:

```sh
python3 -m natc build herramientas/nat_fuente.nat --backend asm -o build/nat-fuente
./build/nat-fuente < examples/datos/fuente.txt
python3 -m natc build herramientas/nat_fuente.nat -o build/nat-fuente-c
./build/nat-fuente-c < examples/datos/fuente.txt
python3 -m natc emit-ir herramientas/nat_fuente.nat -o build/fuente.ir.json
python3 -m natc emit-asm herramientas/nat_fuente.nat -o build/fuente.s
```

Entrada: `alpha beta_2\n123 + _x\n`, 22 bytes. Resultado observado, idéntico por
las dos rutas:

```text
lineas
2
palabras
5
identificadores_ascii
3
bytes
22
```

Los identificadores son candidatos ASCII `[A-Za-z_][A-Za-z_0-9]*` en un flujo,
sin excluir cadenas o comentarios. No se anuncia tokenización completa.
Las palabras usan los seis blancos ASCII; las líneas cuentan LF, no fragmentos
sin LF final. Los bytes NUL y 128..255 son datos válidos de entrada.

## Pruebas, dependencias y diferencias

```sh
make test-functions
python3 -m unittest discover -s tests -p test_source_tool.py -v
make test
```

Resultados: 57 pruebas legadas y 19 del compilador pasan, más 11 de funciones y
3 de la herramienta (con subcasos). Se ejecutaron binarios reales de ambos
backends: seis argumentos, llamadas anidadas, Fibonacci, recursión mutua,
variables locales independientes, Bool/Texto, bucles, errores estáticos,
desbordamientos y límite de profundidad. Un programa recursivo C se ejecutó
con ASan/UBSan, sin detección de fugas. No se instrumentó el ASM con sanitizers.
El clasificador Nat se comparó con una referencia independiente para los 256
bytes en ambos backends; las métricas se contrastaron con regex y operaciones
sobre bytes de Python. También se comprobaron stdin cerrado y `/dev/full`.

La ruta nativa se construyó con PATH limitado a as/ld, sin GCC accesible.
`file`/`readelf` verifican ELF estático sin sección dinámica. La prueba inicial
halló que GCC convierte la advertencia sintáctica de recursión infinita en error;
se desactiva específicamente esa advertencia en C generado porque Nat permite
recursión con una trampa de profundidad comprobada. El resto de advertencias
sigue tratándose como error. No se afirma un nuevo resultado de rendimiento.

| Backend | Construcción | Ejecución y límites |
| --- | --- | --- |
| C | Python 3 + GCC 13.3 probado; C emitido y runtime C | libc; optimización O0/O2 y ASan/UBSan disponibles |
| ASM | Python 3 + GNU as y ld; sin emitir C ni invocar GCC | Linux x86_64; sin libc, Python ni cargador dinámico; sin optimizador ni sanitizers |

`--opt` y `--sanitize` son exclusivos de C. La ruta ASM no se probó en otros
sistemas/arquitecturas ni se adapta la convención Linux a Windows por suposición.
Python y binutils siguen siendo herramientas externas, con sus propias
implementaciones/dependencias. La emisión propia de objetos ELF no existe aún.

## Componente Nat y bootstrap

El componente viable implementado es el clasificador de bytes ASCII: funciones
puras escritas en Nat, sin heap ni dependencias más allá de Int/Bool/call/return.
Se validó su comportamiento completo por bytes y se usa en una herramienta real.
No está sustituyendo automáticamente al lexer Python.

Bootstrap concreto: (1) fijar esta semilla Python y sus commits; (2) compilar y
comparar componentes Nat, como el clasificador; (3) añadir Bytes con propiedad,
longitud e índices seguros para lexemas y tokens, y migrar el lexer contrastando
tokens/ubicaciones; (4) migrar parser, tipos e IR por componentes; (5) compilar
un compilador Nat con la semilla, producir las siguientes generaciones y comparar
IR normalizada/corpus y binarios cuando la construcción sea determinista.
Solo (1) y el primer componente de (2) están conseguidos. No hay self-hosting.

Siguiente unidad prioritaria: Bytes con longitud e índices comprobados para
almacenar lexemas/tokens, con una política explícita de vida útil. Las funciones
actuales ya permiten organizar esa implementación sin volver al estado global.
