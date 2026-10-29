# Nat

La base principal es el compilador `natc/`. El intérprete C queda como
compatibilidad explícita, sin ampliar su lenguaje. No son dos implementaciones
equivalentes: la transición y sus diferencias se documentan por separado.

Dos rutas disponibles:

- Intérprete de compatibilidad en C: `make`, `./build/nat pruebas/interprete.nat`.
- Compilador AOT experimental: `python3 -m natc build examples/compiled/suma.nat -o build/suma`, después `./build/suma 100`.

Se necesitan Python 3 y GCC para el compilador y sus pruebas; Make para los
atajos. El ejecutable generado necesita libc, sin Python ni intérprete Nat.
La implementación de arranque del compilador es Python, no self-hosted.

```sh
make test
make test-sanitize ASAN_OPTIONS=detect_leaks=0:halt_on_error=1
make benchmark-native
```

[Entrega 2: funciones, semántica, archivos, comandos y límites](docs/COMPILADOR.md).
[Primera auditoría histórica](docs/AUDITORIA.md).
El [borrador general](docs/ESPECIFICACION_PROPUESTA.md) describe objetivos, no
capacidades ya disponibles. El compilador solo implementa el subconjunto de
la entrega 2; los programas anteriores siguen usando el intérprete de C.

Trabajo local basado en `kinjeabrahan/nat`, commit
`fd64d424e604eec93ef2bf0f6cc235d76ffbb210`. Las dos entregas previas ya están integradas en ese commit remoto.
Esta tercera mejora sigue local y no ha creado commits ni cambios remotos. `nat.exe` original permanece fuera de esta copia de fuentes, sin cambios
propuestos sobre ese archivo. LeakSanitizer no funciona en este contenedor;
la opción mostrada desactiva solo fugas, conservando ASan y UBSan.

[Entrega 3: corrección semántica y compatibilidad](docs/ENTREGA3.md).
