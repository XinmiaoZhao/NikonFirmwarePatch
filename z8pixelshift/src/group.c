/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Bounded metadata-only discovery. The FS enumeration callback never performs FS I/O.
   Camera files stay read-only. No external config or filenames determine group membership.
   PS7: both cards and every group. A refused frame marks its own group, not the scan; a merged output is a
   <first frame stem>_MERGED.NEFX or _MERGED_<2..99>.NEFX beside the first frame (the name PS1-PS6 give it). */
#include "group.h"
static uint32_t g16(const uint8_t *b) { return b[0] | (uint32_t)b[1]<<8; }
static uint32_t g32(const uint8_t *b) { return g16(b) | g16(b+2)<<16; }
static void gput(uint8_t *b,uint32_t v) { for(unsigned i=0;i<4;++i)b[i]=(uint8_t)(v>>(i*8)); }
static void gzero(void *b,size_t n) { uint8_t *p=b;while(n--)*p++=0; }
static void gcopy(void *d,const void *s,size_t n) { uint8_t *a=d;const uint8_t *b=s;while(n--)*a++=*b++; }
static int geq(const void *a,const void *b,size_t n) { const uint8_t *x=a,*y=b;while(n--)if(*x++!=*y++)return 0;return 1; }
static unsigned glen(const char *s) { unsigned n=0;while(s[n])++n;return n; }
static int gupper(int c) { return c>='a'&&c<='z'?c-32:c; }
static int gieq(const char *a,const char *b,unsigned n) { while(n--)if(gupper(*a++)!=gupper(*b++))return 0;return 1; }
static int gpath(char *out,const char *base,const char *name) {
    unsigned a=glen(base),b=glen(name);if(a+b+2>128)return 1;
    gcopy(out,base,a);if(a && out[a-1]!='\\')out[a++]='\\';gcopy(out+a,name,b+1);return 0;
}
typedef struct { const psm_platform *p;int fd;uint32_t size,at,used;uint8_t *cache; } greader;
static int gread(greader *r,uint32_t at,void *out,uint32_t n) {
    uint8_t *d=out;if(at>r->size||n>r->size-at)return PSM_BAD_NEF;
    while(n) {
        if(!r->used||at<r->at||at-r->at>=r->used) {
            r->at=at&~(PSM_SCAN_CACHE-1u);r->used=r->size-r->at;if(r->used>PSM_SCAN_CACHE)r->used=PSM_SCAN_CACHE;
            if(r->p->read_at(r->p->context,r->fd,r->at,r->cache,r->used))return PSM_READ_ERROR;
        }
        uint32_t k=r->used-(at-r->at);if(k>n)k=n;gcopy(d,r->cache+at-r->at,k);d+=k;at+=k;n-=k;
    }return 0;
}
/* Exact tag type/count, duplicate rejection, overflow and MakerNote extent checks. */
static int gtag(greader *r,uint32_t base,uint32_t limit,uint32_t ifd,uint16_t tag,
                uint16_t type,uint32_t count,void *out) {
    uint8_t b[12];uint32_t found=0,n,unit=type==3?2:type==4?4:(type==5||type==10)?8:1;
    if(ifd<base||ifd>limit||limit-ifd<2||gread(r,ifd,b,2))return PSM_BAD_NEF;
    n=g16(b);if(n>512||(uint64_t)ifd+2+12*n>limit)return PSM_BAD_NEF;
    for(uint32_t i=0;i<n;++i) {
        if(gread(r,ifd+2+12*i,b,12))return PSM_READ_ERROR;
        if(g16(b)!=tag)continue;
        if(found++||g16(b+2)!=type||g32(b+4)!=count)return PSM_BAD_NEF;
        uint32_t bytes=unit*count;
        if(bytes<=4)gcopy(out,b+8,bytes);
        else {
            uint64_t off=(uint64_t)base+g32(b+8);
            if(off>limit||bytes>limit-off)return PSM_BAD_NEF;
            int st=gread(r,(uint32_t)off,out,bytes);if(st)return st;
        }
    }return found?0:PSM_BAD_NEF;
}
/* PS12: 0x0056 bytes 4-7 name the first file of the burst, the same word in every frame of a group (ExifTool
   MakerNotes0x56 BurstStart*): bit 29 = slot - 1, bits 19-28 folder, bits 5-18 file number, bits 0-4 file type
   (2 = NEF; pixel shift records RAW only). PS3-PS11 compared its low half with 0x0022 (file 1 of a NEF burst), which
   refused every group whose first file number is not 1 mod 2048 (issue #17: 102NCZ_8/DSC_2841 gives 0x03316322). */
static int gstart(uint32_t v) {
    uint32_t folder=(v>>19)&0x3FFu,file=(v>>5)&0x3FFFu;
    return !(v&0xC0000000u)&&folder>=100&&folder<=999&&file>=1&&file<=9999&&(v&0x1Fu)==2;
}
/* PS7: identity bit 1 = a Z 8 NEF; bit 2 = count, index, group, start, serial and time are known, so a later
   refusal belongs to that group. The checks are PS6's; serial and time are read before the checks of one frame. */
int psm_probe_metadata(const psm_platform *p,int fd,uint32_t size,psm_metadata *m,void *cache) {
    greader r={p,fd,size,0,0,cache};uint8_t b[64];uint32_t ifd,exif,base,limit,mifd;
    gzero(m,sizeof(*m));
    if(gread(&r,0,b,8))return PSM_READ_ERROR;
    if(!geq(b,"II\x2a\0",4))return PSM_UNSUPPORTED_NEF;
    ifd=g32(b+4);
    if(gtag(&r,0,size,ifd,0x110,2,10,b)||!geq(b,"NIKON Z 8\0",10))return PSM_UNSUPPORTED_NEF;
    m->identity=1;
    if(gtag(&r,0,size,ifd,0x8769,4,1,b))return PSM_BAD_NEF;exif=g32(b);
    /* MakerNote length is variable; locate its descriptor without following arbitrary IFDs. */
    if(gread(&r,exif,b,2))return PSM_BAD_NEF;
    uint32_t n=g16(b),seen=0;base=limit=0;
    if(n>512||(uint64_t)exif+2+12*n>size)return PSM_BAD_NEF;
    for(uint32_t i=0;i<n;++i) {
        if(gread(&r,exif+2+12*i,b,12))return PSM_READ_ERROR;
        if(g16(b)!=0x927c)continue;
        if(seen++||g16(b+2)!=7)return PSM_BAD_NEF;
        uint32_t len=g32(b+4),at=g32(b+8);
        if(len<18||at>size||len>size-at)return PSM_BAD_NEF;base=at+10;limit=at+len;
    }
    if(!seen||gread(&r,base-10,b,18)||!geq(b,"Nikon\0\2\21\0\0II\x2a\0",14))return PSM_BAD_NEF;
    if(g32(b+14)>limit-base)return PSM_BAD_NEF;mifd=base+g32(b+14);
    /* The mode/index block distinguishes ordinary NEFs from pixel-shift files. */
    if(gtag(&r,base,limit,mifd,0x5e,7,28,b))return PSM_BAD_NEF;
    if(!geq(b,"0100",4))return PSM_UNSUPPORTED_NEF;
    if(!b[4])return PSM_BAD_CONFIG; /* ordinary photo, not a candidate */
    if(b[4]>4)return PSM_UNSUPPORTED_NEF;
    /* PS6: modes 1-4 = 4, 8, 16, 32 shots. The frame index is 0x0056's (1..n). 0x005E numbers the place in its
       pass, pass * 16 + place: an 8-shot group's second pass is 17-20 (299NCZ_8), a 32-shot group's 17-32. */
    m->count=4u<<(b[4]-1);uint32_t place=b[5];
    if(gtag(&r,base,limit,mifd,0x56,7,16,b)||!geq(b,"0100",4)||!gstart(g32(b+4))||g32(b+12)!=1)return PSM_BAD_GROUP;
    m->index=g32(b+8);
    if(!m->index||m->index>m->count)return PSM_BAD_GROUP;
    m->group=g32(b+4);   /* PS12: the whole start-file word; PS3-PS11 kept its high half (slot and folder) */
    if(gtag(&r,base,limit,mifd,0xa7,4,1,b)||g32(b)<m->index)return PSM_BAD_GROUP;
    m->start=g32(b)-m->index+1;
    if(gtag(&r,base,limit,mifd,0x1d,2,8,m->serial)||gtag(&r,0,size,exif,0x9003,2,20,m->time)||m->time[19])
        return PSM_BAD_GROUP;
    m->identity=3;
    uint32_t half=m->count==8||m->count==32?m->count/2:m->count;
    if(place!=(m->index>half?16+m->index-half:m->index))return PSM_BAD_GROUP;
    if(gtag(&r,base,limit,mifd,0x54,7,20,b)||!geq(b,"0100",4))return PSM_BAD_GROUP;
    for(unsigned i=0;i<2;++i) {m->shift[i]=(int32_t)g32(b+4+8*i);m->denominator[i]=g32(b+8+8*i);
        if(m->denominator[i]!=256||m->shift[i]<-4096||m->shift[i]>4096)return PSM_BAD_LATTICE;}
    if(gtag(&r,base,limit,mifd,0x0c,5,4,b))return PSM_BAD_GROUP;
    for(unsigned i=0;i<8;++i){m->wb[i]=g32(b+4*i);if(!m->wb[i]||m->wb[i]>1000000)return PSM_BAD_GROUP;}
    if(gtag(&r,base,limit,mifd,0x3d,3,4,b))return PSM_BAD_GROUP;
    for(unsigned i=0;i<4;++i)m->black[i]=(uint16_t)g16(b+2*i);
    if(gtag(&r,base,limit,mifd,0x45,3,4,b))return PSM_BAD_GROUP;
    for(unsigned i=0;i<4;++i)m->crop[i]=(uint16_t)g16(b+2*i);
    if(gtag(&r,base,limit,mifd,0x1b,3,7,b))return PSM_BAD_GROUP;
    for(unsigned i=0;i<7;++i)m->dimensions[i]=(uint16_t)g16(b+2*i);
    /* The currently supported camera crop has been checked against PS2/NX Studio. */
    if(m->dimensions[1]!=8280||m->dimensions[2]!=5520||m->dimensions[3]!=8280||m->dimensions[4]!=5520||
       m->crop[0]!=12||m->crop[1]!=8||m->crop[2]!=8256||m->crop[3]!=5504)return PSM_BAD_CROP;
    if(gtag(&r,0,size,exif,0x829a,5,1,m->exposure)||gtag(&r,0,size,exif,0x829d,5,1,m->exposure+8)||
       gtag(&r,0,size,exif,0x8827,3,1,m->exposure+16)||gtag(&r,0,size,exif,0x920a,5,1,m->exposure+18))
        return PSM_BAD_GROUP;
    return 0;
}
/* Read-only debugger observation point: the discovery check that refused (site), two values and the candidate. */
__attribute__((noinline,used)) void psm_group_reject(uint32_t site,uint32_t first,uint32_t second,const char *path) {
    __asm__ volatile("" : : "r"(site), "r"(first), "r"(second), "r"(path) : "memory");
}
static int greject(int st,uint32_t site,uint32_t first,uint32_t second,const char *path) {
    psm_group_reject(site,first,second,path);return st;
}
/* PS7: <stem>_MERGED.NEFX or <stem>_MERGED_<n>.NEFX, n = 2..99 without a leading zero (PS1 choose_output); the stem
   of an 8.3 NEF name has 1..8 characters. Returns the stem length, 0 for any other name. */
static unsigned gmerged(const char *name,unsigned n) {
    if(n<13||!gieq(name+n-5,".NEFX",5))return 0;
    unsigned e=n-5;
    if(name[e-1]>='0'&&name[e-1]<='9') {
        if(name[e-2]>='0'&&name[e-2]<='9'){if(name[e-2]=='0'||e<3||name[e-3]!='_')return 0;e-=3;}
        else{if(name[e-1]<'2'||name[e-2]!='_')return 0;e-=2;}
    }
    if(e<8||!gieq(name+e-7,"_MERGED",7))return 0;
    e-=7;return e>=1&&e<=8?e:0;
}
typedef struct {psm_scan *s;psm_entry *entries;uint32_t count,capacity,overflow,dirs;uint16_t dir;} glist;
/* PS7: names of up to 31 characters arrive whole (firmware native_listing); a longer one arrives as its first 32
   and is skipped here. */
static int gcollect(void *opaque,const char *name,uint64_t bytes,uint32_t attrs) {
    glist *l=opaque;psm_scan *s=l->s;unsigned n=0;while(n<32&&name[n])++n;
    if(!n||n==32||name[0]=='.')return 0;
    if(l->dirs) {if(!(attrs&16)||n>12)return 0;}
    else {
        if(attrs&16)return 0;
        unsigned stem=gmerged(name,n);
        if(stem) {
            if(s->nmerged==PSM_SCAN_MERGED){l->overflow=1;return 1;}
            psm_merged_ref *m=&s->merged[s->nmerged++];m->dir=l->dir;gcopy(m->stem,name,stem);m->stem[stem]=0;return 0;
        }
        if(n>12||n<5||!gieq(name+n-4,".NEF",4))return 0;
    }
    if(l->count==l->capacity){l->overflow=1;return 1;}
    psm_entry *e=&l->entries[l->count++];gcopy(e->name,name,n+1);e->attrs=(uint8_t)attrs;e->dir=l->dir;e->bytes=bytes;return 0;
}
static int gnewdir(psm_scan *s,const char *base,const char *name,uint16_t *dir) {
    char path[128];
    if(s->ndirs==2u*(PSM_SCAN_DIRS+1u))return PSM_SCAN_LIMIT;
    if(gpath(path,base,name)||glen(path)>=PSM_DIR_PATH)return greject(PSM_BAD_GROUP,6,s->ndirs,0,base);
    gcopy(s->dir_paths[s->ndirs],path,glen(path)+1);*dir=(uint16_t)s->ndirs++;return 0;
}
/* The group of a probed frame: same card, serial, first frame, group id and count. */
static int gadd(psm_scan *s,uint8_t card,const psm_entry *e,uint32_t bytes,const psm_metadata *m,int st) {
    psm_group *g=0;
    for(uint32_t i=s->ngroups;i--;) {
        psm_group *c=&s->groups[i];
        if(c->card==card&&c->start==m->start&&c->group==m->group&&c->count==m->count&&geq(c->serial,m->serial,32)){g=c;break;}
    }
    if(!g) {
        if(s->ngroups==PSM_SCAN_GROUPS)return PSM_SCAN_LIMIT;
        g=&s->groups[s->ngroups++];gzero(g,sizeof(*g));
        g->card=card;g->start=m->start;g->group=m->group;g->count=m->count;gcopy(g->serial,m->serial,32);gcopy(g->time,m->time,20);
        for(unsigned k=0;k<32;++k)g->frames[k]=PSM_NO_FRAME;
    }
    if(s->nframes==PSM_SCAN_FRAMES)return PSM_SCAN_LIMIT;
    psm_frame_ref *f=&s->frames[s->nframes];
    f->bytes=bytes;f->metadata=psm_crc32(m,sizeof(*m),0);f->dir=e->dir;f->status=(uint8_t)st;gcopy(f->name,e->name,13);
    unsigned k=m->index-1;
    if(g->frames[k]!=PSM_NO_FRAME)g->duplicate=1;
    else {g->frames[k]=(uint16_t)s->nframes;g->mask|=1u<<k;if(!k)gcopy(g->time,m->time,20);}
    ++s->nframes;
    if(st&&!g->status)g->status=(uint8_t)st;
    return 0;
}
static int gscan(const psm_platform *p,psm_scan *s,unsigned card,uint16_t dir) {
    const char *directory=s->dir_paths[dir];psm_card_scan *c=&s->cards[card];
    glist l={s,s->files,0,PSM_SCAN_FILES,0,0,dir};
    if(p->list(p->context,directory,0x27,gcollect,&l))return glen(directory)==3?PSM_NO_CARD:PSM_READ_ERROR;
    if(l.overflow)return PSM_SCAN_LIMIT;
    for(uint32_t i=0;i<l.count;++i) {
        uint32_t bytes=0;char path[128];psm_metadata m;
        if(p->cancelled&&p->cancelled(p->context))return PSM_CANCELLED;
        PSM_PHASE(p,PSM_PHASE_SCAN,(uint8_t)directory[0],++s->probed); /* PS4: reported before the file is opened */
        ++c->nefs;
        if(gpath(path,directory,s->files[i].name))return greject(PSM_BAD_GROUP,1,i,0,directory);
        int fd=p->open(p->context,path,&bytes),st;
        if(fd<0)st=PSM_READ_ERROR;
        else {
            st=psm_probe_metadata(p,fd,bytes,&m,s->cache);
            if(p->close(p->context,fd)){p->close(p->context,fd);return PSM_READ_ERROR;}
        }
        if(fd>=0&&st==PSM_BAD_CONFIG){++c->ordinary;continue;}
        if(fd<0||!(m.identity&2)) {
            /* PS7: a refused file whose group is unknown is counted and named in the log; it cannot be a frame of a
               complete group (each group needs all of its frame numbers, each once). */
            if(fd>=0&&!(m.identity&1)){++c->other;continue;}
            if(!c->unattributed++){c->first_status=st;unsigned k=glen(path);if(k>47)k=47;gcopy(c->first_path,path,k);c->first_path[k]=0;}
            psm_group_reject(2,(uint32_t)st,fd>=0?m.index:0,path);
            continue;
        }
        if(!st&&bytes!=s->files[i].bytes)st=greject(PSM_BAD_GROUP,3,bytes,(uint32_t)s->files[i].bytes,path);
        else if(st)psm_group_reject(2,(uint32_t)st,m.index,path);
        ++c->candidates;
        int added=gadd(s,(uint8_t)('A'+card),&s->files[i],bytes,&m,st);if(added)return added;
    }return 0;
}
static int gnewer(const psm_group *a,const psm_group *b) {
    for(unsigned i=0;i<19;++i)if(a->time[i]!=b->time[i])return (uint8_t)a->time[i]>(uint8_t)b->time[i];
    if(a->start!=b->start)return a->start>b->start;
    if(a->card!=b->card)return a->card<b->card;
    return a->group>b->group;
}
int psm_scan_cards(const psm_platform *p,psm_scan *s) {
    if(!p->list)return PSM_BAD_PLAN;
    unsigned present=0;
    for(unsigned card=0;card<2;++card) {
        psm_card_scan *c=&s->cards[card];
        char root[4]="A:\\";root[0]=(char)('A'+card);
        uint16_t dir;uint64_t t0=p->ticks?p->ticks(p->context):0;
        int st=gnewdir(s,"",root,&dir);if(st)return st;
        st=gscan(p,s,card,dir);
        if(st==PSM_NO_CARD)continue;
        if(st)return st;
        c->present=1;++present;c->dirs=1;
        glist rootdirs={s,s->dirs,0,PSM_SCAN_DIRS,0,1,dir};
        if(p->list(p->context,root,0x13,gcollect,&rootdirs))return PSM_READ_ERROR;
        if(rootdirs.overflow)return PSM_SCAN_LIMIT;
        unsigned has_dcim=0;
        for(unsigned i=0;i<rootdirs.count;++i)if(geq(s->dirs[i].name,"DCIM",5))has_dcim=1;
        if(has_dcim) {
            uint16_t dcim;
            if((st=gnewdir(s,root,"DCIM",&dcim)))return st;
            glist l={s,s->dirs,0,PSM_SCAN_DIRS,0,1,dcim};
            if(p->list(p->context,s->dir_paths[dcim],0x13,gcollect,&l))return PSM_READ_ERROR;
            if(l.overflow)return PSM_SCAN_LIMIT;
            --s->ndirs;           /* DCIM itself is listed for folders only */
            char base[PSM_DIR_PATH];gcopy(base,s->dir_paths[dcim],glen(s->dir_paths[dcim])+1);
            for(unsigned i=0;i<l.count;++i) {
                if((st=gnewdir(s,base,s->dirs[i].name,&dir)))return st;
                ++c->dirs;
                if((st=gscan(p,s,card,dir)))return st;
            }
        }
        if(p->ticks)c->ticks=p->ticks(p->context)-t0;
    }
    if(!present)return PSM_NO_CARD;
    /* merged: the first frame's folder holds <its stem>_MERGED[_n].NEFX */
    for(uint32_t i=0;i<s->ngroups;++i) {
        psm_group *g=&s->groups[i];
        if(g->frames[0]==PSM_NO_FRAME)continue;
        const psm_frame_ref *f=&s->frames[g->frames[0]];unsigned stem=glen(f->name)-4;
        for(uint32_t k=0;k<s->nmerged&&!g->merged;++k)
            if(s->merged[k].dir==f->dir&&glen(s->merged[k].stem)==stem&&gieq(s->merged[k].stem,f->name,stem))g->merged=1;
    }
    for(uint32_t i=0;i<s->ngroups;++i) {
        uint32_t k=i;
        while(k&&gnewer(&s->groups[i],&s->groups[s->order[k-1]])){s->order[k]=s->order[k-1];--k;}
        s->order[k]=(uint16_t)i;
    }
    return 0;
}
int psm_group_mergeable(const psm_group *g) {
    uint32_t all=g->count==32?0xFFFFFFFFu:(1u<<g->count)-1u;
    return (g->count==4||g->count==8||g->count==16||g->count==32)&&g->mask==all&&!g->duplicate&&!g->status;
}
/* PS7: the groups a job merges, newest first: unmerged complete groups, only the first for PSM_MODE_NEWEST. */
uint32_t psm_targets(const psm_scan *s,uint32_t mode,uint16_t *out) {
    uint32_t n=0;
    for(uint32_t i=0;i<s->ngroups&&(mode==PSM_MODE_ALL||!n);++i) {
        const psm_group *g=&s->groups[s->order[i]];
        if(!g->merged&&psm_group_mergeable(g))out[n++]=s->order[i];
    }return n;
}
int psm_frame_path(const psm_scan *s,const psm_group *g,uint32_t i,char *out) {
    if(i>=g->count||g->frames[i]==PSM_NO_FRAME)return PSM_BAD_GROUP;
    const psm_frame_ref *f=&s->frames[g->frames[i]];
    return gpath(out,s->dir_paths[f->dir],f->name)?PSM_BAD_GROUP:0;
}
/* PS6 psm_auto_config's plan, from the metadata of the group's open frames (selected[i] = frame i + 1). */
int psm_group_config(const psm_scan *s,const psm_group *g,const psm_metadata *selected,const uint32_t *sizes,
                     uint8_t *c,uint32_t *bytes) {
    char path[128];
    unsigned n=g->count,scale=n>=16?2:1;
    if(n!=4&&n!=8&&n!=16&&n!=32)return PSM_NEFX_MODE;
    for(unsigned i=0;i<n;++i) {
        const psm_metadata *m=&selected[i];
        if(psm_frame_path(s,g,i,path))return PSM_BAD_GROUP;
        /* the frame read now is the one scanned: same group, number and camera */
        if(m->identity!=3||m->count!=n||m->index!=i+1||m->start!=g->start||m->group!=g->group||!geq(m->serial,g->serial,32))
            return greject(PSM_BAD_GROUP,11,i,m->index,path);
    }
    int32_t shift[32][2],minimum[2]={100,100};
    for(unsigned i=0;i<n;++i) {
        const psm_metadata *m=&selected[i],*a=&selected[0];
        if(!geq(m->wb,a->wb,sizeof(*m)-__builtin_offsetof(psm_metadata,wb))) {
            psm_frame_path(s,g,i,path);return greject(PSM_BAD_GROUP,8,i,0,path);
        }
        for(unsigned k=0;k<2;++k) {
            int v=m->shift[k]*(int)scale,mag=v<0?-v:v;
            int round=(mag+128)/256;int residual=mag-round*256;if(residual<0)residual=-residual;
            /* Exact half-step ties and residual >= 1/4 pixel are ambiguous. */
            if(residual*4>=256*(int)scale){psm_frame_path(s,g,i,path);return greject(PSM_BAD_LATTICE,9,i,k,path);}
            shift[i][k]=(v<0?round:-round)*(2/(int)scale);
            if(shift[i][k]<minimum[k])minimum[k]=shift[i][k];
        }
    }
    *bytes=384+192*n;gzero(c,*bytes);gcopy(c,"Z8PSMERGEv1",11);gput(c+16,1);gput(c+24,g->group);
    gput(c+32,n);gput(c+36,8280);gput(c+40,5520);gput(c+44,scale);
    for(unsigned i=0;i<4;++i)gput(c+48+4*i,selected[0].crop[i]*scale);
    gput(c+64,selected[0].wb[1]);gput(c+68,selected[0].wb[0]);gput(c+72,1);gput(c+76,1);
    gput(c+80,selected[0].wb[3]);gput(c+84,selected[0].wb[2]);
    /* Keep output next to its first frame. The job chooses _2 .. _99 on collision. */
    psm_frame_path(s,g,0,path);
    unsigned len=glen(path);if(len<5||len+9>128)return PSM_BAD_GROUP;
    gcopy(c+88,path,len+1);gcopy(c+88+len-4,"_MERGED.NEFX",13);
    gcopy(c+216,"A:\\PSMERGE.TMP",15);c[216]=g->card;
    for(unsigned i=0;i<n;++i) {
        uint8_t *r=c+384+192*i;gput(r,i);gput(r+4,(uint32_t)(shift[i][0]-minimum[0]));gput(r+8,(uint32_t)(shift[i][1]-minimum[1]));gput(r+12,sizes[i]);
        for(unsigned k=0;k<4;++k){uint16_t v=selected[i].black[k];r[16+2*k]=(uint8_t)v;r[17+2*k]=(uint8_t)(v>>8);r[24+2*k]=0xcf;r[25+2*k]=0x3b;}
        r[32]=0;r[33]=r[34]=1;r[35]=2;psm_frame_path(s,g,i,path);gcopy(r+40,path,glen(path)+1);
    }
    gput(c+380,psm_crc32(c+384,*bytes-384,psm_crc32(c,380,0)));
    return 0;
}
