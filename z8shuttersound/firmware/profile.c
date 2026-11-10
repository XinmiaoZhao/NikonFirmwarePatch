#include "profile.h"
static uint32_t get(const uint8_t *b){return b[0]|((uint32_t)b[1]<<8)|((uint32_t)b[2]<<16)|((uint32_t)b[3]<<24);}
static void put(uint8_t *b,uint32_t v){for(unsigned i=0;i<4;i++)b[i]=(uint8_t)(v>>(i*8));}
static uint32_t crc(const uint8_t *b){uint32_t v=~0u;for(unsigned i=0;i<156;i++){v^=b[i];for(unsigned j=0;j<8;j++)v=(v>>1)^((0u-(v&1u))&0xedb88320u);}return ~v;}
static int path_ok(const char *p){
 if(!p || p[0]<'A'||p[0]>'Z')return 0;
 const char *prefix=":\\CUSTOM_SOUND\\";
 for(unsigned i=0;prefix[i];i++)if(p[i+1]!=prefix[i])return 0;
 unsigned n=16;while(n<128 && p[n]){
  if((unsigned char)p[n]<32||(unsigned char)p[n]>126||p[n]=='/'||p[n]=='\\'||
     p[n]==':'||p[n]=='*'||p[n]=='?'||p[n]=='"'||p[n]=='<'||p[n]=='>'||p[n]=='|')return 0;
  n++;
 }
 return n>=21 && n<128 && p[n-4]=='.' && (p[n-3]|32)=='w' && (p[n-2]|32)=='a' && (p[n-1]|32)=='v';
}

int m2_profile_encode(uint8_t *b,uint32_t seq,uint32_t enabled,const char *path){
 if(!b || enabled>1 || (enabled && !path_ok(path)))return 1;
 for(unsigned i=0;i<M2_PROFILE_BYTES;i++)b[i]=0;
 put(b,0x3150324d);put(b+4,1);put(b+8,seq);put(b+12,enabled);
 if(enabled)for(unsigned i=0;path[i];i++)b[16+i]=(uint8_t)path[i];
 put(b+156,crc(b));return 0;
}
int m2_profile_decode(const uint8_t *b,size_t n,struct m2_profile *p){
 if(!b || !p || n!=M2_PROFILE_BYTES || get(b)!=0x3150324d || get(b+4)!=1 || get(b+12)>1 || get(b+156)!=crc(b))return 1;
 for(unsigned i=144;i<156;i++)if(b[i])return 1;
 struct m2_profile tmp={0};tmp.sequence=get(b+8);tmp.enabled=get(b+12);
 unsigned i=0;for(;i<128 && b[16+i];i++)tmp.path[i]=(char)b[16+i];if(i==128)return 1;
 for(unsigned j=i;j<128;j++)if(b[16+j])return 1;
 if(tmp.enabled?!path_ok(tmp.path):tmp.path[0]!=0)return 1;
 *p=tmp;return 0;
}
int m2_profile_newest(const struct m2_profile *a,int av,const struct m2_profile *b,int bv){
 if(!av)return bv?1:-1;
 if(!bv)return 0;
 uint32_t delta=a->sequence-b->sequence;if(delta==0x80000000u)return -2;
 if(!delta){if(a->enabled!=b->enabled)return -2;for(unsigned i=0;i<128;i++)if(a->path[i]!=b->path[i])return -2;return 0;}
 return delta<0x80000000u?0:1;
}
