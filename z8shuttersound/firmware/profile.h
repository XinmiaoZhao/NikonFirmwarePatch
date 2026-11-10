#ifndef M2_PROFILE_H
#define M2_PROFILE_H
#include <stddef.h>
#include <stdint.h>
#define M2_PROFILE_BYTES 160u
struct m2_profile {uint32_t sequence,enabled;char path[128];};
int m2_profile_encode(uint8_t *,uint32_t,uint32_t,const char *);
int m2_profile_decode(const uint8_t *,size_t,struct m2_profile *);
int m2_profile_newest(const struct m2_profile *,int,const struct m2_profile *,int);
int m2_native_profile_read(const char *,uint8_t *);
int m2_native_profile_write(const char *,const uint8_t *);
#endif
