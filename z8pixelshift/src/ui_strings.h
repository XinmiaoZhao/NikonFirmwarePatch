/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef PS9_UI_STRINGS_H
#define PS9_UI_STRINGS_H
/* All Chinese characters are checked against the corresponding pinned stock
   language pool. English remains the fallback for the other menu languages. */
static const char *const ps9_status[3][19]={
 {"Done","Plan?","Group?","Shift?","Crop?","No mem","Rd err","Stop","NEF?","Use lossless","Wr err","Exists","No job","Mode?","Ready","Limit","No card","Busy","No new"},
 {"完成","设置错误","组错误","位移错误","裁切错误","内存不足","读取失败","已取消","格式错误","仅支持无损压缩","写入失败","文件已存在","无合成组","模式错误","可用","超过限制","无存储卡","请稍候","无未合成组"},
 {"完成","設定錯誤","組錯誤","位移錯誤","裁剪錯誤","記憶體不足","讀取失敗","已取消","格式錯誤","僅支援無損壓縮","寫入失敗","檔案已存在","無合成組","模式錯誤","可用","超過限制","無記憶卡","請稍候","無未合成組"}
};
enum ps9_label {
 UI_TITLE,UI_SCAN,UI_CONFIRM,UI_GROUPS,UI_CANCEL,UI_SELECT,UI_ALL,UI_PREVIOUS,UI_NEXT,
 UI_SHOTS,UI_DUPLICATE,UI_MISSING,UI_MERGED,UI_NEW,UI_WAIT,UI_STOPPING,UI_STOP,
 UI_SCAN_SHORT,UI_OPEN,UI_PREPARE,UI_STARTING,UI_SECONDS,UI_OK,UI_LABEL_COUNT
};
static const char *const ps9_labels[3][UI_LABEL_COUNT]={
 {"Pixel shift merge","Scanning cards...","Merge "," groups?","Cancel","Merge selected (","Select all unmerged","Previous groups","Next groups"," shots ","duplicate","missing","merged","new","I/O wait","Stopping","Stop ","Scan ","Open ","Prepare ","Starting","s"," - OK"},
 {"像素变化合成","正在扫描存储卡","确认合成 "," 组","取消","合成所选组 (","选择全部未合成","上一页","下一页","张","重复","不全","已合成","未合成","等待读写","正在取消","取消 ","扫描 ","打开 ","准备 ","正在开始","秒"," - 确定"},
 {"像素位移合成","正在掃描記憶卡","確認合成 "," 組","取消","合成所選組 (","選擇全部未合成","上一頁","下一頁","張","重複","不全","已合成","未合成","等候讀寫","正在取消","取消 ","掃描 ","開啟 ","準備 ","正在開始","秒"," - 確定"}
};
/* Convert the fixed UTF-8 UI vocabulary to the original 24-unit slot. A result
   of 0 means unsupported/malformed/truncated text; no partial glyph is drawn. */
static unsigned ps9_utf16(const char *text,uint16_t out[25]){
    unsigned n=0;const uint8_t *p=(const uint8_t *)text;
    while(*p){
        uint32_t x=*p++;unsigned extra=0;
        if(x>=0xe0&&x<=0xef){x&=15;extra=2;}
        else if(x>=0xc2&&x<=0xdf){x&=31;extra=1;}
        else if(x>=128)return 0;
        for(unsigned i=0;i<extra;++i){if((*p&0xc0)!=0x80)return 0;x=(x<<6)|(*p++&63);}
        if((extra==2&&x<0x800)||(x>=0xd800&&x<=0xdfff)||n==24)return 0;
        out[n++]=(uint16_t)x;
    }
    out[n]=0;return n+1;
}
#endif
