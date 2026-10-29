
/*
 * Nat v0.3.0
 * Interprete con variables, bloques, modulos y funciones de cadenas.
 *
 * Compilar:
 * gcc -std=c11 -Wall -Wextra -Wpedantic nat.c -o nat.exe
 *
 * Sintaxis:
 *   nombre = "texto"
 *   nombre = otra_variable
 *   imprimir "Hola Nat"
 *   imprimir longitud("Nat")
 *   imprimir caracter("Nat", 1)
 *   imprimir buscar("Nat", "a")
 *
 *   si nombre == "valor":
 *       imprimir "Correcto"
 *
 *   mientras nombre != "fin":
 *       nombre = "fin"
 *
 *   leer "modulo.nat"
 *
 * Indices de cadenas: empiezan en cero.
 * Las cadenas se procesan como bytes; Unicode completo aun no.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <errno.h>

#define NAT_VERSION "0.3.0"

#define MAX_VARIABLES 100
#define MAX_LINEAS 500
#define MAX_LINEA 512
#define MAX_NOMBRE 64
#define MAX_VALOR 256
#define MAX_RUTA 1024

#define MAX_PROFUNDIDAD_ARCHIVOS 32
#define MAX_PROFUNDIDAD_BLOQUES 128
#define MAX_ITERACIONES 1000000UL

typedef struct
{
    char nombre[MAX_NOMBRE];
    char valor[MAX_VALOR];
} Variable;

typedef struct
{
    char (*lineas)[MAX_LINEA];
    int total;
    char ruta[MAX_RUTA];
} Programa;

static Variable memoria[MAX_VARIABLES];
static size_t total_variables = 0;
static unsigned long total_iteraciones = 0;

/* =========================================================
   ERRORES Y MEMORIA
   ========================================================= */

static _Noreturn void error_general(const char *mensaje)
{
    fprintf(stderr, "[Nat %s] %s\n", NAT_VERSION, mensaje);
    exit(EXIT_FAILURE);
}

static _Noreturn void error_nat(
    const char *ruta,
    int linea,
    const char *mensaje)
{
    fprintf(stderr, "[Nat %s] %s:%d: %s\n",
            NAT_VERSION,
            ruta ? ruta : "<entrada>",
            linea > 0 ? linea : 1,
            mensaje);

    exit(EXIT_FAILURE);
}

static void *nat_malloc(size_t cantidad)
{
    void *p = malloc(cantidad);

    if (p == NULL)
        error_general("No hay memoria suficiente.");

    return p;
}

static void comprobar_formato(int n, size_t capacidad, const char *ruta, int linea)
{
    if (n < 0 || (size_t)n >= capacidad)
        error_nat(ruta, linea, "Texto formateado demasiado largo o error de formato.");
}

#include "legacy_lex.h"

/* =========================================================
   UTILIDADES DE TEXTO
   ========================================================= */

static char *recortar(char *texto)
{
    while (isspace((unsigned char)*texto))
        texto++;

    size_t n = strlen(texto);

    while (n > 0 && isspace((unsigned char)texto[n - 1]))
        texto[--n] = '\0';

    return texto;
}

static int linea_ignorable(const char *linea)
{
    while (isspace((unsigned char)*linea))
        linea++;

    return *linea == '\0' || *linea == '#';
}

static char *quitar_indentacion(char *linea)
{
    while (*linea == ' ' || *linea == '\t')
        linea++;

    return linea;
}

static int obtener_indentacion(
    const char *linea,
    const char *ruta,
    int numero_linea)
{
    int nivel = 0;
    int espacios = 0;
    int tabuladores = 0;

    while (*linea == ' ' || *linea == '\t')
    {
        if (*linea == ' ')
        {
            espacios = 1;
            nivel++;
        }
        else
        {
            tabuladores = 1;
            nivel += 4;
        }

        linea++;
    }

    if (espacios && tabuladores)
    {
        error_nat(
            ruta,
            numero_linea,
            "No mezcles espacios y tabuladores al inicio de una linea.");
    }

    return nivel;
}

static void quitar_comentario(char *texto)
{
    int comillas = 0;
    int escape = 0;

    for (char *p = texto; *p; p++)
    {
        if (escape)
        {
            escape = 0;
            continue;
        }

        if (comillas && *p == '\\')
        {
            escape = 1;
            continue;
        }

        if (*p == '"')
        {
            comillas = !comillas;
            continue;
        }

        if (*p == '#' && !comillas)
        {
            *p = '\0';
            return;
        }
    }
}

static int identificador_valido(const char *nombre)
{
    if (nombre == NULL || *nombre == '\0')
        return 0;

    if (!(isalpha((unsigned char)nombre[0]) ||
          nombre[0] == '_'))
        return 0;

    for (const char *p = nombre + 1; *p; p++)
    {
        if (!(isalnum((unsigned char)*p) || *p == '_'))
            return 0;
    }

    return 1;
}

/* =========================================================
   VARIABLES
   ========================================================= */

static const char *obtener_variable(const char *nombre)
{
    for (size_t i = 0; i < total_variables; i++)
    {
        if (strcmp(memoria[i].nombre, nombre) == 0)
            return memoria[i].valor;
    }

    return NULL;
}

static void asignar_variable(
    const char *nombre,
    const char *valor,
    const char *ruta,
    int numero_linea)
{
    if (!identificador_valido(nombre))
        error_nat(ruta, numero_linea, "Nombre de variable no valido.");

    if (strlen(nombre) >= MAX_NOMBRE)
        error_nat(ruta, numero_linea, "Nombre de variable demasiado largo.");

    if (strlen(valor) >= MAX_VALOR)
        error_nat(ruta, numero_linea, "Valor demasiado largo.");

    for (size_t i = 0; i < total_variables; i++)
    {
        if (strcmp(memoria[i].nombre, nombre) == 0)
        {
            strcpy(memoria[i].valor, valor);
            return;
        }
    }

    if (total_variables >= MAX_VARIABLES)
        error_nat(ruta, numero_linea, "Limite de variables alcanzado.");

    strcpy(memoria[total_variables].nombre, nombre);
    strcpy(memoria[total_variables].valor, valor);
    total_variables++;
}

/* =========================================================
   CARGA Y LIBERACION DE ARCHIVOS
   ========================================================= */

static void cargar_programa(Programa *p, const char *ruta)
{
    if (ruta[0] == '\0')
        error_general("La ruta no puede estar vacia.");

    if (strlen(ruta) >= sizeof(p->ruta))
        error_general("La ruta del archivo es demasiado larga.");

    FILE *archivo = fopen(ruta, "r");

    if (archivo == NULL)
    {
        char mensaje[MAX_RUTA + 128];

        int n = snprintf(
            mensaje,
            sizeof(mensaje),
            "No se pudo abrir '%s' (errno=%d).",
            ruta,
            errno);

        comprobar_formato(n, sizeof(mensaje), ruta, 1);
        error_general(mensaje);
    }

    strcpy(p->ruta, ruta);
    p->total = 0;
    p->lineas = nat_malloc(sizeof(*p->lineas) * MAX_LINEAS);

    char buffer[MAX_LINEA];

    while (fgets(buffer, sizeof(buffer), archivo) != NULL)
    {
        size_t n = strlen(buffer);

        if (n > 0 && buffer[n - 1] != '\n' && !feof(archivo))
        {
            int c;

            while ((c = fgetc(archivo)) != '\n' && c != EOF)
            {
                /* Consumir el resto de la linea. */
            }

            fclose(archivo);
            free(p->lineas);
            p->lineas = NULL;

            error_nat(
                ruta,
                p->total + 1,
                "La linea supera el limite permitido.");
        }

        if (p->total >= MAX_LINEAS)
        {
            fclose(archivo);
            free(p->lineas);
            p->lineas = NULL;

            error_nat(
                ruta,
                p->total + 1,
                "El archivo supera el limite de lineas.");
        }

        buffer[strcspn(buffer, "\r\n")] = '\0';
        strcpy(p->lineas[p->total], buffer);
        p->total++;
    }

    if (ferror(archivo))
    {
        fclose(archivo);
        free(p->lineas);
        p->lineas = NULL;

        error_nat(ruta, p->total + 1, "Error al leer el archivo.");
    }

    fclose(archivo);
}

static void liberar_programa(Programa *p)
{
    free(p->lineas);
    p->lineas = NULL;
    p->total = 0;
}

/* =========================================================
   RUTAS RELATIVAS
   ========================================================= */

static int ruta_absoluta(const char *ruta)
{
#ifdef _WIN32
    if (isalpha((unsigned char)ruta[0]) && ruta[1] == ':')
        return 1;

    if (ruta[0] == '\\' && ruta[1] == '\\')
        return 1;
#endif

    return ruta[0] == '/';
}

static void construir_ruta_include(
    const char *archivo_actual,
    const char *solicitada,
    char *salida,
    size_t capacidad,
    const char *ruta_error,
    int numero_linea)
{
    if (ruta_absoluta(solicitada))
    {
        int n = snprintf(salida, capacidad, "%s", solicitada);

        if (n < 0 || (size_t)n >= capacidad)
            error_nat(ruta_error, numero_linea, "Ruta demasiado larga.");

        return;
    }

    const char *separador = strrchr(archivo_actual, '/');

#ifdef _WIN32
    const char *barra = strrchr(archivo_actual, '\\');

    if (barra != NULL && (separador == NULL || barra > separador))
        separador = barra;
#endif

    if (separador == NULL)
    {
        int n = snprintf(salida, capacidad, "%s", solicitada);

        if (n < 0 || (size_t)n >= capacidad)
            error_nat(ruta_error, numero_linea, "Ruta demasiado larga.");

        return;
    }

    size_t prefijo = (size_t)(separador - archivo_actual + 1);
    size_t longitud = strlen(solicitada);

    if (prefijo + longitud + 1 > capacidad)
        error_nat(ruta_error, numero_linea, "Ruta demasiado larga.");

    memcpy(salida, archivo_actual, prefijo);
    memcpy(salida + prefijo, solicitada, longitud + 1);
}

/* =========================================================
   RESOLUCION DE VALORES Y FUNCIONES DE CADENAS
   ========================================================= */

static void resolver_operando(
    char *texto,
    char *salida,
    size_t capacidad,
    const char *ruta,
    int numero_linea);

static void evaluar_funcion_cadena(
    char *texto,
    char *salida,
    size_t capacidad,
    const char *ruta,
    int numero_linea)
{
    char copia[MAX_LINEA];

    if (strlen(texto) >= sizeof(copia))
        error_nat(ruta, numero_linea, "Expresion demasiado larga.");

    strcpy(copia, texto);

    char *abre = strchr(copia, '(');

    if (abre == NULL)
        error_nat(ruta, numero_linea, "Llamada de funcion no valida.");

    size_t n = strlen(copia);

    if (n < 3 || copia[n - 1] != ')')
        error_nat(ruta, numero_linea, "Falta ')' en la funcion.");

    /*
     * Comprobar que el ultimo ')' cierra el primer '(',
     * y no que haya texto adicional despues de la llamada.
     */
    int profundidad = 0;
    int comillas = 0;
    int escape = 0;
    char *cierre = NULL;

    for (char *p = abre; *p; p++)
    {
        if (escape)
        {
            escape = 0;
            continue;
        }

        if (comillas && *p == '\\')
        {
            escape = 1;
            continue;
        }

        if (*p == '"')
        {
            comillas = !comillas;
            continue;
        }

        if (comillas)
            continue;

        if (*p == '(')
            profundidad++;

        if (*p == ')')
        {
            profundidad--;

            if (profundidad < 0)
                error_nat(ruta, numero_linea, "Parentesis no valido.");

            if (profundidad == 0)
            {
                cierre = p;
                break;
            }
        }
    }

    if (comillas || cierre != copia + n - 1 || profundidad != 0)
        error_nat(ruta, numero_linea, "Estructura de funcion no valida.");

    *abre = '\0';
    *cierre = '\0';

    char *nombre = recortar(copia);
    char *argumentos = abre + 1;

    char args[2][MAX_LINEA];
    size_t longitud_arg = 0;
    int cantidad = 0;
    comillas = 0;
    escape = 0;
    profundidad = 0;

    for (char *p = argumentos;; p++)
    {
        char c = *p;

        /* Validar la fila antes de escribir cualquier byte del argumento. */
        if (cantidad >= 2)
            error_nat(ruta, numero_linea, "Demasiados argumentos.");

        if (escape)
        {
            escape = 0;
        }
        else if (comillas && c == '\\')
        {
            escape = 1;
        }
        else if (c == '"')
        {
            comillas = !comillas;
        }
        else if (!comillas && c == '(')
        {
            profundidad++;
        }
        else if (!comillas && c == ')')
        {
            profundidad--;
        }

        int separador =
            (c == ',' && !comillas && profundidad == 0);

        if (separador || c == '\0')
        {
            if (longitud_arg >= sizeof(args[0]))
                error_nat(ruta, numero_linea, "Argumento demasiado largo.");

            args[cantidad][longitud_arg] = '\0';

            if (*recortar(args[cantidad]) == '\0')
                error_nat(ruta, numero_linea, "Argumento vacio.");

            cantidad++;

            if (c == '\0')
                break;

            longitud_arg = 0;
            continue;
        }

        if (longitud_arg + 1 >= sizeof(args[0]))
            error_nat(ruta, numero_linea, "Argumento demasiado largo.");

        args[cantidad][longitud_arg++] = c;
    }

    if (comillas || profundidad != 0)
        error_nat(ruta, numero_linea, "Argumentos mal formados.");

    char valor1[MAX_VALOR];
    char valor2[MAX_VALOR];

    resolver_operando(
        recortar(args[0]),
        valor1,
        sizeof(valor1),
        ruta,
        numero_linea);

    if (strcmp(nombre, "longitud") == 0)
    {
        if (cantidad != 1)
            error_nat(ruta, numero_linea, "longitud() necesita un argumento.");

        comprobar_formato(snprintf(salida, capacidad, "%zu", strlen(valor1)), capacidad, ruta, numero_linea);
        return;
    }

    if (cantidad != 2)
        error_nat(ruta, numero_linea, "Esta funcion necesita dos argumentos.");

    resolver_operando(
        recortar(args[1]),
        valor2,
        sizeof(valor2),
        ruta,
        numero_linea);

    if (strcmp(nombre, "caracter") == 0)
    {
        char *fin = NULL;

        errno = 0;
        long posicion = strtol(valor2, &fin, 10);

        if (errno == ERANGE || fin == valor2 || *fin != '\0' || posicion < 0)
            error_nat(ruta, numero_linea, "Indice de caracter no valido.");

        size_t longitud = strlen(valor1);

        if ((unsigned long)posicion >= longitud)
            error_nat(ruta, numero_linea, "Indice fuera del texto.");

        if (capacidad < 2)
            error_nat(ruta, numero_linea, "Buffer de salida insuficiente.");

        salida[0] = valor1[posicion];
        salida[1] = '\0';
        return;
    }

    if (strcmp(nombre, "buscar") == 0)
    {
        char *encontrado = strstr(valor1, valor2);

        if (encontrado == NULL)
        {
            comprobar_formato(snprintf(salida, capacidad, "-1"), capacidad, ruta, numero_linea);
        }
        else
        {
            int n = snprintf(
                salida,
                capacidad,
                "%ld",
                (long)(encontrado - valor1));
            comprobar_formato(n, capacidad, ruta, numero_linea);
        }

        return;
    }

    error_nat(ruta, numero_linea, "Funcion de cadenas desconocida.");
}

static void resolver_operando(
    char *texto,
    char *salida,
    size_t capacidad,
    const char *ruta,
    int numero_linea)
{
    texto = recortar(texto);

    size_t n = strlen(texto);

    if (n == 0)
        error_nat(ruta, numero_linea, "Operando vacio.");

    if (capacidad == 0)
        error_nat(ruta, numero_linea, "Buffer de salida no valido.");

    const char *cursor = texto;
    NatToken token = nat_siguiente(&cursor, ruta, numero_linea);
    NatToken siguiente = nat_siguiente(&cursor, ruta, numero_linea);

    if (token.clase == NAT_ID && siguiente.clase == NAT_ABRE)
    {
        evaluar_funcion_cadena(texto, salida, capacidad, ruta, numero_linea);
        return;
    }
    if (siguiente.clase != NAT_FIN)
        error_nat(ruta, numero_linea, "Expresion no valida; las cadenas necesitan comillas y un solo literal.");

    const char *valor = NULL;
    if (token.clase == NAT_CADENA) valor = token.valor;
    else if (token.clase == NAT_ID)
    {
        char nombre[MAX_NOMBRE];
        if (token.longitud >= sizeof(nombre))
            error_nat(ruta, numero_linea, "Nombre de variable demasiado largo.");
        memcpy(nombre, token.inicio, token.longitud);
        nombre[token.longitud] = '\0';
        valor = obtener_variable(nombre);
        if (valor == NULL)
        {
            char mensaje[MAX_NOMBRE + 64];
            int n = snprintf(mensaje, sizeof(mensaje), "Variable no definida: %s.", nombre);
            if (n < 0 || (size_t)n >= sizeof(mensaje))
                error_nat(ruta, numero_linea, "Error al construir diagnostico.");
            error_nat(ruta, numero_linea, mensaje);
        }
    }
    else if (token.clase == NAT_ENTERO || nat_palabra(&token, "verdadero") || nat_palabra(&token, "falso"))
    {
        if (token.longitud >= capacidad)
            error_nat(ruta, numero_linea, "Operando demasiado largo.");
        memcpy(salida, texto, token.longitud);
        salida[token.longitud] = '\0';
        return;
    }
    else error_nat(ruta, numero_linea, "Operando no valido; las cadenas necesitan comillas.");

    if (strlen(valor) >= capacidad)
        error_nat(ruta, numero_linea, "Cadena demasiado larga.");
    strcpy(salida, valor);
}

/* =========================================================
   CONDICIONES
   ========================================================= */

static int evaluar_condicion(
    const char *condicion_original,
    const char *ruta,
    int numero_linea)
{
    char condicion[MAX_LINEA];

    if (strlen(condicion_original) >= sizeof(condicion))
        error_nat(ruta, numero_linea, "Condicion demasiado larga.");

    strcpy(condicion, condicion_original);

    char *texto = recortar(condicion);
    size_t n = strlen(texto);

    if (n == 0 || texto[n - 1] != ':')
        error_nat(ruta, numero_linea, "Falta ':' al final de la condicion.");

    texto[n - 1] = '\0';
    texto = recortar(texto);

    char *operador = NULL;
    int comillas = 0;
    int escape = 0;

    for (char *p = texto; *p; p++)
    {
        if (escape)
        {
            escape = 0;
            continue;
        }

        if (comillas && *p == '\\')
        {
            escape = 1;
            continue;
        }

        if (*p == '"')
        {
            comillas = !comillas;
            continue;
        }

        if (!comillas &&
            ((p[0] == '=' && p[1] == '=') ||
             (p[0] == '!' && p[1] == '=')))
        {
            operador = p;
            break;
        }
    }

    if (operador == NULL)
        error_nat(ruta, numero_linea, "Usa == o != en la condicion.");

    char simbolo[3] = {operador[0], operador[1], '\0'};

    *operador = '\0';

    char *izquierda = recortar(texto);
    char *derecha = recortar(operador + 2);

    if (*izquierda == '\0' || *derecha == '\0')
        error_nat(ruta, numero_linea, "Falta un operando en la condicion.");

    char valor_izq[MAX_VALOR];
    char valor_der[MAX_VALOR];

    resolver_operando(
        izquierda, valor_izq, sizeof(valor_izq),
        ruta, numero_linea);

    resolver_operando(
        derecha, valor_der, sizeof(valor_der),
        ruta, numero_linea);

    int iguales = strcmp(valor_izq, valor_der) == 0;

    return strcmp(simbolo, "==") == 0 ? iguales : !iguales;
}

/* =========================================================
   ASIGNACIONES
   ========================================================= */

static char *buscar_igual_asignacion(char *texto)
{
    int comillas = 0;
    int escape = 0;

    for (char *p = texto; *p; p++)
    {
        if (escape)
        {
            escape = 0;
            continue;
        }

        if (comillas && *p == '\\')
        {
            escape = 1;
            continue;
        }

        if (*p == '"')
        {
            comillas = !comillas;
            continue;
        }

        if (!comillas && *p == '=')
        {
            if (p[1] == '=' || (p > texto && (p[-1] == '!' || p[-1] == '=')))
                continue;

            return p;
        }
    }

    return NULL;
}

static void ejecutar_asignacion(
    char *texto,
    const char *ruta,
    int numero_linea)
{
    char *igual = buscar_igual_asignacion(texto);

    if (igual == NULL)
        error_nat(ruta, numero_linea, "Asignacion no valida.");

    *igual = '\0';

    char *nombre = recortar(texto);
    char *valor = recortar(igual + 1);

    if (!identificador_valido(nombre))
        error_nat(ruta, numero_linea, "Nombre de variable no valido.");

    if (*valor == '\0')
        error_nat(ruta, numero_linea, "Falta el valor de la asignacion.");

    char resultado[MAX_VALOR];

    resolver_operando(
        valor, resultado, sizeof(resultado),
        ruta, numero_linea);

    asignar_variable(nombre, resultado, ruta, numero_linea);
}

/* =========================================================
   EJECUCION DE BLOQUES Y ARCHIVOS
   ========================================================= */

static void ejecutar_archivo(const char *ruta, int profundidad_archivos);

static void ejecutar_rango(
    Programa *p,
    int inicio,
    int fin,
    int indent_padre,
    int profundidad_bloques,
    int profundidad_archivos);

static int encontrar_fin_bloque(
    Programa *p,
    int inicio,
    int fin,
    int indent_padre)
{
    int encontro_cuerpo = 0;

    for (int i = inicio; i < fin; i++)
    {
        if (linea_ignorable(p->lineas[i]))
            continue;

        int nivel = obtener_indentacion(p->lineas[i], p->ruta, i + 1);

        if (nivel <= indent_padre)
        {
            if (!encontro_cuerpo)
            {
                error_nat(
                    p->ruta, i + 1,
                    "El bloque necesita una linea indentada.");
            }

            return i;
        }

        encontro_cuerpo = 1;
    }

    if (!encontro_cuerpo)
        error_nat(p->ruta, inicio + 1, "El bloque esta vacio.");

    return fin;
}

/* Validate lexical strings and block structure before any side effects. */
static void validar_estructura(Programa *p)
{
    int anterior = 0, necesita_cuerpo = 0, ultima_linea = 0;
    for (int i = 0; i < p->total; i++)
    {
        if (linea_ignorable(p->lineas[i])) continue;
        int nivel = obtener_indentacion(p->lineas[i], p->ruta, i + 1);
        if (strchr(p->lineas[i], '\t') != NULL)
        {
            const char *inicio = p->lineas[i];
            while (*inicio == ' ' || *inicio == '\t')
                if (*inicio++ == '\t') error_nat(p->ruta, i + 1, "Indentacion: usa cuatro espacios, sin tabuladores.");
        }
        if (nivel % 4 != 0)
            error_nat(p->ruta, i + 1, "Indentacion: usa cuatro espacios por nivel.");
        if (necesita_cuerpo && nivel != anterior + 4)
            error_nat(p->ruta, i + 1, "El bloque necesita una linea indentada exactamente cuatro espacios.");
        if (!necesita_cuerpo && nivel > anterior)
            error_nat(p->ruta, i + 1, "Indentacion inesperada fuera de un bloque.");
        const char *cursor = quitar_indentacion(p->lineas[i]);
        NatToken primero = nat_siguiente(&cursor, p->ruta, i + 1);
        NatToken segundo = nat_siguiente(&cursor, p->ruta, i + 1);
        if (primero.clase == NAT_RESERVADA && segundo.clase == NAT_ASIGNAR)
            error_nat(p->ruta, i + 1, "No puedes asignar a una palabra reservada.");
        NatToken ultimo = primero, actual = segundo;
        while (actual.clase != NAT_FIN)
        {
            ultimo = actual;
            actual = nat_siguiente(&cursor, p->ruta, i + 1);
        }
        necesita_cuerpo = nat_palabra(&primero, "si") || nat_palabra(&primero, "mientras");
        if (necesita_cuerpo && ultimo.clase != NAT_DOSPUNTOS)
            error_nat(p->ruta, i + 1, "Falta ':' en el bloque.");
        anterior = nivel;
        ultima_linea = i + 1;
    }
    if (necesita_cuerpo)
        error_nat(p->ruta, ultima_linea + 1, "El bloque esta vacio.");
}

static void ejecutar_archivo(const char *ruta, int profundidad_archivos)
{
    if (profundidad_archivos >= MAX_PROFUNDIDAD_ARCHIVOS)
        error_general("Limite de archivos anidados alcanzado.");

    Programa programa;

    cargar_programa(&programa, ruta);
    validar_estructura(&programa);

    ejecutar_rango(
        &programa,
        0,
        programa.total,
        -1,
        0,
        profundidad_archivos);

    liberar_programa(&programa);
}

static void ejecutar_rango(
    Programa *p,
    int inicio,
    int fin,
    int indent_padre,
    int profundidad_bloques,
    int profundidad_archivos)
{
    if (profundidad_bloques > MAX_PROFUNDIDAD_BLOQUES)
        error_nat(p->ruta, inicio + 1, "Demasiados bloques anidados.");

    int pc = inicio;

    while (pc < fin)
    {
        char linea[MAX_LINEA];
        strcpy(linea, p->lineas[pc]);

        if (linea_ignorable(linea))
        {
            pc++;
            continue;
        }

        int nivel = obtener_indentacion(linea, p->ruta, pc + 1);

        if (indent_padre == -1 && nivel != 0)
        {
            error_nat(
                p->ruta,
                pc + 1,
                "Indentacion inesperada fuera de un bloque.");
        }

        if (nivel <= indent_padre)
            return;

        char *instruccion = quitar_indentacion(linea);
        quitar_comentario(instruccion);
        instruccion = recortar(instruccion);

        if (*instruccion == '\0')
        {
            pc++;
            continue;
        }

        int numero_linea = pc + 1;

        const char *cursor = instruccion;
        NatToken primero = nat_siguiente(&cursor, p->ruta, numero_linea);
        const char *argumentos = cursor;
        NatToken segundo = nat_siguiente(&cursor, p->ruta, numero_linea);
        if (segundo.clase == NAT_ASIGNAR)
        {
            if (primero.clase == NAT_RESERVADA)
                error_nat(p->ruta, numero_linea, "No puedes asignar a una palabra reservada.");
            ejecutar_asignacion(instruccion, p->ruta, numero_linea);
            pc++;
            continue;
        }
        if (segundo.clase == NAT_IGUAL || segundo.clase == NAT_DISTINTO)
            error_nat(p->ruta, numero_linea, "Una comparacion no es una asignacion; usa '='.");
        int es_si = nat_palabra(&primero, "si");
        int es_mientras = nat_palabra(&primero, "mientras");

        /* SI y MIENTRAS */
        if (es_si || es_mientras)
        {
            char *condicion = (char *)argumentos;
            condicion = recortar(condicion);
            size_t n = strlen(condicion);

            if (n == 0 || condicion[n - 1] != ':')
                error_nat(p->ruta, numero_linea, "Falta ':' en el bloque.");

            int cuerpo_inicio = pc + 1;
            int cuerpo_fin = encontrar_fin_bloque(
                p, cuerpo_inicio, fin, nivel);

            if (es_si)
            {
                if (evaluar_condicion(condicion, p->ruta, numero_linea))
                {
                    ejecutar_rango(
                        p,
                        cuerpo_inicio,
                        cuerpo_fin,
                        nivel,
                        profundidad_bloques + 1,
                        profundidad_archivos);
                }
            }
            else
            {
                while (evaluar_condicion(condicion, p->ruta, numero_linea))
                {
                    total_iteraciones++;

                    if (total_iteraciones > MAX_ITERACIONES)
                        error_nat(
                            p->ruta,
                            numero_linea,
                            "Limite global de iteraciones alcanzado.");

                    ejecutar_rango(
                        p,
                        cuerpo_inicio,
                        cuerpo_fin,
                        nivel,
                        profundidad_bloques + 1,
                        profundidad_archivos);
                }
            }

            pc = cuerpo_fin;
            continue;
        }

        /* IMPRIMIR */
        if (nat_palabra(&primero, "imprimir"))
        {
            char *argumento = recortar((char *)argumentos);

            if (*argumento == '\0')
                error_nat(p->ruta, numero_linea, "imprimir necesita un argumento.");

            char resultado[MAX_VALOR];

            resolver_operando(
                argumento,
                resultado,
                sizeof(resultado),
                p->ruta,
                numero_linea);

            printf("%s\n", resultado);
            pc++;
            continue;
        }

        /* LEER */
        if (nat_palabra(&primero, "leer"))
        {
            const char *entrada = argumentos;
            NatToken archivo = nat_siguiente(&entrada, p->ruta, numero_linea);
            NatToken fin = nat_siguiente(&entrada, p->ruta, numero_linea);
            if (archivo.clase != NAT_CADENA || fin.clase != NAT_FIN)
                error_nat(p->ruta, numero_linea, "Sintaxis correcta: leer \"archivo.nat\".");
            if (archivo.valor[0] == '\0')
                error_nat(p->ruta, numero_linea, "La ruta no puede estar vacia.");
            if (strchr(archivo.valor, '\n') || strchr(archivo.valor, '\t'))
                error_nat(p->ruta, numero_linea, "La ruta no puede contener saltos de linea ni tabuladores.");
            const char *ruta_solicitada = archivo.valor;
            char ruta_final[MAX_RUTA];

            construir_ruta_include(
                p->ruta,
                ruta_solicitada,
                ruta_final,
                sizeof(ruta_final),
                p->ruta,
                numero_linea);

            ejecutar_archivo(ruta_final, profundidad_archivos + 1);

            pc++;
            continue;
        }

        error_nat(p->ruta, numero_linea, "Instruccion desconocida.");
    }
}

/* =========================================================
   PROGRAMA PRINCIPAL
   ========================================================= */

int main(int argc, char **argv)
{
    if (argc != 2)
    {
        fprintf(stderr, "Nat %s\nUso: nat archivo.nat\n", NAT_VERSION);
        return EXIT_FAILURE;
    }

    ejecutar_archivo(argv[1], 0);

    return EXIT_SUCCESS;
}
