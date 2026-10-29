# Nat: propuesta de núcleo, todavía no implementada

Estado: borrador de diseño para revisar con pruebas. El único cambio de
semántica de ejecución realizado en esta entrega es rechazar de forma segura
los argumentos que exceden el límite existente. Nada de esta especificación
debe anunciarse como disponible en v0.3.0.

## Sintaxis y ejecución

Fuente UTF-8; comentarios `#`; cadenas entre comillas dobles; índices desde cero.
Los bloques usan `:` y cuatro espacios por nivel. El lexer emitirá NEWLINE,
INDENT y DEDENT, rechazando tabuladores y saltos de indentación no justificados.
Cada token conservará archivo, desplazamiento en bytes, línea y columna.
Los diagnósticos mostrarán línea y columna desde uno; para texto UTF-8, columna
en valores escalares Unicode, no en bytes ni anchura visual del terminal.

```nat
func fibonacci(n: Int) -> Int:
    si n < 2:
        retornar n
    retornar fibonacci(n - 1) + fibonacci(n - 2)

nombre = "Nat"
edad = 15
activo = verdadero
numeros = [10, 20, 30]
numeros = agregar(numeros, 40)
imprimir numeros[0]
imprimir fibonacci(20)
```

`imprimir` sigue siendo una sentencia para conservar el uso actual. Las
funciones ordinarias se invocan con paréntesis. Las asignaciones evalúan primero
la expresión derecha y después actualizan el destino. La ejecución de
argumentos y operandos será de izquierda a derecha; `y` y `o` tendrán
cortocircuito. `si` y `mientras` requerirán Bool, sin conversión por veracidad.

`agregar(lista, elemento)` devuelve una lista con el elemento añadido. No
modifica implícitamente otra variable del llamador. Se elige esta forma para
mantener semántica de valor y evitar introducir préstamos en el núcleo inicial.
El compilador podrá reutilizar el almacenamiento si demuestra que es único.

Precedencia, de mayor a menor: llamadas e índices; unarios `-` y `no`;
`* / %`; `+ -`; comparaciones `< <= > >=`; igualdad `== !=`; `y`; `o`.
Se rechazan comparaciones encadenadas en el núcleo inicial. `/` solo se define
para Float; la división entera se pedirá con `dividir_entero(a, b)`, truncando
hacia cero; su resto cumple `a = cociente*b + resto`. Esto evita que `/`
signifique operaciones distintas según una conversión implícita.

Nombres locales con ámbitos léxicos por función y bloque. La primera asignación
a un nombre que no esté visible lo introduce en el ámbito actual. Una
asignación posterior actualiza el binding visible más cercano y conserva su
tipo; para evitar ambigüedad, el núcleo no permite ocultar un nombre visible.
Cada lectura debe estar precedida por una inicialización en todas las rutas
posibles. Un nombre inexistente es un error estático, nunca un literal.
Una función puede leer constantes del módulo, pero no modificar bindings de
otro ámbito; sus variables y parámetros se resuelven antes de generar código.

`si` admite posteriormente `sino` con la misma indentación. La gramática debe
definir sus tokens y pruebas antes de incorporarlo. `leer` conserva su
comportamiento actual solo en el intérprete de compatibilidad; la compilación
estática usará un sistema de módulos con nombres y dependencias resueltas,
no ejecutará inclusiones arbitrarias para descubrir tipos.

## Tipos e inferencia

| Tipo o capacidad | Política propuesta |
| --- | --- |
| Int | Entero con signo de 64 bits, comportamiento igual en cada plataforma |
| Float | IEEE 754 binary64, sin fast-math por defecto; NaN no se iguala a sí mismo |
| Bool | `verdadero` y `falso`; no se convierte automáticamente a Int |
| Texto | UTF-8 válido, inmutable; no es una dirección de memoria |
| Bytes | Secuencia de bytes para E/S y trabajo interno del lexer |
| Lista[T] | Elementos homogéneos, longitud dinámica, semántica de valor |
| Unidad | Resultado de procedimientos sin valor significativo |
| Registros y tipos algebraicos | Segunda ampliación, con campos y variantes declarados |
| Opcion[T], Resultado[T,E] | Tipos algebraicos de biblioteca; manejo exhaustivo de variantes |
| Genéricos | Monomorfización inicial; medir tamaño de código y tiempo de compilación |
| Interfaces | Restricciones estáticas simples después de genéricos; sin especialización ni herencia compleja inicialmente |
| Funciones como valores | Tipo `(Int, Int) -> Int`; primero funciones sin captura, luego capturas inmutables por valor |

Una variable local infiere su tipo desde el inicializador: `edad = 15` es Int.
Puede indicarse `edad: Int = 15`. Los parámetros y el retorno de funciones
con resultado llevan anotaciones en el primer núcleo, incluidas funciones
recursivas y públicas. Un procedimiento sin anotación de retorno produce
Unidad. Esto evita depender de todas las llamadas para inferir una API.

Una lista vacía requiere contexto: `valores: Lista[Int] = []`. Un retorno
ambiguo, una unión de ramas incompatibles o un genérico sin información
suficiente requieren anotación; no se inventará un tipo dinámico `Any`.
Los genéricos tendrán parámetros declarados, por ejemplo
`func identidad[T](x: T) -> T`, e inferencia de T desde argumentos concretos.
La recursión que expanda indefinidamente instancias genéricas se rechazará con
un diagnóstico y un límite de compilación documentado.

No habrá conversiones implícitas entre Texto, Bool, Int y Float. Los literales
numéricos podrán adaptarse a un tipo numérico esperado si son representables.
`convertir_float(entero)` será explícito; la conversión que pueda fallar
devolverá Resultado. Igualdad y operadores exigirán tipos compatibles; las
conversiones de precisión no se ocultarán para hacer compilar una expresión.

El desbordamiento entero, la división por cero y los índices inválidos se
detectarán también en compilaciones optimizadas. Un error demostrable en una
constante se señalará al compilar. En ejecución provocará una terminación
controlada con ubicación. Operaciones deliberadamente modulares, si se
añaden, llevarán nombres explícitos; no dependerán de UB de C o LLVM.

`longitud(Texto)` contará valores escalares Unicode; el índice textual accederá
al mismo tipo de unidad y puede costar O(n). No promete contar grafemas.
Bytes tendrá longitud e índices en bytes. Esta distinción cambia la conducta
actual para caracteres no ASCII y exige versión, documentación y migración;
no se introducirá silenciosamente en el arreglo de v0.3.0.

## Representación y memoria

El intérprete de referencia comenzará con un valor etiquetado y una unión
discriminada. El compilador eliminará las etiquetas cuando conozca el tipo:
un Int local debe ser un entero máquina, sin caja ni conteo de referencias.
Las arenas del compilador poseerán tokens, AST e IR; los NodeId se comprobarán
al desreferenciar. No se devolverán punteros a arenas ya liberadas.

Para el primer runtime se propone semántica de valor: escalares y registros
pequeños por valor, Texto inmutable y listas con almacenamiento compartido
interno mediante conteo de referencias. La modificación de una lista compartida
copiará antes de escribir. El núcleo no expone referencias mutables almacenables
ni grafos cíclicos de objetos; los grafos del compilador usan IDs en arenas.
Así se limita inicialmente el problema de ciclos de RC. Introducir referencias
o cierres mutables exige reabrir expresamente esa decisión.

El runtime comprobará multiplicaciones de tamaños, límites, capacidad y fallos
de asignación. No habrá `free` en código ordinario Nat. Esto es una estrategia,
no una garantía ya demostrada: C, los wrappers del runtime y el backend siguen
siendo parte de la base de confianza.

## Compatibilidad y validación

Antes de habilitar el nuevo lenguaje, conservar el intérprete anterior y sus
pruebas en modo de compatibilidad. Especificar los cambios de números-texto,
variables inexistentes, Unicode, módulos e indentación. Las mismas entradas
válidas del núcleo nuevo deben producir la misma salida y los mismos errores
con el intérprete de AST tipado y el backend nativo.

Se requieren pruebas positivas, rechazos estáticos, límites numéricos,
propiedades de listas por valor, errores en ramas no ejecutadas y spans exactos.
Los futuros detalles de FFI, concurrencia, interfaces, patrones y módulos
necesitan especificaciones propias; no están definidos por este borrador.
