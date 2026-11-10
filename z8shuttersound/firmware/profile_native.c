/* SPDX-License-Identifier: GPL-3.0-or-later
 * Derived from s3lemming/z9-firmware-patch, commit 88a6f3e5195d7f38792dc8eddeb1526fde4096dc.
 * Z8 C3.11 adaptation: native interfaces, event IDs, state addresses and labels.
 * Device-qualified: the full feature set passed complete on-camera verification.
 */
#include "profile.h"
#define FN(a,t) ((t)(uintptr_t)(a))
#define OK 0x4320080u
struct file {const char *path;uint32_t flags,fd;uint64_t cursor,length,auxiliary;};
_Static_assert(sizeof(struct file)==40,"original native file ABI");
static void init(struct file *f,const char *p){FN(0x40863838,void(*)(void *,const char *,uint64_t,uint64_t))(f,p,0,0);}
int m2_native_profile_read(const char *path,uint8_t *b){
 struct file f;init(&f,path);uint32_t status=FN(0x40863860,uint32_t(*)(void *,uint32_t,uint32_t))(&f,0,0);uint32_t actual=0;
 int bad=status!=OK;
 if(!bad && FN(0x40863b14,uint64_t(*)(void *))(&f)!=M2_PROFILE_BYTES)bad=1;
 if(!bad)bad=FN(0x40863b38,uint32_t(*)(void *,void *,uint32_t,uint32_t *))(&f,b,M2_PROFILE_BYTES,&actual)!=OK || actual!=M2_PROFILE_BYTES;
 if(f.fd!=UINT32_MAX && FN(0x408638e8,uint32_t(*)(void *))(&f)!=OK)bad=1;
 return bad;
}
int m2_native_profile_write(const char *path,const uint8_t *b){
 struct file f;init(&f,path);uint32_t status=FN(0x408638c0,uint32_t(*)(void *,uint32_t))(&f,0);uint32_t actual=0;
 int bad=status!=OK;
 if(!bad)bad=FN(0x408639ec,uint32_t(*)(void *,const void *,uint32_t,uint32_t *))(&f,b,M2_PROFILE_BYTES,&actual)!=OK || actual!=M2_PROFILE_BYTES;
 if(f.fd!=UINT32_MAX && FN(0x408638e8,uint32_t(*)(void *))(&f)!=OK)bad=1;
 if(bad)return 1;
 uint8_t verify[M2_PROFILE_BYTES];if(m2_native_profile_read(path,verify))return 1;
 for(unsigned i=0;i<M2_PROFILE_BYTES;i++)if(b[i]!=verify[i])return 1;
 return 0;
}
