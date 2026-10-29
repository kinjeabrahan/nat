/* Tokenizer for the frozen compatibility interpreter. Included after diagnostics. */
typedef enum {
    NAT_FIN, NAT_ID, NAT_ENTERO, NAT_CADENA, NAT_ASIGNAR,
    NAT_IGUAL, NAT_DISTINTO, NAT_ABRE, NAT_CIERRA, NAT_COMA, NAT_DOSPUNTOS,
    NAT_RESERVADA, NAT_OTRO
} NatClase;

typedef struct {
    NatClase clase;
    const char *inicio;
    size_t longitud;
    char valor[MAX_LINEA];
} NatToken;

static int nat_palabra(const NatToken *t, const char *palabra)
{
    return strlen(palabra) == t->longitud &&
           strncmp(t->inicio, palabra, t->longitud) == 0;
}

static int nat_reservada(const NatToken *t)
{
    static const char *const palabras[] = {
        "si", "mientras", "imprimir", "verdadero", "falso", "y", "o", "no",
        "func", "retornar", "leer", "sino"
    };
    for (size_t i = 0; i < sizeof(palabras) / sizeof(palabras[0]); i++)
        if (nat_palabra(t, palabras[i])) return 1;
    return 0;
}

static NatToken nat_siguiente(const char **cursor, const char *ruta, int linea)
{
    const char *p = *cursor;
    while (isspace((unsigned char)*p)) p++;
    NatToken t = {NAT_OTRO, p, 0, {0}};
    if (*p == '\0' || *p == '#') t.clase = NAT_FIN;
    else if (isalpha((unsigned char)*p) || *p == '_') {
        p++;
        while (isalnum((unsigned char)*p) || *p == '_') p++;
        t.longitud = (size_t)(p - t.inicio);
        t.clase = nat_reservada(&t) ? NAT_RESERVADA : NAT_ID;
    }
    else if (isdigit((unsigned char)*p) || (*p == '-' && isdigit((unsigned char)p[1]))) {
        p++;
        while (isdigit((unsigned char)*p)) p++;
        t.clase = NAT_ENTERO;
    }
    else if (*p == '"') {
        p++;
        size_t n = 0;
        while (*p && *p != '"') {
            char c = *p++;
            if (c == '\\') {
                char escape = *p++;
                switch (escape) {
                    case '"': c = '"'; break;
                    case '\\': c = '\\'; break;
                    case 'n': c = '\n'; break;
                    case 't': c = '\t'; break;
                    default: error_nat(ruta, linea, "Escape de cadena no valido.");
                }
            }
            if (n + 1 >= sizeof(t.valor))
                error_nat(ruta, linea, "Cadena demasiado larga.");
            t.valor[n++] = c;
        }
        if (*p != '"') error_nat(ruta, linea, "Cadena sin cerrar.");
        p++;
        t.valor[n] = '\0';
        t.clase = NAT_CADENA;
    }
    else if (p[0] == '=' && p[1] == '=') { t.clase = NAT_IGUAL; p += 2; }
    else if (p[0] == '!' && p[1] == '=') { t.clase = NAT_DISTINTO; p += 2; }
    else {
        switch (*p++) {
            case '=': t.clase = NAT_ASIGNAR; break;
            case '(': t.clase = NAT_ABRE; break;
            case ')': t.clase = NAT_CIERRA; break;
            case ',': t.clase = NAT_COMA; break;
            case ':': t.clase = NAT_DOSPUNTOS; break;
        }
    }
    t.longitud = (size_t)(p - t.inicio);
    *cursor = p;
    return t;
}
