#include <stddef.h>
#include <stdint.h>
/* Compiler aggregate helpers; volatile byte accesses avoid recursive lowering. */
void *memcpy(void *dst,const void *src,size_t bytes){volatile uint8_t *d=dst;const volatile uint8_t *s=src;for(size_t i=0;i<bytes;i++)d[i]=s[i];return dst;}
void *memset(void *dst,int value,size_t bytes){volatile uint8_t *d=dst;for(size_t i=0;i<bytes;i++)d[i]=(uint8_t)value;return dst;}
