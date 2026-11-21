/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Native GUI adapter. GUI owns the controller; only the claimed worker owns
   scan/thumbnail preparation. Published scan is immutable through confirmation
   and merge. Thumbnail banks have generation/page identity and render pins. */
static void browser_save_text(int save){
    static const uint16_t fonts[]={4,0x207,0x208,0x20a,0x20b,0x20d,0x20e,0x210,0x211,0x213,0x214,0x21f};
    for(unsigned i=0;i<12;++i){
        void *entry=(void *)(uintptr_t)(DYNAMIC_FONTS+16ull*fonts[i]);
        if(save)memcpy(R->saved_fonts[i],entry,16);else memcpy(entry,R->saved_fonts[i],16);
    }
    uint8_t *flags=(uint8_t *)(uintptr_t)(0xA032AA850ull+BROWSER_ROW_BASE-0x2921);
    if(save)memcpy(R->saved_disabled,flags,BROWSER_ROWS);else memcpy(flags,R->saved_disabled,BROWSER_ROWS);
    for(unsigned i=0;i<BROWSER_TEXT_COUNT;++i){
        uint8_t *entry=(uint8_t *)(uintptr_t)(0xA032BD4A8ull+24ull*(BROWSER_TEXT_BASE+i));
        char *buffer=*(char **)(entry+8);
        if(save){R->text_length[i]=*(uint32_t *)entry;R->text_format[i]=*(uint32_t *)(entry+16);memcpy(R->saved_text[i],buffer,51);}
        else{memcpy(buffer,R->saved_text[i],51);*(uint32_t *)entry=R->text_length[i];*(uint32_t *)(entry+16)=R->text_format[i];}
    }
}
__attribute__((noinline)) static void browser_release(void){
    /* The caller is the GUI with no live worker, or the worker after its last
       I/O callback joined. No thumbnail draw survives a GUI page exit. */
    if(R->scan_memory)FW_FREE(R->scan_memory);
    if(R->thumb_memory)FW_FREE(R->thumb_memory);
    R->scan_memory=R->thumb_memory=0;R->scan=0;R->thumb_pixels=0;
    store32(&R->thumb_bank,UINT32_MAX);R->browser.scan=0;
}
typedef struct {
    const psm_platform *p;
    psm_scan *scan;
    uint32_t operation,page,generation,bank;
    uint8_t *jpeg,*scratch;void *workspace;
    int status;
} browser_request;
static void browser_io(void *argument){
    browser_request *q=argument;const psm_platform *p=q->p;
    if(q->operation==PS8_SCAN){q->status=psm_scan_cards(p,q->scan);return;}
    uint32_t valid=0;
    for(unsigned i=0;i<BROWSER_THUMBS&&q->page+i<q->scan->ngroups;++i){
        if(p->cancelled(p->context)||load32(&R->thumb_requested)!=q->page||load32(&R->thumb_generation)!=q->generation)break;
        const psm_group *g=&q->scan->groups[q->scan->order[q->page+i]];
        char path[128];uint32_t bytes=0;
        if(psm_frame_path(q->scan,g,0,path)||ps8_thumbnail_read(p,path,q->jpeg,&bytes,q->scratch))continue;
        uint8_t *pixels=R->thumb_pixels+(q->bank*BROWSER_THUMBS+i)*PS8_THUMB_RGBA;
        if(!ps8_jpeg_decode(q->jpeg,bytes,pixels,q->workspace,ps8_jpeg_workspace_bytes()))valid|=1u<<i;
    }
    R->thumb_page[q->bank]=q->page;R->thumb_gen[q->bank]=q->generation;R->thumb_valid[q->bank]=valid;
    if(!p->cancelled(p->context)&&load32(&R->thumb_requested)==q->page&&load32(&R->thumb_generation)==q->generation)
        store32(&R->thumb_bank,q->bank);
    q->status=0;
}
__attribute__((noinline,used)) void ps8_browser_prepared(uint32_t operation,uint32_t status,uint32_t value){
    __asm__ volatile("" : : "r"(operation),"r"(status),"r"(value) : "memory");
}
__attribute__((noinline)) static int browser_work(const psm_platform *p,psm_summary *summary){
    uint32_t operation=R->operation;
    if(operation==PS8_MERGE){
        if(R->browser.phase!=PSB_RUNNING||R->browser.scan!=R->scan)return PSM_BAD_GROUP;
        return ps8_selected_job(p,R->scan,R->browser.targets,R->browser.target_count,summary);
    }
    browser_request q;memset(&q,0,sizeof(q));q.p=p;q.operation=operation;q.status=PSM_BAD_PLAN;
    if(operation==PS8_SCAN){
        browser_release();
        R->scan_memory=p->allocate(p->context,sizeof(psm_scan)+64);
        if(!R->scan_memory)return PSM_NO_MEMORY;
        R->scan=(void *)(((uintptr_t)R->scan_memory+63)&~(uintptr_t)63);q.scan=R->scan;
        memset(R->scan,0,sizeof(*R->scan));
        R->thumb_memory=p->allocate(p->context,2*BROWSER_THUMBS*PS8_THUMB_RGBA+64);
        R->thumb_pixels=R->thumb_memory?(void *)(((uintptr_t)R->thumb_memory+63)&~(uintptr_t)63):0;
        R->thumb_no_memory=R->thumb_memory?0:1;
    }else if(operation==PS8_THUMB){
        if(!R->thumb_pixels||!R->scan)return 0;
        q.scan=R->scan;q.page=load32(&R->thumb_requested);q.generation=load32(&R->thumb_generation);
        uint32_t published=load32(&R->thumb_bank);q.bank=published<2?1-published:0;
        while(load32(&R->thumb_readers[q.bank])){if(p->cancelled(p->context))return PSM_CANCELLED;FW_SLEEP(1);}
        q.jpeg=p->allocate(p->context,PS8_THUMB_JPEG_MAX+64+ps8_jpeg_workspace_bytes()+64);
        if(!q.jpeg){R->thumb_no_memory=1;return 0;}
        uint8_t *memory=q.jpeg;q.jpeg=(void *)(((uintptr_t)memory+63)&~(uintptr_t)63);
        q.scratch=q.jpeg+PS8_THUMB_JPEG_MAX;q.workspace=q.scratch+64;
        if(native_io_start(p->context,browser_io,&q))native_io_join(p->context);else browser_io(&q);
        p->release(p->context,memory);
        ps8_browser_prepared(operation,(uint32_t)q.status,q.page);return q.status;
    }else return PSM_BAD_PLAN;
    if(native_io_start(p->context,browser_io,&q))native_io_join(p->context);else browser_io(&q);
    ps8_browser_prepared(operation,(uint32_t)q.status,q.scan->ngroups);return q.status;
}
static int browser_post(uint32_t operation){
    if(load32(&R->state)==1)return 0;
    uint32_t serial=load32(&R->serial)+1;
    R->operation=operation;R->status=0;R->wait_polls=R->spawned=0;
    R->merged=R->targets=R->attempted=R->seconds=0;
    store32(&R->group_index,0);store32(&R->group_count,0);
    store32(&R->cancel,0);store32(&R->io_timeout,0);R->context.rows=R->context.total=0;store32(&R->context.phase,0);
    store32(&R->serial,serial);
    if(!worker_alive()&&spawn_worker())R->spawned=serial;
    if(!worker_alive()){R->status=PSM_NO_MEMORY;store32(&R->state,2);return 0;}
    store32(&R->state,1);psm_job_posted(serial,R->worker_id,R->spawned==serial);return 1;
}
static void browser_scan(void){
    if(R->browser.scan)R->focus_valid=!psb_identity_at(&R->browser,R->browser.cursor,&R->focus);
    uint32_t generation=R->browser.generation+1;
    psb_begin_scan(&R->browser,generation);store32(&R->thumb_generation,generation);store32(&R->thumb_requested,UINT32_MAX);
    browser_post(PS8_SCAN);
}
/* Draw RGBA through the stock image submission path. The source bank stays
   pinned until the original graphics fence returns. No display-register writes. */
__attribute__((noinline,used)) int ps8_thumbnail_draw(void *node){
    uint32_t bank=load32(&R->thumb_bank);
    if(bank>=2||!R->browser_open||R->browser.phase!=PSB_LIST)return 1;
    __atomic_fetch_add(&R->thumb_readers[bank],1,__ATOMIC_ACQ_REL);
    uint32_t page=load32(&R->thumb_requested);
    if(load32(&R->thumb_bank)!=bank||R->thumb_page[bank]!=page||R->thumb_gen[bank]!=R->browser.generation)goto finished;
    uint32_t row=*(uint32_t *)((uint8_t *)node+8);
    unsigned slot=row-page;
    if(slot>=BROWSER_THUMBS||!(R->thumb_valid[bank]&(1u<<slot)))goto finished;
    union {uint64_t wide[13];uint32_t words[26];int16_t shorts[52];} descriptor;
    uint32_t *d=descriptor.words;memset(&descriptor,0,sizeof(descriptor));
    d[0]=0;d[1]=0; /* scaled normal image, stock format 0 -> VG 0xc1 (RGBA bytes) */
    descriptor.wide[1]=(uintptr_t)(R->thumb_pixels+(bank*BROWSER_THUMBS+slot)*PS8_THUMB_RGBA);
    int16_t *src=descriptor.shorts+12,*dst=descriptor.shorts+16;
    src[0]=src[1]=0;src[2]=PS8_THUMB_W;src[3]=PS8_THUMB_H;
    const int16_t *rect=(const int16_t *)((const uint8_t *)node+0x10);
    for(unsigned i=0;i<4;++i)dst[i]=rect[i];
    d[21]=PS8_THUMB_W;d[22]=PS8_THUMB_H;
    uint32_t extent=FW_DRAW_SIZE();d[23]=(uint16_t)extent;d[24]=extent>>16;
    FW_CLEAN((void *)(uintptr_t)descriptor.wide[1],PS8_THUMB_RGBA);FW_DRAW_IMAGE(d);FW_DRAW_FINISH();
finished:
    __atomic_fetch_sub(&R->thumb_readers[bank],1,__ATOMIC_ACQ_REL);return 1;
}
/* A bounded native window owns one dynamic text slot per row. Rebinding a
   changed slot resets the stock glyph cache; reusing one slot while drawing
   leaves cached row labels stale when selection or page changes. */
static void browser_label(uint32_t row,char text[50]){
    psb_browser *b=&R->browser;char *end=text;
    if(b->phase==PSB_SCANNING){*copy(text,ui_label(UI_SCAN))=0;return;}
    if(b->phase==PSB_CONFIRM){
        if(!row){end=copy(text,ui_label(UI_CONFIRM));end=decimal(end,b->target_count);*copy(end,ui_label(UI_GROUPS))=0;}
        else *copy(text,ui_label(UI_CANCEL))=0;return;
    }
    if(b->phase!=PSB_LIST||!b->scan){*copy(text,ui_status(R->status))=0;return;}
    if(!row){end=copy(text,ui_label(UI_SELECT));end=decimal(end,b->selected_count);*copy(end,")")=0;return;}
    if(row==1){*copy(text,ui_label(UI_ALL))=0;return;}
    if(row==22){*copy(text,ui_label(UI_PREVIOUS))=0;return;}
    if(row==23){*copy(text,ui_label(UI_NEXT))=0;return;}
    row=R->window_first+row-2;if(row>=b->scan->ngroups){text[0]=0;return;}
    const psm_group *g=&b->scan->groups[b->scan->order[row]];char path[128];path[0]=0;
    unsigned found=0;for(unsigned i=0;i<g->count;++i){
        if(g->mask&(1u<<i)){++found;if(!path[0])psm_frame_path(b->scan,g,i,path);}
    }
    const char *name=path;
    if(path[0]){
        if(path[3]=='D'&&path[4]=='C'&&path[5]=='I'&&path[6]=='M'){
            name=path+8;while(*name&&*name!='\\'&&end<text+18)*end++=*name++;
            *end++='/';if(*name=='\\')++name;
        }else name=path+3;
    }
    while(*name&&*name!='.'&&end<text+24)*end++=*name++;
    if(ui_language()){*end=0;return;}
    *end++=' ';
    if(ui_language()&&g->status){*copy(end,ui_status(g->status))=0;return;}
    if(found!=g->count){end=decimal(end,found);*end++='/';}
    end=decimal(end,g->count);
    if(!ui_language()||found==g->count)end=copy(end,ui_label(UI_SHOTS));
    end=copy(end,g->duplicate?ui_label(UI_DUPLICATE):g->status?ui_status(g->status):
                  found!=g->count?ui_label(UI_MISSING):g->merged?ui_label(UI_MERGED):ui_label(UI_NEW));*end=0;
}
/* Static menu strings get their language metrics in 4032B648. The wide setter
   supplies a dynamic preset with 100% width and extra tracking instead. Use
   the same accessors as a static photo-menu label before caching the glyphs.
   Narrow filename slots keep the dedicated ASCII family and fit-to-row sizes. */
#define FW_MENU_SIZE ((uint8_t (*)(uint32_t,uint32_t))(uintptr_t)0x4032E2A0)
#define FW_MENU_SCALE ((void (*)(uint32_t,uint32_t,uint8_t *,uint8_t *))(uintptr_t)0x4032E364)
#define FW_MENU_TRACKING ((uint8_t (*)(uint32_t,uint32_t))(uintptr_t)0x4032E554)
static void browser_menu_metrics(uint32_t font,uint32_t language,int fit){
    uint8_t *style=(uint8_t *)(uintptr_t)(DYNAMIC_FONTS+16ull*font);
    uint8_t vertical;
    FW_MENU_SCALE(language,0x8ae,&style[2],&vertical);
    style[3]=FW_MENU_TRACKING(language,0x8ae);
    if(!fit)style[1]=FW_MENU_SIZE(language,0x8ae);
}
__attribute__((noinline)) static void browser_bind_text(void *node,uint32_t index,const char *text,int force){
    if(index>=BROWSER_TEXT_COUNT)return;uint32_t slot=BROWSER_TEXT_BASE+index;
    const uint8_t *entry=(const uint8_t *)(uintptr_t)(0xA032BD4A8ull+24ull*BROWSER_TEXT_BASE+24ull*index);
    const char *old=*(const char *const *)(entry+8);unsigned i=0;int changed;
    int path_row=R->browser.phase==PSB_LIST&&index>=2&&index<22;
    uint32_t language=FW_LANGUAGE();
    int wide=!path_row&&(language==1||language==8||language==9);
    if(wide){
        uint16_t wide[25];unsigned n=ps9_utf16(text,wide);
        changed=!n||*(const uint32_t *)entry!=n-1||!ui_equal(old,wide,n*2u);
    }else{
        while(i<49&&text[i]&&text[i]==old[i])++i;changed=text[i]!=old[i];
    }
    if(force||changed){
        static const uint16_t fonts[]={0x207,0x20a,0x20d,0x210,0x213}; /* stock 28,26,24,22,20 px */
        int group=path_row||index>=25;
        const int16_t *rect=(const int16_t *)((const uint8_t *)node+0xc0);
        for(unsigned k=0;k<(group?5u:1u);++k){
            uint32_t font=group?fonts[k]+(index>=25?1u:0u):0x21f;
            if(wide){
                ui_set_menu_text(text,slot,font);
                browser_menu_metrics(font,language,group);
            }else FW_SET_TEXT(text,slot,font);
            FW_BIND_TEXT(node,0,0);FW_BIND_TEXT(node,slot,wide?4:3);
            int16_t size[2]={0};if(!group||(FW_TEXT_SIZE(node,size)&&size[0]<=rect[2]-rect[0]))break;
        }
        FW_DIRTY(node,1);
    }
}
static void browser_status(uint32_t row,char text[50]){
    const psm_group *g=&R->scan->groups[R->scan->order[row]];
    char *end=text;unsigned found=0;
    for(unsigned i=0;i<g->count;++i)found+=(g->mask>>i)&1u;
    if(g->status){*copy(end,ui_status(g->status))=0;return;}
    if(found!=g->count){end=decimal(end,found);*end++='/';}
    end=decimal(end,g->count);end=copy(end,ui_label(UI_SHOTS));
    *copy(end,g->duplicate?ui_label(UI_DUPLICATE):found!=g->count?ui_label(UI_MISSING):
              g->merged?ui_label(UI_MERGED):ui_label(UI_NEW))=0;
}
__attribute__((noinline)) static void browser_status_leaf(void *page,unsigned i,void *parent){
    if(i<2||i>=22||!ui_language())return;
    unsigned slot=i-2;
    if(R->status_parent[slot]==parent)return;
    void *prototype=FW_CHILD(page,BROWSER_ROW_BASE+i,0x4ba7);
    if(!prototype)return;
    uint8_t *node=R->status_nodes[slot];
    /* Clone the original embedded image primitive (no owned glyph cache),
       then use the native reset operation before assigning our text. The
       row owns its child-list links; this fixed leaf memory is never freed. */
    memcpy(node,prototype,0x118);
    *(uint32_t *)node=0x4bab;
    FW_BIND_TEXT(node,0,0);
    FW_ATTACH_CHILD(parent,node);R->status_parent[slot]=parent;
}
__attribute__((noinline)) static void browser_status_release(void){
    FW_DRAW_FINISH();
    for(unsigned i=0;i<20;++i)if(R->status_parent[i]){
        FW_BIND_TEXT(R->status_nodes[i],0,0);R->status_parent[i]=0;
    }
}
__attribute__((noinline,used)) void ps8_browser_observe(uint32_t phase,uint32_t cursor,uint32_t selected,
                                                       uint32_t generation,uint32_t bank,uint32_t groups){
    __asm__ volatile("" : : "r"(phase),"r"(cursor),"r"(selected),"r"(generation),"r"(bank),"r"(groups) : "memory");
}
static uint32_t browser_first(void){
    int16_t rect[4]={0};FW_VIEW_RECT(FW_VIEW_ID(2),rect);
    /* Native 0x5c row is 56 pixels high with a 2-pixel gap; first two rows are actions. */
    int32_t row=rect[1]/58-2;if(row<0)row=0;
    return R->window_first+(uint32_t)row;
}
__attribute__((noinline,used)) void ps8_browser_widgets(void *row,void *counter,void *thumb,void *page,uint32_t count){
    __asm__ volatile("" : : "r"(row),"r"(counter),"r"(thumb),"r"(page),"r"(count) : "memory");
}
__attribute__((noinline)) static void browser_reset_view(uint32_t cursor){
    int16_t rect[4];uint32_t view=FW_VIEW_ID(2);FW_VIEW_RECT(view,rect);int32_t height=rect[3]-rect[1];
    int32_t y=(int32_t)(cursor+1)*58-height;if(y<0)y=0;rect[1]=(int16_t)y;rect[3]=(int16_t)(y+height);FW_VIEW_SET(view,rect);
}
int ps8_browser_refresh(void *page){
    if(!page||!R->browser_open)return 0;
    psb_browser *b=&R->browser;
    uint32_t count=b->phase==PSB_LIST&&b->scan?b->scan->ngroups+2:b->phase==PSB_CONFIRM?2:1;
    int rebuild=R->native_phase!=b->phase||R->native_count!=count;
    uint32_t visible=b->scan&&b->scan->ngroups>R->window_first?b->scan->ngroups-R->window_first:0;
    if(visible>BROWSER_GROUP_ROWS)visible=BROWSER_GROUP_ROWS;
    if(rebuild){
        uint32_t old=*(uint16_t *)((uint8_t *)page+0x58)+*(uint16_t *)((uint8_t *)page+0x32);
        if(old<BROWSER_ROWS)FW_ROW_FOCUS(page,old,0);
        for(unsigned i=0;i<BROWSER_ROWS;++i){
            void *n=FW_CONTAINER(BROWSER_ROW_BASE+i,(uint8_t *)page+0x18);if(!n)continue;
            browser_status_leaf(page,i,n);
            *(uintptr_t *)((uint8_t *)n+0x48)=(uintptr_t)FW_ROW_DRAW;
            int show=b->phase==PSB_LIST?(i<2||(i>=2&&i<2+visible)||(i==22&&R->window_first)||(i==23&&R->window_first+visible<b->scan->ngroups)):i<count;
            FW_ROW_DISABLE(page,i,!show);FW_DIRTY(n,show);
            void *thumb=FW_CHILD(page,BROWSER_ROW_BASE+i,0x4baa);
            if(thumb){*(uint32_t *)((uint8_t *)thumb+8)=R->window_first+i-2;*(uintptr_t *)((uint8_t *)thumb+0x48)=(uintptr_t)ps8_thumbnail_draw;FW_DYNAMIC(thumb,b->phase==PSB_LIST&&i>=2&&i<2+visible);}
            void *check=FW_CHILD(page,BROWSER_ROW_BASE+i,0x4ba7);
            if(check){FW_CONTENT_KIND(check,1,0x126d);FW_DYNAMIC(check,b->phase==PSB_LIST&&i>=2&&i<2+visible);}
            void *card=FW_CHILD(page,BROWSER_ROW_BASE+i,0x4ba8);
            if(card){
                uint32_t icon=0;
                if(b->phase==PSB_LIST&&i>=2&&i<2+visible)icon=b->scan->groups[b->scan->order[R->window_first+i-2]].card=='A'?0x15a0:0x159f;
                FW_CONTENT_KIND(card,1,icon);FW_DYNAMIC(card,icon!=0);
            }
            void *status=FW_CHILD(page,BROWSER_ROW_BASE+i,0x4bab);
            if(status)FW_DYNAMIC(status,ui_language()&&b->phase==PSB_LIST&&i>=2&&i<2+visible);
        }
        *(uint16_t *)((uint8_t *)page+0x30)=(uint16_t)FW_ROW_COUNT(page);
        *(uint16_t *)((uint8_t *)page+0x32)=0;*(uint16_t *)((uint8_t *)page+0x58)=0;
        FW_LIST_LAYOUT(page);
        uint32_t orientation=FW_ORIENTATION();if(orientation>1)orientation=0;
        const int16_t *viewport=(const int16_t *)(*(const uint8_t **)((uint8_t *)page+0x50)+0x22+orientation*8);
        int16_t width=viewport[2]-viewport[0];
        for(unsigned i=0;i<BROWSER_ROWS;++i){
            void *n=FW_CONTAINER(BROWSER_ROW_BASE+i,(uint8_t *)page+0x18);if(!n)continue;
            int16_t bounds[4];memcpy(bounds,(uint8_t *)n+0x10,8);bounds[2]=bounds[0]+width;FW_RECT(n,bounds);
            const int16_t *r=(const int16_t *)((uint8_t *)n+0x10);
            int group=b->phase==PSB_LIST&&i>=2&&i<2+visible;
            int16_t text_rect[4]={(int16_t)(r[0]+(group?96:6)),(int16_t)(r[1]+8),(int16_t)(r[0]+(group?(ui_language()?width-270:width-86):width-6)),(int16_t)(r[1]+48)};
            memcpy((uint8_t *)n+0xc0,text_rect,8);
            for(unsigned k=0;k<2;++k){void *child=FW_CHILD(page,BROWSER_ROW_BASE+i,0x4ba7+k);if(!child)continue;
                int16_t rect[4]={(int16_t)(r[0]+(k?48:6)),(int16_t)(r[1]+10),(int16_t)(r[0]+(k?88:42)),(int16_t)(r[1]+46)};
                FW_RECT(child,rect);memcpy((uint8_t *)child+0xc0,rect,8);
            }
            void *thumb=FW_CHILD(page,BROWSER_ROW_BASE+i,0x4baa);
            if(thumb){int16_t rect[4]={(int16_t)(r[0]+width-72),(int16_t)(r[1]+7),(int16_t)(r[0]+width-8),(int16_t)(r[1]+49)};
                FW_RECT(thumb,rect);memcpy((uint8_t *)thumb+0xc0,rect,8);}
            void *status=FW_CHILD(page,BROWSER_ROW_BASE+i,0x4bab);
            if(status){int16_t rect[4]={(int16_t)(r[0]+width-265),(int16_t)(r[1]+8),(int16_t)(r[0]+width-86),(int16_t)(r[1]+48)};
                FW_RECT(status,rect);memcpy((uint8_t *)status+0xc0,rect,8);}

        }
        FW_VIEW_LAYOUT(page);FW_SCROLLBAR(page);
        uint32_t cursor=b->phase==PSB_LIST&&R->restore_cursor?2+b->cursor-R->window_first:0;
        if(cursor>=2+visible)cursor=0;R->restore_cursor=0;
        *(uint16_t *)((uint8_t *)page+0x32)=(uint16_t)cursor;
        FW_ROW_FOCUS(page,cursor,1);R->native_cursor=cursor;
        browser_reset_view(cursor);FW_SCROLLBAR(page);R->native_phase=b->phase;R->native_count=count;
    }
    if(b->phase==PSB_LIST&&b->scan){
        for(unsigned i=0;i<visible;++i){uint32_t index=b->scan->order[R->window_first+i];
            void *check=FW_CHILD(page,BROWSER_ROW_BASE+i+2,0x4ba7);
            if(check)FW_SET_CONTENT(check,((b->selected[index/32]>>(index%32))&1u)?0x126c:0x126d);
        }
    }
    void *counter=FW_CONTAINER(0x1405,(uint8_t *)page+0x18);
    if(rebuild)ps8_browser_widgets(FW_CONTAINER(BROWSER_ROW_BASE,(uint8_t *)page+0x18),counter,FW_CHILD(page,BROWSER_ROW_BASE+2,0x4baa),page,*(uint16_t *)((uint8_t *)page+0x30));
    if(counter){char text[50];char *end=decimal(text,R->window_first/BROWSER_GROUP_ROWS+1);*end++='/';
        *decimal(end,b->scan&&b->scan->ngroups?(b->scan->ngroups+BROWSER_GROUP_ROWS-1)/BROWSER_GROUP_ROWS:1)=0;
        browser_bind_text(counter,24,text,rebuild);FW_DYNAMIC(counter,1);}
    ps8_browser_observe(b->phase,b->cursor,b->selected_count,b->generation,load32(&R->thumb_bank),b->scan?b->scan->ngroups:0);
    for(unsigned i=0;i<BROWSER_ROWS;++i){void *n=FW_CONTAINER(BROWSER_ROW_BASE+i,(uint8_t *)page+0x18);if(n&&*((uint8_t *)n+0x28)){char text[50];browser_label(i,text);browser_bind_text(n,i,text,rebuild);FW_DIRTY(n,1);}}
    if(ui_language()&&b->phase==PSB_LIST){
        for(unsigned i=0;i<visible;++i){void *n=FW_CHILD(page,BROWSER_ROW_BASE+i+2,0x4bab);if(!n)continue;
            char text[50];browser_status(R->window_first+i,text);browser_bind_text(n,25+i,text,rebuild);FW_DIRTY(n,1);}
    }
    FW_MARK((uint8_t *)page+0x18,0x403efe48u);FW_REDRAW(FW_REDRAW_PREDICATE,3,7);return 0;
}
static void browser_poll(void){
    if(!R->browser_open||!R->browser_page)return;
    uint32_t state=load32(&R->state);
    if(state==1&&load32(&R->claimed)!=load32(&R->serial)){
        if(++R->wait_polls==CLAIM_POLLS&&R->spawned!=load32(&R->serial)){
            if(spawn_worker())R->spawned=load32(&R->serial);else settle_unclaimed(PSM_NO_MEMORY);
        }else if(R->wait_polls>=GIVEUP_POLLS)settle_unclaimed(STATUS_BUSY);
    }
    if(state==2){
        if(R->operation==PS8_SCAN){
            if(R->status||psb_publish(&R->browser,R->browser.generation,R->scan))R->browser.phase=PSB_EMPTY;
            else{
                uint32_t row=0;R->restore_cursor=R->focus_valid&&!psb_find_identity(R->scan,&R->focus,&row);
                R->browser.cursor=row;R->window_first=row/BROWSER_GROUP_ROWS*BROWSER_GROUP_ROWS;
            }
        }
        store32(&R->state,0);
    }
    if(R->merge_pending&&R->browser.phase==PSB_CONFIRM&&load32(&R->state)!=1){
        R->merge_pending=0;
        if(!psb_start(&R->browser,R->browser.generation)){progress_layout(0);FW_TRANSITION(2,0xc5);return;}
    }
    if(R->browser.phase==PSB_LIST){
        uint32_t first=browser_first(),bank=load32(&R->thumb_bank);
        store32(&R->thumb_requested,first);store32(&R->thumb_generation,R->browser.generation);
        if(load32(&R->state)!=1&&!R->thumb_no_memory&&R->scan&&R->scan->ngroups&&
           (bank>=2||R->thumb_page[bank]!=first||R->thumb_gen[bank]!=R->browser.generation))browser_post(PS8_THUMB);
    }
    ps8_browser_refresh(R->browser_page);FW_TIMER_START(0x1a,100,browser_poll);
}
int ps8_browser_entry(void *page){
    if(!worker_alive()){
        /* Warm boot: the old heap and every task are gone. Do not dereference or free stale pointers. */
        R->scan_memory=R->thumb_memory=0;R->scan=0;R->thumb_pixels=0;R->browser_open=0;R->browser.scan=0;
        memset(R->status_parent,0,sizeof(R->status_parent));
        memset(R->status_nodes,0,sizeof(R->status_nodes));
        store32(&R->thumb_bank,UINT32_MAX);R->thumb_readers[0]=R->thumb_readers[1]=0;
    }
    if(!R->browser_open){
        browser_save_text(1);R->window_first=0;R->focus_valid=R->restore_cursor=0;R->menu_delay=FW_GET_SETTING(MENU_DELAY_SETTING);R->timer_kind=FW_TIMER_KIND();
        FW_TIMER_HOLD(UINT32_MAX);FW_SET_SETTING(MENU_DELAY_SETTING,8);store32(&R->browser_open,1);
    }
    R->browser_page=page;R->native_phase=UINT32_MAX;R->native_count=0;R->return_to_list=R->merge_pending=0;FW_SCREEN(3,7);
    if(load32(&R->state)!=1){store32(&R->state,0);browser_scan();}
    FW_TIMER_CANCEL(0x1a);browser_poll();return 0;
}
int ps8_browser_exit(void *page){
    (void)page;R->browser_page=0;FW_TIMER_CANCEL(0x1a);
    browser_status_release();
    if(R->browser.phase==PSB_RUNNING){
        /* Thumbnail worker is joined before confirmation can start. This GUI
           callback runs after the last pinned image submission has fenced. */
        if(!load32(&R->thumb_readers[0])&&!load32(&R->thumb_readers[1])){
            store32(&R->thumb_bank,UINT32_MAX);if(R->thumb_memory)FW_FREE(R->thumb_memory);
            R->thumb_memory=0;R->thumb_pixels=0;
        }
        return 0;
    }
    store32(&R->browser_open,0);store32(&R->cancel,1);settle_unclaimed(PSM_CANCELLED);
    if(load32(&R->state)!=1)browser_release();browser_save_text(0);
    FW_SET_SETTING(MENU_DELAY_SETTING,R->menu_delay);FW_TIMER_SET(R->timer_kind);return 0;
}
__attribute__((noinline)) static void browser_up(void *page,void *event){FW_ROW_UP(page,event);}
__attribute__((noinline)) static void browser_down(void *page,void *event){FW_ROW_DOWN(page,event);}
int ps8_browser_event(void *event,uint32_t code){
    psb_browser *b=&R->browser;void *page=R->browser_page;
    if(!page)return 0;
    if(code==0x27e||code==0x285||code==0x2a0){
        R->merge_pending=0;if(b->phase==PSB_CONFIRM){psb_back(b);R->restore_cursor=1;}else FW_TRANSITION(2,0x19);
    }else if(b->phase==PSB_LIST||b->phase==PSB_CONFIRM){
        if(code==0x283||code==0x29d)browser_up(page,event);
        else if(code==0x284||code==0x29e)browser_down(page,event);
        R->native_cursor=*(uint16_t *)((uint8_t *)page+0x58)+*(uint16_t *)((uint8_t *)page+0x32);
        if(b->phase==PSB_LIST){
            if(R->native_cursor>=2&&R->native_cursor<22)b->cursor=R->window_first+R->native_cursor-2;
            if(code==0x2ae||code==0x28b||code==0x29f||code==0x286){
                if(!R->native_cursor){if(!psb_confirm(b))store32(&R->thumb_requested,UINT32_MAX);}
                else if(R->native_cursor==1)psb_select_unmerged(b);
                else if(R->native_cursor>=22){
                    if(R->native_cursor==22&&R->window_first)R->window_first-=BROWSER_GROUP_ROWS;
                    else if(R->native_cursor==23&&R->window_first+BROWSER_GROUP_ROWS<b->scan->ngroups)R->window_first+=BROWSER_GROUP_ROWS;
                    b->cursor=R->window_first;R->native_phase=UINT32_MAX;store32(&R->thumb_requested,UINT32_MAX);
                }else psb_toggle(b,b->cursor);
            }
        }else if(code==0x2ae||code==0x28b||code==0x29f||code==0x286){
            if(R->native_cursor){psb_back(b);R->restore_cursor=1;}
            else if(load32(&R->state)==1){R->merge_pending=1;store32(&R->cancel,1);}
            else if(!psb_start(b,b->generation)){progress_layout(0);FW_TRANSITION(2,0xc5);return 0;}
        }
    }else if(b->phase==PSB_EMPTY&&(code==0x2ae||code==0x28b)&&load32(&R->state)!=1)browser_scan();
    if(R->browser_page){FW_TIMER_CANCEL(0x1a);browser_poll();}return 0;
}
