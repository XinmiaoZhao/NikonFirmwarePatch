#!/usr/bin/env python3
"""Recompute the 2026-11-05 measured comparisons and render four bilingual figures.

Only public numerical samples are read. No firmware, original media, fitting,
camera access or network calls. Requires NumPy, Matplotlib and Pillow.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT/'docs/data'
E = np.array([[109,366,37],[-59,-197,256],[256,-233,-23]], float)/512
PRIM = {'slog3': [[.766,.275],[.225,.800],[.089,-.087]],
        'log3g10': [[.780308,.304253],[.121595,1.493994],[.095612,-.084589]]}


def npm(prim):
    p = np.asarray(prim)
    m = np.array([p[:,0]/p[:,1], np.ones(3), (1-p.sum(1))/p[:,1]])
    return m*np.linalg.solve(m, np.array([.3127/.329,1,(1-.3127-.329)/.329]))


def linear(ycc, mode):
    c = (np.asarray(ycc)-[0,512,512])@np.linalg.inv(E).T
    if mode == 'log3g10':
        return (10**(c/1023/.224282)-1)/155.975327-.01
    return np.where(c>=171.2102946929, .19*10**((c-420)/261.5)-.01,
                    (c-95)*.01125/(171.2102946929-95))


def errors(p,t,keys,greys,mode,minimum=None):
    gi = [keys.index(k) for k in greys]
    use = np.ones(len(p),bool) if minimum is None else (p>=minimum).all(1)&(t>=minimum).all(1)
    assert use[gi].all()
    scale = np.exp(np.log(t[gi]/p[gi]).mean(0)); n = p*scale
    d = np.log2(n[use]/t[use]); c = d[:,[0,2]]-d[:,[1]]
    b = np.log2((n[use]@npm(PRIM[mode])[1])/(t[use]@npm(PRIM[mode])[1]))
    stats = dict(colour_rms=float(np.sqrt((c*c).mean())), brightness_rms=float(np.sqrt((b*b).mean())),
                 colour_worst=float(np.abs(c).max()), chips_scored=int(use.sum()),
                 excluded=[k for k,u in zip(keys,use) if not u],
                 worst_patch=np.array(keys)[use][np.abs(c).max(1).argmax()])
    return stats,dict(normalized=n,target=t,colour=c,brightness=b,use=use,scale=scale)


def calculate(data):
    summary, detail = {}, {}
    for mode,m in data['modes'].items():
        summary[mode], detail[mode] = {}, {}
        keys=m['patches'];greys=data['grey_patches']
        rest=[i for i,k in enumerate(keys) if k not in data['code_metric_excluded_patches']]
        for group,g in m['groups'].items():
            summary[mode][group], detail[mode][group] = {}, {}
            for arm,clips in g['clips'].items():
                code=np.mean([x['ycbcr'] for x in clips],0)
                p=np.mean([linear(x['ycbcr'],mode) for x in clips],0) if mode=='log3g10' else linear(code,mode)
                hp=np.mean([linear(x['holdout_ycbcr'],mode) for x in clips],0) if mode=='log3g10' else linear(np.mean([x['holdout_ycbcr'] for x in clips],0),mode)
                refs={'mean':{k:np.mean([r[k] for r in g['references'].values()],0) for k in ['preF','holdout_linear']}} if mode=='log3g10' else g['references']
                rows,ds={},{}
                for ref,r in refs.items():
                    t=np.array(r['preF' if mode=='log3g10' else 'cine'])
                    s,d=errors(p,t,keys,greys,mode,None if mode=='log3g10' else data['ratio_metric_min_linear'])
                    expected=g['expected'][arm] if mode=='log3g10' else g['expected'][arm][ref]
                    tol=.000501 if mode=='log3g10' else .000051
                    for k in ['colour_rms','brightness_rms','colour_worst']:assert abs(s[k]-expected[k])<tol,(mode,group,arm,ref,k,s[k],expected[k])
                    ht=np.array(r['holdout_linear']);hn=hp*d['scale'];hd=np.log2(hn/ht)
                    hc=hd[:,[0,2]]-hd[:,[1]];hb=np.log2((hn@npm(PRIM[mode])[1])/(ht@npm(PRIM[mode])[1]))
                    s['holdout']={k:dict(colour=hc[i].tolist(),brightness=float(hb[i])) for i,k in enumerate(m['holdout_patches'])}
                    for k,v in s['holdout'].items():
                        assert np.max(np.abs(np.array(v['colour'])-expected['holdout'][k]['colour']))<.000051
                        assert abs(v['brightness']-expected['holdout'][k]['brightness'])<.000051
                    if mode=='slog3':
                        ce=code-np.array(r['M']);cp=code-np.array(r['P'])
                        s['code_rms_45']=float(np.sqrt((ce[rest]**2).mean()));s['code_max_45']=np.abs(ce[rest]).max(0).tolist()
                        assert abs(s['code_rms_45']-expected['code_rms_45'])<.000051
                        assert np.max(np.abs(np.array(s['code_max_45'])-expected['code_max_45']))<.0051
                        assert s['chips_scored']==expected['chips_scored']
                        s['main_code_errors']={k:dict(M=ce[keys.index(k)].tolist(),P=cp[keys.index(k)].tolist()) for k in data['code_metric_excluded_patches']}
                        st,dt=errors(p,linear(r['P'],mode),keys,greys,mode,data['ratio_metric_min_linear'])
                        # The original post-hoc calculation also retains the M-type valid mask.
                        mask=d['use'] & dt['use']
                        if not np.array_equal(mask,dt['use']):raise AssertionError('P comparison requires joint validity mask')
                        for k in ['colour_rms','brightness_rms','colour_worst']:assert abs(st[k]-expected['post_hoc_P'][k])<.000051
                        s['post_hoc_P']={k:st[k] for k in ['colour_rms','brightness_rms','colour_worst','chips_scored']}
                    rows[ref]=s;ds[ref]=d
                summary[mode][group][arm]=rows;detail[mode][group][arm]=ds
    return summary,detail


def render(data,summary,detail,language,font,destination):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from PIL import Image
    if language=='zh':
        from matplotlib import font_manager
        if font:
            font_manager.fontManager.addfont(str(font)); family=font_manager.FontProperties(fname=str(font)).get_name()
        else:
            family=font_manager.FontProperties(family=['Noto Sans CJK SC','Hiragino Sans GB','PingFang SC'])
            family=font_manager.FontProperties(fname=font_manager.findfont(family,fallback_to_default=False)).get_name()
    else:family='DejaVu Sans'
    plt.rcParams.update({'font.family':family,'font.size':10,'axes.titlesize':12,'figure.facecolor':'white',
                         'axes.spines.top':False,'axes.spines.right':False,'text.color':'#243447',
                         'axes.labelcolor':'#243447','xtick.color':'#45566c','ytick.color':'#45566c','axes.unicode_minus':False})
    tr=lambda en,zh:zh if language=='zh' else en
    blue,orange,gray='#1768AC','#CE6A28','#617286'
    labels={'revised':tr('Revised M1 + constant Cpxs','新版 M1＋常量 Cpxs'), 'previous':tr('Previous M1 + hue table','旧版 M1＋色相表')}
    names={'log3g10':'Log3G10 / RWG','slog3':'S-Log3 / S-Gamut3.Cine'}
    group_label=lambda g:tr(('Cool' if g[0]=='K' else 'Warm')+'\n1/'+g[1:]+' s',('冷光' if g[0]=='K' else '暖光')+'\n1/'+g[1:]+' 秒')
    destination.mkdir(parents=True,exist_ok=True)
    def save(fig,name):
        suffix='-zh' if language=='zh' else ''
        buf=io.BytesIO();fig.savefig(buf,format='png',dpi=160,facecolor='white');buf.seek(0)
        with Image.open(buf) as im:im.convert('RGB').save(destination/(name+suffix+'.png'),optimize=True)
        plt.close(fig)
    def header(fig,title,subtitle,left=.08):
        fig.suptitle(title,x=left,y=.98,ha='left',fontsize=18,fontweight='bold')
        fig.text(left,.922,subtitle,color=gray,fontsize=10)
    # 1: measured condition comparisons. Front/back reference endpoints are not a CI.
    fig,axs=plt.subplots(2,2,figsize=(12.4,8.6));fig.subplots_adjust(left=.08,right=.97,top=.84,bottom=.16,hspace=.50,wspace=.27)
    for row,mode in enumerate(['log3g10','slog3']):
        groups=['K250','K500','W250'];x=np.arange(3)
        for col,key in enumerate(['colour_rms','brightness_rms']):
            ax=axs[row,col]
            for arm,color,offset in [('previous',orange,-.13),('revised',blue,.13)]:
                vals=[list(summary[mode][g][arm].values()) for g in groups]
                lo=np.array([min(s[key] for s in a) for a in vals]);hi=np.array([max(s[key] for s in a) for a in vals]);mid=(lo+hi)/2
                ax.bar(x+offset,mid,.25,color=color,alpha=.86,label=labels[arm])
                ax.errorbar(x+offset,mid,yerr=[mid-lo,hi-mid],fmt='none',ecolor='#243447',capsize=4,lw=1.2)
                for xx,v,a,b in zip(x+offset,mid,lo,hi):ax.text(xx,b+max(hi.max()*.025,.0006),f'{v:.3f}',ha='center',fontsize=9)
            ax.set_xticks(x,[group_label(g) for g in groups]);ax.set_ylabel(tr('RMS error (stops)','RMS 误差（档）'));ax.set_ylim(bottom=0)
            ax.set_ylim(top=ax.get_ylim()[1]*1.17);ax.grid(axis='y',alpha=.18);ax.set_axisbelow(True)
            ax.set_title(names[mode]+' · '+tr('Colour ratio' if col==0 else 'Luminance','色彩比例' if col==0 else '亮度'),loc='left',pad=10)
    handles,labs=axs[0,0].get_legend_handles_labels();fig.legend(handles,labs,loc='lower left',bbox_to_anchor=(.07,.070),ncol=2,frameon=False)
    header(fig,tr('New camera recordings: previous and revised colour tables','新一轮实拍：旧表与新版色彩数据'),tr('Three shared capture conditions per mode; two clips per arm','每种 Log 展示三个拍摄条件，每臂两段录像'))
    fig.text(.08,.026,tr('Three-neutral alignment. S-Log3 bars show front/back-reference midpoints; whiskers span those two results, not confidence intervals.\nEach mode uses its own linear colour coordinates. The separate W500 S-Log3 capture is shown in the code-error figure.',
                       '采用三块中性片对齐。S-Log3 柱高为前后参照结果的中点，细线连接两次结果，不是置信区间。\n两种 Log 使用各自的线性色彩坐标；S-Log3 加拍的暖光 1/500 秒另见码值图。'),fontsize=9,color=gray)
    save(fig,'log-measured-conditions')
    # 2: S-Log3 code statistics and the near-black averaging distinction.
    fig,axs=plt.subplots(1,2,figsize=(12.8,6.4));fig.subplots_adjust(left=.07,right=.98,top=.79,bottom=.25,wspace=.28)
    groups=['K250','K500','W250','W500'];x=np.arange(4)
    for arm,color,offset in [('previous',orange,-.12),('revised',blue,.12)]:
        vals=[summary['slog3'][g][arm] for g in groups];lo=np.array([min(r['code_rms_45'] for r in v.values()) for v in vals]);hi=np.array([max(r['code_rms_45'] for r in v.values()) for v in vals]);mid=(lo+hi)/2
        axs[0].errorbar(x+offset,mid,yerr=[mid-lo,hi-mid],fmt='o',ms=6,capsize=5,color=color,label=labels[arm])
    axs[0].set(xticks=x,xticklabels=[group_label(g)+(' *' if g=='W500' else '') for g in groups],ylim=(0,1.7),ylabel=tr('YCbCr RMS (10-bit codes)','YCbCr RMS（10-bit 码值）'))
    axs[0].set_title(tr('45 patches; front/back references','45 块色片；前后两份参照'),loc='left');axs[0].legend(fontsize=8,frameon=False,loc='upper right');axs[0].grid(axis='y',alpha=.2)
    patches=data['code_metric_excluded_patches'];r=summary['slog3']['K250']['revised'];x=np.arange(3)
    for typ,color,offset in [('M',orange,-.12),('P',blue,.12)]:
        vals=np.array([[r[ref]['main_code_errors'][k][typ][2] for k in patches] for ref in ['pre','post']]);lo=vals.min(0);hi=vals.max(0);mid=(lo+hi)/2
        axs[1].errorbar(x+offset,mid,yerr=[mid-lo,hi-mid],fmt='s',ms=6,capsize=5,color=color,label=tr('Mean then encode (M)' if typ=='M' else 'Encode then mean (P)','先平均后编码（M）' if typ=='M' else '先编码后平均（P）'))
    axs[1].axhline(0,lw=.8,color=gray);axs[1].set(xticks=x,xticklabels=patches,ylabel=tr('Revised minus reference Cr (codes)','新版减参照 Cr（码值）'),ylim=(-7,12))
    axs[1].set_title(tr('Cool 1/250 s: three blue patches','冷光 1/250 秒：三块蓝片'),loc='left');axs[1].legend(fontsize=8,frameon=False,loc='upper right');axs[1].grid(axis='y',alpha=.2)
    header(fig,tr('S-Log3: file-code errors and near-black averaging','S-Log3：文件码值误差与近黑平均方式'),tr('The three blue patches at right are excluded only from the left 45-patch statistic','右图三块蓝片单列，不计入左图的 45 片统计'),.07)
    fig.text(.07,.06,tr('Dots and whiskers summarize the two reference timings, not repeat-capture uncertainty. * W500 was an additional capture.\nP is a post-capture diagnostic using per-block encoding before averaging; it does not replace the main M-type reference.\nA large ratio error can coexist with a small code difference near black; no per-patch correction was fitted.',
                      '点及细线表示前后两份参照的结果，不代表重复拍摄的不确定度。* W500 为加拍条件。\nP 是拍后增加的诊断：先逐块编码、再平均，不能替代主体的 M 型参照。\n近黑处较大的比例误差可以伴随较小的码值差；这里没有逐色片拟合。'),fontsize=9,color=gray)
    save(fig,'log-slog3-revised-codes')
    # 3: unamplified chromaticity vectors, all 48 patches (including ratio-excluded patches).
    fig,axs=plt.subplots(2,2,figsize=(11.0,11.7));fig.subplots_adjust(left=.09,right=.98,top=.86,bottom=.13,hspace=.23,wspace=.12)
    cie=np.array(json.loads((DATA/'cie-1931.json').read_text())['values'])[:,1:];loc=cie[:,:2]/cie.sum(1)[:,None];loc=np.vstack([loc,loc[0]])
    for row,mode in enumerate(['log3g10','slog3']):
        for col,arm in enumerate(['previous','revised']):
            ax=axs[row,col];ds=list(detail[mode]['K250'][arm].values());p=np.mean([d['normalized'] for d in ds],0)@npm(PRIM[mode]).T;t=np.mean([d['target'] for d in ds],0)@npm(PRIM[mode]).T
            p=p[:,:2]/p.sum(1)[:,None];t=t[:,:2]/t.sum(1)[:,None];color=orange if arm=='previous' else blue
            ax.plot(loc[:,0],loc[:,1],color='#bdc8d2',lw=1);ax.quiver(t[:,0],t[:,1],p[:,0]-t[:,0],p[:,1]-t[:,1],angles='xy',scale_units='xy',scale=1,width=.003,color=color,alpha=.75)
            ax.scatter(t[:,0],t[:,1],s=28,facecolors='white',edgecolors='#334155',lw=.7,label=tr('N-RAW reference','N-RAW 参照'));ax.scatter(p[:,0],p[:,1],s=20,marker='x',color=color,label=tr('Recorded video','实拍录像'))
            ax.set(xlim=(.05,.72),ylim=(.02,.78),xlabel='CIE 1931 x',ylabel='CIE 1931 y');ax.set_aspect('equal');ax.grid(alpha=.15)
            ax.set_title(names[mode]+'\n'+labels[arm],pad=9,fontsize=11);ax.legend(fontsize=8,loc='upper right',frameon=False)
    header(fig,tr('Measured chromaticity: cool light, 1/250 s','实拍色度：冷光，1/250 秒'),tr('48 patches per panel; identical axes; arrows are not magnified','每图 48 块色片，坐标范围相同，连接线偏差未放大'),.09)
    fig.text(.09,.028,tr('Video is aligned using the three neutral patches. S-Log3 shows the average of both reference comparisons.\nThe ratio-error exclusion does not remove patches from this chromaticity view. Chromaticity omits luminance error.\nCIE spectral locus: CIE 2019, CC BY-SA 4.0. Both camera datasets were recorded separately.',
                       '录像用三块中性片对齐；S-Log3 展示两次参照比较的平均坐标。\n比例误差统计排除的色片仍保留在色度图中；色度坐标不展示亮度误差。\n光谱轨迹：CIE 2019，CC BY-SA 4.0。两种 Log 来自分别拍摄的数据集。'),fontsize=9,color=gray)
    save(fig,'log-measured-chromaticity')
    # 4: full residual distribution, no acceptance or perceptual cut-off lines.
    fig,axs=plt.subplots(1,2,figsize=(12.4,6.4));fig.subplots_adjust(left=.08,right=.97,top=.80,bottom=.23,wspace=.25)
    for ax,mode in zip(axs,['log3g10','slog3']):
        for arm,color in [('previous',orange),('revised',blue)]:
            values=[]
            for g in ['K250','K500','W250']:
                # S-Log3 distribution uses the pre reference, with post sensitivity in text/table.
                d=detail[mode][g][arm]['mean' if mode=='log3g10' else 'pre']
                values.extend(np.abs(d['colour']).max(1))
            v=np.sort(values);assert min(v)>0
            ax.step(v,np.arange(1,len(v)+1)/len(v)*100,where='post',color=color,lw=2,label=labels[arm]+f' (n={len(v)})')
            ax.plot(v[-1],100,'o',color=color,ms=4);ax.annotate(f'{v[-1]:.3f}',(v[-1],100),xytext=(-4,-36 if mode=='slog3' and arm=='revised' else -20),textcoords='offset points',ha='right',color=color,fontsize=9)
        ax.set_xscale('log');ax.set(xlim=(.0008,2),ylim=(0,105),ylabel=tr('Cumulative patch-condition fraction (%)','累计色片条件比例（%）'),xlabel=tr('Max |R/G, B/G error| (stops; log axis)','max |R/G、B/G 误差|（档；对数轴）'))
        ax.set_xticks([.001,.01,.1,1],['0.001','0.01','0.1','1']);ax.set_title(names[mode],loc='left');ax.grid(alpha=.2);ax.legend(frameon=False,loc='lower right',fontsize=8)
    header(fig,tr('The full distribution retains the largest residuals','保留最大残差的逐片误差分布'),tr('Cool 1/250 + cool 1/500 + warm 1/250; each patch-condition is one observation','冷光 1/250＋冷光 1/500＋暖光 1/250；每个色片条件计一个观察值'))
    fig.text(.08,.055,tr('Each observation is the larger absolute log2(R/G) or log2(B/G) error after neutral alignment. These are not independent replicates.\nS-Log3 uses the pre reference and its positive-channel selection; K250 r5c2 is 0.208 stops (post reference: 0.1925).\nDifferent target colour coordinates and sample selections preclude ranking the two encoding spaces by these numbers.',
                       '每个观察值取中性片对齐后 log2(R/G)、log2(B/G) 误差绝对值的较大者；各观察值不是独立重复实验。\nS-Log3 使用前参照及正通道样本规则；K250 的 r5c2 为 0.208 档（后参照 0.1925 档）。\n目标色彩坐标与样本范围不同，不能据此为两种编码色域排名。'),fontsize=9,color=gray)
    save(fig,'log-measured-distribution')


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--check',action='store_true');ap.add_argument('--language',choices=['en','zh','both'],default='both');ap.add_argument('--chinese-font',type=Path);a=ap.parse_args()
    source=DATA/'log-colour-measured-20261105.json';data=json.loads(source.read_text());summary,detail=calculate(data)
    result=dict(data_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),modes=summary)
    path=DATA/'log-colour-measured-summary.json'
    if a.check:
        assert json.loads(path.read_text())==result;print('Measured data independently recomputed and match saved summary');return
    path.write_text(json.dumps(result,indent=2)+'\n')
    for language in (['en','zh'] if a.language=='both' else [a.language]):render(data,summary,detail,language,a.chinese_font,ROOT/'docs/images')
    print('Generated four measured figure pairs; original rounded statistics reproduced')


if __name__=='__main__':main()
