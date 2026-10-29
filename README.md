# Nat

Dos rutas independientes, conservadas durante la transición:

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
`0ef1d60775ed96ac6901049092d26a125b9ccc5e`. No se han creado commits ni cambios
remotos. `nat.exe` original permanece fuera de esta copia de fuentes, sin cambios
propuestos sobre ese archivo. LeakSanitizer no funciona en este contenedor;
la opción mostrada desactiva solo fugas, conservando ASan y UBSan.
