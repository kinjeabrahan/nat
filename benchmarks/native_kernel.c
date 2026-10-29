#include <stdio.h>
#include <stdint.h>
#include <inttypes.h>
#include <stdlib.h>
static int64_t add(int64_t a,int64_t b) { int64_t r; if(__builtin_add_overflow(a,b,&r)) exit(1); return r; }
static int64_t mul(int64_t a,int64_t b) { int64_t r; if(__builtin_mul_overflow(a,b,&r)) exit(1); return r; }
int main(int argc,char **argv) {
    if(argc!=2) return 1;
    int64_t n=strtoimax(argv[1],NULL,10),i=0,x=1;
    while(i<n) { x=add(mul(x,17),i)%1000003; i=add(i,1); }
    printf("%" PRId64 "\n",x);
    return 0;
}
