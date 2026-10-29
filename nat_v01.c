#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

typedef struct
{
    char nombre[64];
    char valor[256];
} Variable;

Variable memoria[100];
int total_variables = 0;

char lineas[500][512];
int total_lineas = 0;

void error_nat(const char *mensaje, int linea)
{
    printf("[Error en Nat (Linea %d)]: %s\n", linea, mensaje);
    exit(1);
}

void asignar_variable(const char *nombre, const char *valor)
{
    for (int i = 0; i < total_variables; i++)
    {
        if (strcmp(memoria[i].nombre, nombre) == 0)
        {
            strcpy(memoria[i].valor, valor);
            return;
        }
    }
    if (total_variables < 100)
    {
        strcpy(memoria[total_variables].nombre, nombre);
        strcpy(memoria[total_variables].valor, valor);
        total_variables++;
    }
}

const char *obtener_variable(const char *nombre)
{
    for (int i = 0; i < total_variables; i++)
    {
        if (strcmp(memoria[i].nombre, nombre) == 0)
        {
            return memoria[i].valor;
        }
    }
    return NULL;
}

int evaluar_condicion(const char *var_nombre, const char *operador, const char *valor_comparar)
{
    const char *val_real = obtener_variable(var_nombre);
    if (!val_real)
        val_real = "";

    if (strcmp(operador, "==") == 0)
    {
        return strcmp(val_real, valor_comparar) == 0;
    }
    else if (strcmp(operador, "!=") == 0)
    {
        return strcmp(val_real, valor_comparar) != 0;
    }
    return 0;
}

void cargar_archivo(const char *ruta)
{
    FILE *archivo = fopen(ruta, "r");
    if (archivo == NULL)
    {
        printf("No se pudo abrir el archivo: %s\n", ruta);
        exit(1);
    }

    total_lineas = 0;
    while (fgets(lineas[total_lineas], sizeof(lineas[total_lineas]), archivo) != NULL)
    {
        total_lineas++;
    }
    fclose(archivo);
}

void ejecutar_bloque(int inicio, int fin)
{
    int pc = inicio;
    while (pc <= fin)
    {
        char linea_buffer[512];
        strcpy(linea_buffer, lineas[pc]);
        linea_buffer[strcspn(linea_buffer, "\r\n")] = 0;

        if (strlen(linea_buffer) == 0 || linea_buffer[0] == '#')
        {
            pc++;
            continue;
        }

        if (strncmp(linea_buffer, "imprimir ", 9) == 0)
        {
            char *argumento = linea_buffer + 9;
            if (argumento[0] == '"' && argumento[strlen(argumento) - 1] == '"')
            {
                argumento[strlen(argumento) - 1] = '\0';
                printf("%s\n", argumento + 1);
            }
            else
            {
                const char *val_var = obtener_variable(argumento);
                if (val_var != NULL)
                {
                    printf("%s\n", val_var);
                }
                else
                {
                    error_nat("Variable no definida", pc + 1);
                }
            }
        }
        else
        {
            char *igual = strchr(linea_buffer, '=');
            if (igual != NULL)
            {
                *igual = '\0';
                char nombre_var[64];
                char valor_var[256];
                sscanf(linea_buffer, "%s", nombre_var);

                char *val_raw = igual + 1;
                while (*val_raw == ' ')
                    val_raw++;

                if (val_raw[0] == '"')
                {
                    val_raw++;
                    char *fin_comilla = strchr(val_raw, '"');
                    if (fin_comilla)
                        *fin_comilla = '\0';
                    strcpy(valor_var, val_raw);
                }
                else
                {
                    strcpy(valor_var, val_raw);
                }
                asignar_variable(nombre_var, valor_var);
            }
        }
        pc++;
    }
}

void ejecutar_programa()
{
    int pc = 0;
    while (pc < total_lineas)
    {
        char linea_buffer[512];
        strcpy(linea_buffer, lineas[pc]);
        linea_buffer[strcspn(linea_buffer, "\r\n")] = 0;

        if (strlen(linea_buffer) == 0 || linea_buffer[0] == '#')
        {
            pc++;
            continue;
        }

        if (strncmp(linea_buffer, "mientras ", 8) == 0)
        {
            char var_nombre[64], operador[8], valor_comparar[256];
            sscanf(linea_buffer + 8, "%s %s \"%[^\"]\"", var_nombre, operador, valor_comparar);

            int inicio_cuerpo = pc + 1;
            int fin_cuerpo = total_lineas - 1; // Ejecuta hasta el final del bloque/archivo para este prototipo

            while (evaluar_condicion(var_nombre, operador, valor_comparar))
            {
                ejecutar_bloque(inicio_cuerpo, fin_cuerpo);
            }
            break; // Termina el programa tras el bucle
        }
        else
        {
            ejecutar_bloque(pc, pc);
            pc++;
        }
    }
}

int main(int argc, char *argv[])
{
    if (argc < 2)
    {
        printf("Uso correcto: nat <archivo.nat>\n");
        return 1;
    }

    cargar_archivo(argv[1]);
    ejecutar_programa();
    return 0;
}