# Benchmark inicial: recorrido de dígitos

```sh
python3 benchmarks/run.py --output build/benchmark.json
python3 benchmarks/run.py --repetitions 25 --warmups 3 --output build/benchmark-25.json
```

Los puertos Nat, Python, C, C++ y Rust hacen cuatro bucles anidados de nueve
iteraciones. Cada paso transforma el estado mediante `1234567890`; los
contadores avanzan con `1234567899`. Se realizan 6561 transformaciones
dependientes del estado anterior y se imprime el resultado `1`. No se usa
aritmética de Nat: no existe todavía. C++ compila el mismo archivo que C en
modo C++17. Rust tiene un archivo separado; no se ejecutó en esta entrega
porque `rustc` no está instalado.

Se comprueba la salida de cada ejecución. Las compilaciones se miden aparte,
con GCC/G++ `-O2` y Rust `-C opt-level=2`. Para Nat, ese tiempo corresponde a
construir el intérprete C, no a compilar el programa Nat. Python interpreta
el archivo fuente y su preparación forma parte de la ejecución del proceso.

Cada implementación tiene dos calentamientos y nueve muestras medidas. Las
rondas intercalan los lenguajes con un orden barajado reproducible. El JSON
retiene todas las muestras, mediana, media, desviación estándar muestral,
mínimo, máximo, versiones, opciones, hardware y hashes SHA-256 de las fuentes.
Las rutas temporales registradas documentan la ejecución; para repetirla se
usa el script, que reconstruye los binarios.

Son tiempos de pared que incluyen arranque, carga del programa y salida.
No son tiempos aislados del bucle. C/C++ usan estados escalares de un byte;
Nat/Python usan cadenas; los conversores de índices internos también difieren.
El algoritmo y el trabajo observable son equivalentes, las representaciones
internas siguen las capacidades de cada implementación. El optimizador nativo
puede simplificar el código si preserva ese resultado.

No se fijó afinidad de CPU, frecuencia ni carga del host. La tabla no permite
afirmar que un lenguaje sea más rápido en general, atribuir una diferencia al
pequeño arreglo del parser, ni proyectar resultados de un futuro compilador.
No se midió consumo máximo de memoria ni se ejecutó un perfilador.

## Ampliación de la suite

| Carga | Estado de Nat y requisito previo |
| --- | --- |
| Bucles sobre bytes/cadenas | Implementada y medida aquí |
| Suma, producto, reducción numérica | Pendiente: enteros y operadores reales |
| Fibonacci recursivo y recursión mutua | Pendiente: funciones y ámbitos |
| Álgebra numérica | Pendiente: Float y operaciones definidas |
| Búsqueda de subcadenas y construcción de textos grandes | Pendiente: quitar límite de 255 bytes con representación segura |
| Búsqueda y ordenación de listas | Pendiente: listas tipadas e índices |
| Asignaciones, copias y presión de memoria | Pendiente: valores dinámicos y política de propiedad |
| Archivos con datos de tamaño controlado | Pendiente: API de archivos de datos; `leer` actual ejecuta código |
| Concurrencia | Pendiente: modelo de memoria y concurrencia |
| Tokenizador y parser de archivos reales | Pendiente: frontend separado; futura aplicación de bootstrap |

Cada carga nueva necesita resultados comprobables, mismos datos y algoritmo,
repeticiones, datos crudos y tiempo de compilación separado. Cuando existan
programas suficientemente largos, separar también arranque y tiempo de kernel.
