# Nat

El compilador principal `natc/` tiene frontend, tipos e IR de funciones comunes
a dos backends. La semilla del compilador está escrita en Python 3.

```sh
python3 -m natc build herramientas/nat_fuente.nat --backend asm -o build/nat-fuente
./build/nat-fuente < examples/datos/fuente.txt
make test
```

El ejemplo produce 2 LF, 5 palabras, 3 candidatos a identificador ASCII y
22 bytes. Usa cinco funciones Nat con parámetros, retornos y variables locales.

- `--backend asm`: Python + GNU as/ld para Linux x86_64; genera ELF sin C,
  GCC ni libc. Sin optimizador ni sanitizers.
- Backend C predeterminado: Python + GCC; el ejecutable usa libc. Mantiene
  opciones O0/O2 y ASan/UBSan. `nat.c` sigue como intérprete de compatibilidad.

Tipos Int64, Bool y Texto literal, funciones de hasta seis parámetros,
recursión acotada, ámbitos léxicos, `si/sino`, bucles y lectura por bytes.
No hay colecciones, cierres, módulos nativos, API de archivos por nombre ni
self-hosting. No se anuncia portabilidad del ASM fuera de Linux x86_64.

[Estado actual, archivos, semántica, IR, ABI, pruebas y bootstrap](docs/FUNCIONES_NATIVAS.md).
Los documentos de auditoría/entregas previas describen sus versiones históricas.
El repositorio local de esta misión preserva la base remota y los cambios
locales anteriores en commits separados. No se ha hecho push ni cambiado GitHub.
