#include <stdio.h>
#include <stdlib.h>

static char step(const char *mapping, char value)
{
    char text[2] = {value, '\0'};
    return mapping[strtol(text, NULL, 10)];
}

int main(void)
{
    char state = '0';
    char a = '0';
    while (a != '9') {
        char b = '0';
        while (b != '9') {
            char c = '0';
            while (c != '9') {
                char d = '0';
                while (d != '9') {
                    state = step("1234567890", state);
                    d = step("1234567899", d);
                }
                c = step("1234567899", c);
            }
            b = step("1234567899", b);
        }
        a = step("1234567899", a);
    }
    printf("%c\n", state);
    return 0;
}
