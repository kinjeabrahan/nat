# Nat: auditoría técnica y primera mejora

Fecha: 29 de octubre de 2026. Repositorio privado: `kinjeabrahan/nat`.
Base inspeccionada: `0ef1d60775ed96ac6901049092d26a125b9ccc5e`, mensaje
`nat v0.3.0`. Esta entrega contiene trabajo local; GitHub no se ha modificado.

## 1. Resultado y alcance

Nat tiene una base aprovechable para ejecutar programas pequeños con cadenas,
asignaciones, condiciones, bucles e inclusión relativa de archivos. Todavía no
es un compilador ni tiene enteros, tipos estáticos, funciones del usuario o
colecciones. El camino recomendado es conservar esa base como referencia de
compatibilidad y construir un frontend separado con tipos y generación nativa
mediante un compilador existente.

Se corrigió un acceso fuera de límites en el análisis de argumentos. Hay 41
pruebas automáticas que pasan, tanto con compilación normal como con
AddressSanitizer y UndefinedBehaviorSanitizer. La detección de fugas quedó
pendiente por una limitación comprobada del entorno. Esto valida el arreglo
y los casos ejercitados; no demuestra seguridad de memoria para todo Nat.

## 2. Procedencia e historial

La búsqueda en los repositorios conectados identificó `kinjeabrahan/nat`,
privado y con rama por defecto `main`. Su historial disponible tiene dos commits:

| Commit | Fecha | Mensaje |
| --- | --- | --- |
| `5d4663b0d7fb5429dd3504e19d8172f0b56918fb` | 2026-10-29 | Initial commit |
| `0ef1d60775ed96ac6901049092d26a125b9ccc5e` | 2026-10-29 | nat v0.3.0 |

Se inspeccionaron el árbol recursivo, los dos registros de historial, ambos
fuentes C y todos los programas Nat. No había AGENTS.md, Makefile, README,
runner de pruebas ni configuración de CI en el árbol recibido. Los archivos
de texto se recuperaron de la revisión fija y se verificaron con sus hashes
de blob Git, conservando sus finales de línea originales.

La terminal no dispone de credenciales de Git para el repositorio privado;
el intento de clonación terminó solicitando un usuario. La copia de trabajo
se obtuvo mediante la conexión GitHub y es una instantánea local, no una rama
Git. No se generaron commits ni se fabricó historial. El binario `nat.exe`
no pudo descargarse mediante la interfaz de texto; queda fuera de la auditoría
binaria y del paquete de cambios, sin proponer su eliminación.

## 3. Arquitectura real y capacidades

`nat.c` reúne toda la implementación actual. `nat_v01.c` es un prototipo
anterior independiente; no forma parte del ejecutable compilado para las
pruebas. Los archivos `nat.nat` e `interprete*.nat` asignan variables,
imprimen mensajes e incluyen otros archivos: no tokenizan ni interpretan
fuente Nat. No hay evidencia de implementación metacircular ni self-hosting.

La ejecución actual hace esta secuencia: cargar hasta 500 líneas; guardar sus
bytes; recorrer instrucciones reconociendo prefijos; resolver operandos como
texto; ejecutar directamente y volver a analizar las líneas al repetir bucles.
Las funciones C están parcialmente organizadas por responsabilidades, pero no
existen tokens persistentes, parser independiente, AST, análisis semántico,
IR ni generación de código.

| Capacidad | Estado comprobado |
| --- | --- |
| Asignación y copia de variables | Sí; todos los valores son cadenas terminadas en NUL |
| Impresión y comentarios | Sí; soporta escapes de comilla y barra inversa |
| Condiciones | `si`, igualdad y desigualdad textual; sin `sino` |
| Bucles | `mientras`, reevaluando la condición; límite global de un millón de iteraciones |
| Archivos | `leer` ejecuta otro programa, relativo al archivo que lo incluye |
| Cadenas | `longitud`, `caracter`, `buscar`; posiciones y longitud en bytes |
| Diagnósticos | Normalmente archivo y línea; sin columna; algunos errores generales carecen de origen |
| Números, booleanos y operaciones | No hay valores de esos tipos ni evaluación aritmética |
| Funciones del usuario, retorno y recursión | Pendientes |
| Listas, registros y ámbitos léxicos | Pendientes; variables en una tabla global compartida |
| Compilación nativa, paquetes y concurrencia | Pendientes |

`imprimir 1 + 2` produce literalmente `1 + 2`. Un nombre no definido se trata
como texto en vez de generar un error. El intérprete acepta imprimir una
comilla sin cerrar. `longitud("ñ")` produce 2 para esa entrada UTF-8.
Estas observaciones están separadas de las capacidades propuestas.

Las restricciones actuales incluyen 100 variables, nombres de 63 bytes y
valores de 255 bytes. Cada archivo reserva 500 × 512 bytes para líneas,
independientemente de su tamaño; la profundidad máxima de inclusión es 32.
Son límites de prototipo, no un diseño adecuado para aplicaciones grandes.

## 4. Línea base ejecutada

Se compiló el `nat.c` sin modificar con:

```sh
gcc -std=c11 -Wall -Wextra -Wpedantic -O2 nat.c -o nat-baseline
```

No hubo advertencias. Se ejecutaron los nueve archivos `.nat` del repositorio:

| Archivo | Resultado antes de modificar |
| --- | --- |
| `pruebas/bucle.nat` | Correcto |
| `pruebas/cadenas.nat` | Correcto |
| `pruebas/interprete.nat` | Correcto; incluye su bucle relativo |
| `holamundo.nat` | Correcto; incluye subprograma |
| `subprograma.nat` | Correcto |
| `bucle_v01.nat` | Error: falta `:` y usa bloques antiguos |
| `interprete_v01.nat` | Error: falta `:` |
| `nat.nat` | Error: falta `:` |
| `interprete.nat` | Imprime el arranque y falla buscando `bucle.nat` en la raíz |

Los tres archivos de `pruebas/` eran ejemplos ejecutables sin aserciones.
El runner nuevo convierte sus salidas en comprobaciones y añade casos de
módulos, anidamiento, comentarios, escapes, índices, recursos y errores.
Las 33 pruebas del grupo de compatibilidad pasaron contra la base original
antes de cambiar el intérprete.

## 5. Defectos y deuda priorizados

Las referencias de línea de esta tabla corresponden al archivo original del
commit inspeccionado; después del pequeño arreglo algunas se desplazan una línea.

| Prioridad | Evidencia e impacto | Acción |
| --- | --- | --- |
| P0, corregido | `args[2][MAX_LINEA]` en `nat.c:515`; la escritura de `nat.c:575` usa la tercera fila antes de comprobar el número de argumentos | Mover la comprobación antes de cualquier acceso a la fila; ocho regresiones |
| P0 si se distribuye | `nat_v01.c` mantiene copias y lecturas sin límites suficientes, y carga líneas sin comprobar la capacidad del arreglo | Identificarlo como histórico; compilar solo `nat.c`; no distribuirlo como alternativa segura |
| P1 | `resolver_operando`, especialmente `nat.c:715` y `nat.c:730`, convierte nombres desconocidos y expresiones mal formadas en texto | Separar tokens de nombres/literales; errores por variable inexistente y comillas no cerradas |
| P1 | Se permite una indentación adicional sin bloque y no se valida toda la sintaxis de ramas no ejecutadas | Lexer con pila de indentación y parseo completo antes de ejecutar |
| P1 | Una tabla global combina todas las variables y archivos; no hay resolución de nombres ni contratos de módulo | Entornos explícitos y ámbitos; pruebas de colisiones y dependencias |
| P1 | Cuatro ejemplos no funcionan con la implementación actual | Migrarlos con pruebas de salida en un cambio separado, o marcarlos como históricos |
| P2 | `nat.c:302` consulta `feof` antes de intentar leer más; rechaza una última línea de exactamente 511 bytes sin salto final | Probar bordes de longitud con y sin LF y corregir el lector sin truncar |
| P2 | Errores terminan el proceso desde funciones internas; no hay recuperación ni limpieza estructurada al fallar | Contexto de ejecución y resultados de error; necesarios para REPL, editor y biblioteca embebida |
| P2 | Límites fijos, cadenas por bytes y comprobaciones repetidas al ejecutar cada línea | Valores con longitud/capacidad y AST; medir antes de optimizar |
| P2 | `nat.exe` está versionado sin una construcción reproducible documentada | Documentar toolchain, reconstruir y verificar equivalencia antes de distribuir; no eliminado aquí |

No se ha realizado fuzzing exhaustivo ni se atribuye explotación práctica a
los problemas. El desbordamiento sí se reprodujo, no es una conjetura.
El coste de volver a analizar bucles es una hipótesis fundada en la estructura
del código; todavía no hay perfil CPU que cuantifique ese coste.

## 6. Primera mejora implementada

Entrada que activa el problema:

```nat
imprimir buscar("Nat", "a", "extra")
```

UBSan en el original notificó `index 2 out of bounds for type 'char [2][512]'`.
La comprobación anterior solo se ejecutaba al encontrar una coma o el final;
los bytes del tercer argumento ya se habían escrito en una fila inexistente.
Ahora se comprueba `cantidad >= 2` al comenzar cada iteración del escáner,
antes de leer o escribir esa fila. Se conserva el límite y el mensaje de error.

El cambio de `nat.c` mueve esa condición; no añade nuevas capacidades del
lenguaje. Se agregan Makefile, pruebas, benchmark y documentación. No se
reescribieron ni eliminaron los otros archivos originales.

| Comprobación | Original | Con arreglo |
| --- | --- | --- |
| Grupo de compatibilidad | 33/33 pasan | 33/33 pasan |
| Regresiones de argumentos bajo sanitizers | 7 fallan por UB; 1 caso de coma final ya era correcto | 8/8 pasan |
| Suite completa normal | No se presenta como correcta: contiene el defecto | 41/41 pasan |
| Suite completa ASan + UBSan | No se presenta como correcta: contiene el defecto | 41/41 pasan, detección de fugas desactivada |
| LeakSanitizer | Falla el propio detector al inspeccionar `/proc` | Pendiente en un host compatible |

Los registros están en `docs/results/`. Que una entrada termine con código 1
no basta para pasar: las pruebas exigen el mensaje Nat esperado y rechazan
diagnósticos de los sanitizers. Se usaron GCC 13.3.0, C11, `-O2` para pruebas
normales y `-g -O1 -fsanitize=address,undefined` para instrumentación.

## 7. Comparación arquitectónica

Esta tabla es una evaluación de ingeniería para Nat, no una medición de
implementaciones que todavía no existen. Los costes son relativos al proyecto.

| Alternativa | Rendimiento potencial | Desarrollo y mantenimiento | Portabilidad y depuración | Self-hosting |
| --- | --- | --- | --- | --- |
| A. Intérprete tradicional | Limitado por despacho y representación; útil como referencia | Menor coste inicial; el ejecutor actual necesita frontend separado | C11 portable; diagnósticos fáciles si se guardan spans | Viable al tener datos/funciones, pero lento para compilar proyectos grandes |
| B. Bytecode y VM | Puede reducir reparsing y despacho; no elimina por sí solo coste dinámico | Coste medio: formato, VM, verificador y depurador propios | VM portable; requiere mapear instrucciones a fuente | Viable, con VM y runtime como dependencias |
| C. Nativo con backend existente | Alto si tipos, valores e IR exponen bien las operaciones | Coste medio del frontend; reutiliza optimizador y generación de máquina | Mediante C emitido o LLVM; cuidar ABI, ubicaciones y toolchain | Buen encaje: Nat puede emitir C o IR |
| D. Nativo con backend propio | Alto en teoría; calidad inicial y alcance inciertos | Coste muy alto: registros, ABI, objetos, optimizaciones y varias CPU | Cada plataforma aumenta trabajo de mantenimiento y depuración | Posible, pero retrasa el bootstrap y la corrección |
| E. Híbrido con intérprete/JIT/AOT | Puede combinar arranque y rendimiento; ventaja pendiente de demostrar | Más complejidad, cachés, transiciones y compatibilidad de modos | JIT y depuración aumentan dependencias | Posible; no justifica mantener dos semánticas distintas |

**Recomendación:** C, compilación nativa anticipada con infraestructura existente.
Primero emitir C11 desde una IR propia pequeña y tipada, y usar GCC/Clang.
Permite aprovechar el entorno actual y hace accesible el bootstrap: escribir
un emisor de texto en Nat resulta más sencillo que implementar un asignador
de registros y un formato de objetos. El compilador Nat seguirá siendo
responsable de tipos, ámbitos y seguridad; emitir C no transfiere esas tareas.

Mantener un intérprete del AST tipado como referencia de desarrollo. No añadir
una VM ni un JIT por defecto. Si los perfiles o la depuración muestran límites
concretos del emisor C, evaluar un backend LLVM sobre la misma IR mediante un
prototipo medido. LLVM ofrece infraestructura de optimización y código nativo
[1, 2]; eso no demuestra que Nat ya tenga su rendimiento. C y LLVM tienen UB:
los chequeos de Nat deben ocurrir antes de operaciones inválidas del backend.

## 8. Tubería y rendimiento

Tubería propuesta: archivo UTF-8 → lexer con indentación → parser → AST con
spans → resolución de módulos y nombres → inferencia y comprobación de tipos
→ IR tipada con flujo de control → simplificaciones verificadas → C11 →
compilador del sistema → enlazado con runtime → ejecutable nativo.

Cada etapa tendrá una entrada y salida inspeccionable, pruebas independientes
y diagnósticos `archivo:línea:columna`. El frontend analizará también los
bloques que no se ejecuten. Tokens/AST/IR usarán arenas con propietario único;
los entornos y errores dejarán de depender de estado global del proceso.

Primeros objetivos de optimización: enteros y Float sin cajas, llamadas
directas, variables con IDs en vez de búsquedas textuales y eliminación de
reparsing. Después, plegado de constantes y código muerto conservando errores
y orden de efectos. Dejar inlining, vectorización y optimización de máquina
al backend inicialmente. Especializar genéricos cuando existan; medir copias
y asignaciones antes de añadir eliminación de RC u optimizaciones de aliasing.

No introducir flags como `nsw`, `noalias` o fast-math sin justificar sus
precondiciones con la semántica Nat. La documentación LLVM explica que la
forma de la IR influye en sus optimizaciones [3]; seleccionar LLVM no sustituye
un frontend correcto ni un modelo de memoria definido.

### Medición inicial

Se preparó una misma carga de bucles y transiciones sobre dígitos en Nat, C,
C++, Rust y Python. Rust quedó pendiente por falta de compilador. Todos los
procesos medidos verificaron exactamente la salida `1`. Las fuentes y datos
crudos están incluidos; el método completo está en `benchmarks/README.md`.

Host: Linux x86_64, AMD EPYC 9V74, 9 CPU lógicas visibles; GCC/G++ 13.3.0,
Python 3.12.14. Dos calentamientos y nueve repeticiones por implementación,
rondas intercaladas y opciones `-O2` para los compiladores C/C++.

| Implementación | Mediana original, ms | Desv. estándar original, ms | Mediana después, ms | Desv. estándar después, ms |
| --- | ---: | ---: | ---: | ---: |
| Nat | 7.543 | 0.505 | 8.231 | 2.928 |
| C | 1.327 | 0.273 | 1.339 | 0.197 |
| C++ | 1.371 | 0.210 | 1.031 | 0.965 |
| Python | 17.181 | 1.415 | 15.329 | 3.520 |
| Rust | No medido | — | No medido | — |

Estas muestras incluyen el arranque del proceso. El algoritmo es el mismo;
las representaciones de estado y conversiones dependen de cada lenguaje.
No son un ranking general, no prueban un rendimiento superior a Python y no
permiten atribuir el cambio de tiempo de Nat al arreglo. No se afirma mejora
de velocidad ni ausencia de regresión de rendimiento con esta muestra.
El objetivo del arreglo es corregir memoria; evaluar su coste con un estudio
pareado más largo si el perfil posterior lo justifica.

La construcción del intérprete C tomó 0.252 s en la línea base y 0.224 s
después. No son tiempos de compilación de programas Nat. Los JSON separan
las compilaciones de los tiempos de ejecución de cada implementación.

## 9. Sintaxis, tipos y seguridad de memoria

El borrador detallado está en `ESPECIFICACION_PROPUESTA.md`. Se recomienda
tipado estático con inferencia local, parámetros y retornos anotados, tipos
Int de 64 bits, Float, Bool, Texto, Bytes y Lista[T]. Evitar un tipo dinámico
universal por defecto. Después, registros, tipos algebraicos, Opcion,
Resultado, genéricos monomorfizados y funciones como valores. Interfaces y
capturas complejas esperan necesidades reales. Las conversiones son explícitas.

Se propone comenzar con valores sin referencias mutables escapables: escalares
por valor, Texto inmutable y listas con copia al modificar almacenamiento
compartido. RC interno mantiene vivos los bloques; no expone liberación manual.
Los grafos del compilador usan IDs en arenas. El primer núcleo no admite
grafos cíclicos de referencias ni cierres con captura mutable. Añadirlos
obliga a decidir de nuevo cómo se recogen ciclos: RC solo no los resuelve [4].

| Estrategia | Evaluación para Nat |
| --- | --- |
| Propiedad y préstamos completos | Buen control de recursos; alto coste de especificación, análisis y aprendizaje. Reservar préstamos más adelante para necesidades demostradas |
| RC con valores e inmutabilidad | Sencillo para el núcleo propuesto; coste de contadores/copias; revisar ciclos si se añaden referencias |
| GC trazador | Simplifica grafos cíclicos; añade runtime y política de pausas/raíces. Alternativa si los usos reales lo requieren |
| Arenas y regiones | Adecuadas para tokens/AST/IR; no sustituyen la gestión de toda aplicación. Evitar IDs colgantes entre regiones |
| Gestión manual o punteros sin chequeos | No apropiados para el código ordinario; posibles más adelante detrás de una frontera explícita y auditada |

Errores a impedir estáticamente: nombres no resueltos, tipos incompatibles,
uso sin inicialización, retornos inconsistentes y acceso a variantes sin
comprobación. Errores a detectar durante ejecución si no son demostrables:
índices, desbordamientos, división por cero, capacidad y asignaciones fallidas.
Un optimizador solo eliminará chequeos cuando pruebe que son redundantes.

Todavía no existen garantías contra uso después de liberar, doble liberación,
aliasing inválido o carreras en toda la implementación. Deben validarse
invariantes del runtime, tamaños, índices, propiedad, traducción y FFI. La
futura frontera C requerirá wrappers de longitud, vida útil y errores;
`unsafe` no vuelve válidas operaciones indefinidas [5]. Concurrencia y
paralelismo esperan un modelo de memoria y transferencia bien especificado.

## 10. Hoja de ruta con criterios verificables

Se adelantan lexer/AST y diseño de seguridad: añadir funciones y listas sobre
el parser textual actual multiplicaría deuda. La seguridad se diseña desde
tipos y representación, aunque la validación intensiva tenga una fase propia.

| Orden | Entrega | Criterio de aceptación propuesto |
| --- | --- | --- |
| 1. Estabilización | Arreglo actual, runner, compilación y datos base | 41 pruebas y sanitizers sin hallazgos en los casos cubiertos; después cerrar P1 y comprobar fugas en otro host. Fase iniciada, no completada |
| 2. Especificación | Gramática, precedencia, tipos, errores, Unicode y compatibilidad | Cada regla aprobada tiene al menos un caso válido y uno inválido donde corresponda; lista explícita de rupturas frente a v0.3 |
| 3. Frontend | Lexer, parser y AST separados del ejecutor | Tokens/AST verificables; spans exactos; rechazar indentación y cadenas inválidas incluso en ramas no ejecutadas; conservar corpus válido |
| 4. Semántica y valores | Ámbitos, enteros, Float, Bool e inferencia local | Casos positivos/negativos de tipos; inicialización por flujo; bordes Int64 y errores numéricos iguales en debug y release |
| 5. Funciones y datos | Funciones, retorno, recursión, listas y registros | Fibonacci y recursión mutua; aislamiento de ámbitos; listas vacías anotadas; índices y copias con semántica definida |
| 6. Primer compilador | IR y emisor C con runtime pequeño | Mismo corpus en intérprete tipado y nativo; comparar salidas y fallos, incluidos al menos 30 programas generados con semilla fija; ejecutable independiente |
| 7. Validación de memoria | Invariantes de valores, RC/arenas y frontera nativa | Sanitizers y detector de fugas en host compatible; fallos de asignación inyectados; corpus generado y al menos una hora de fuzzing sin hallazgos sin resolver; revisión del modelo, sin tomar las pruebas como demostración completa |
| 8. Rendimiento | Ampliación de benchmarks y perfiles | Incluir todas las categorías cuando existan; ≥10 muestras en host controlado; datos y versiones guardados; perfilar antes y después; criterio de mejora declarado por carga |
| 9. Biblioteca y herramientas | Texto/bytes, listas, matemáticas, archivos/rutas y errores; CLI `run`, `check`, `build` | Programas útiles de archivos y procesamiento de texto; errores con columna; instalación repetible; contratos probados. Paquetes, editor y formateador después de estabilizar núcleo |
| 10. Bootstrap | Lexer, parser, AST y análisis migrados progresivamente a Nat | Construir stage1 con semilla C; stage2 y stage3 con Nat; mismos tokens/AST/IR y corpus; binarios iguales donde sea determinista o diferencias documentadas |
| 11. Madurez | Portabilidad, depuración, compatibilidad y documentación | CI en Linux, Windows y macOS con toolchains fijados; correspondencia de fuente al depurar; política de versiones y migración probada; no anunciar capacidades sin casos reproducibles |

Cada fase produce cambios pequeños. Las metas son criterios futuros, no tareas
que esta entrega declare terminadas. El siguiente cambio recomendado es
introducir un lexer con posiciones y pruebas de indentación/literales, sin
añadir de inmediato funciones al analizador actual.

## 11. Bootstrap y dependencias

Durante las primeras etapas, frontend y runtime permanecen en C. El backend
externo es GCC/Clang para el C emitido, junto al enlazador y bibliotecas del
sistema. Los programas `.nat` actuales no sustituyen ninguno de estos
componentes.

Migrar primero el lexer y comparar sus tokens con la semilla. Después parser
y AST, usando listas/arenas y tipos algebraicos. Luego resolución, tipos y
emisor; migrar biblioteca de cadenas y colecciones cuando haya pruebas de
equivalencia. Conservar una semilla versionada y documentar comandos,
toolchains, fuentes y hashes de cada stage. La equivalencia funcional del
bootstrap no elimina por sí sola el problema de confiar en la semilla.

Llamar self-hosted al compilador solo cuando el compilador escrito en Nat
construya una siguiente etapa funcional y el proceso se pueda repetir. El
runtime C, backend externo, linker y bibliotecas se seguirán declarando como
dependencias; no se afirmará autocontención total mientras existan.

## 12. Fuentes técnicas primarias

Las decisiones específicas de Nat son propuestas de esta auditoría. Estas
fuentes respaldan las capacidades y limitaciones de las tecnologías comparadas,
no ofrecen resultados de Nat:

1. LLVM Project. [My First Language Frontend with LLVM](https://llvm.org/docs/tutorial/MyFirstLanguageFrontend/). Lexer, AST, IR, optimización, objetos y depuración; consultado 2026-10-29.
2. LLVM Project. [The LLVM Target-Independent Code Generator](https://llvm.org/docs/CodeGenerator.html). Componentes del backend y generación de código; consultado 2026-10-29.
3. LLVM Project. [Performance Tips for Frontend Authors](https://llvm.org/docs/Frontend/PerformanceTips.html). Efecto de la forma de IR, layout y linkage; consultado 2026-10-29.
4. Swift Project. [Automatic Reference Counting, fuente oficial del libro](https://github.com/swiftlang/swift-book/blob/main/TSPL.docc/LanguageGuide/AutomaticReferenceCounting.md). RC y ciclos fuertes; consultado 2026-10-29.
5. Rust Project. [Behavior considered undefined](https://doc.rust-lang.org/stable/reference/behavior-considered-undefined.html). Responsabilidad de código unsafe e interoperabilidad; consultado 2026-10-29.

La evidencia principal sobre Nat procede del código privado fijado, de las
ejecuciones descritas y de los registros conservados en esta entrega.
