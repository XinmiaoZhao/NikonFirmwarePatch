#!/usr/bin/env python3
"""Recompute the published colour report from numerical samples; render static figures.

Requires NumPy, Matplotlib and Pillow; no camera, firmware input or network.
The sample file distinguishes measured output from forward-model predictions.
CIE locus data and figures using it: CC BY-SA 4.0, see docs/data/README.md.
"""
import argparse,hashlib,io,json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'docs/data'
# N-Log primaries: Nikon N-Log Specification v1.0.0, section 3 (BT.2020 / D65).
PRIMARIES={'BT.2020 (N-Log)':[[.708,.292],[.170,.797],[.131,.046]],
           'S-Gamut3.Cine':[[.766,.275],[.225,.800],[.089,-.087]],
           'REDWideGamutRGB':[[.780308,.304253],[.121595,1.493994],[.095612,-.084589]]}
D65=np.array([.3127,.3290])
def npm(p):
    xy=np.array(p);basis=np.vstack([xy[:,0]/xy[:,1],np.ones(3),(1-xy.sum(1))/xy[:,1]])
    white=np.array([D65[0]/D65[1],1,(1-D65.sum())/D65[1]])
    return basis*np.linalg.solve(basis,white)
CINE=npm(PRIMARIES['S-Gamut3.Cine']);RWG=npm(PRIMARIES['REDWideGamutRGB'])
WHITE=CINE@np.ones(3)

def adobe_reference_xy():
    """Virtual basis coordinates of one published XYZ -> camera calibration matrix.
    This reference has no assigned 4000 K condition and is not an encoding gamut.
    """
    d=json.loads((DATA/'adobe-z8-matrix.json').read_text())
    camera_to_xyz=np.linalg.inv(np.array(d['xyz_to_camera_integer'],float)/d['divisor'])
    return (camera_to_xyz[:2]/camera_to_xyz.sum(axis=0)).T
def slog_decode(c):
    c=np.asarray(c,float)
    return np.where(c>=171.2102946929,10**((c-420)/261.5)*.19-.01,(c-95)*.01125/(171.2102946929-95))
def red_encode(v):
    return 1023*.224282*np.log10((np.maximum(v,-.009)+.01)*155.975327+1)
def red_decode(c):return (10**(c/1023/.224282)-1)/155.975327-.01
def xy(xyz):return xyz[:,:2]/xyz.sum(axis=1)[:,None]
def uv(xyz):
    den=xyz@np.array([1,15,3]);return np.c_[4*xyz[:,0]/den,9*xyz[:,1]/den]
def lab(xyz,yw):
    ratio=xyz/(WHITE*yw);delta=6/29
    f=np.where(ratio>delta**3,np.cbrt(ratio),ratio/(3*delta**2)+4/29)
    return np.c_[116*f[:,1]-16,500*(f[:,0]-f[:,1]),200*(f[:,1]-f[:,2])]

def de2000(l1, l2):
    L1, a1, b1 = l1.T
    L2, a2, b2 = l2.T
    C1, C2 = np.hypot(a1, b1), np.hypot(a2, b2)
    Cm = (C1 + C2) / 2
    G = 0.5 * (1 - np.sqrt(Cm ** 7 / (Cm ** 7 + 25.0 ** 7)))
    a1p, a2p = a1 * (1 + G), a2 * (1 + G)
    C1p, C2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p, h2p = np.degrees(np.arctan2(b1, a1p)) % 360, np.degrees(np.arctan2(b2, a2p)) % 360
    dLp, dCp = L2 - L1, C2p - C1p
    dh = h2p - h1p
    dh = np.where(C1p * C2p == 0, 0, np.where(dh > 180, dh - 360, np.where(dh < -180, dh + 360, dh)))
    dHp = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dh / 2))
    Lpm, Cpm = (L1 + L2) / 2, (C1p + C2p) / 2
    hs = h1p + h2p
    hpm = np.where(C1p * C2p == 0, hs, np.where(np.abs(h1p - h2p) <= 180, hs / 2, np.where(hs < 360, (hs + 360) / 2, (hs - 360) / 2)))
    T = 1 - 0.17 * np.cos(np.radians(hpm - 30)) + 0.24 * np.cos(np.radians(2 * hpm)) + 0.32 * np.cos(np.radians(3 * hpm + 6)) - 0.20 * np.cos(np.radians(4 * hpm - 63))
    SL = 1 + 0.015 * (Lpm - 50) ** 2 / np.sqrt(20 + (Lpm - 50) ** 2)
    SC, SH = 1 + 0.045 * Cpm, 1 + 0.015 * Cpm * T
    RT = -2 * np.sqrt(Cpm ** 7 / (Cpm ** 7 + 25.0 ** 7)) * np.sin(np.radians(60 * np.exp(-((hpm - 275) / 25) ** 2)))
    return np.sqrt((dLp / SL) ** 2 + (dCp / SC) ** 2 + (dHp / SH) ** 2 + RT * (dCp / SC) * (dHp / SH))

def grey_match(p,t,indices):
    return p*np.exp(np.log(t[indices]).mean(0)-np.log(np.maximum(p[indices],1e-9)).mean(0))
def forward_rwg(inputs,d):
    linear=inputs@(np.array(d['matrix'],float)/d['matrix_divisor']).T
    rgb=red_encode(linear);D=np.array(d['domain_to_rgb'],float)/d['domain_divisor']
    z=rgb@np.linalg.inv(D).T
    angle=np.mod(np.arctan2(z[:,2],z[:,1]),2*np.pi)
    quadrant=np.floor(angle/(np.pi/2));fraction=angle-quadrant*np.pi/2
    psi=(quadrant+np.sin(fraction)/(np.cos(fraction)+np.sin(fraction)))*90
    position=((psi-d['hue_origin_degrees'])/11.25)%32
    left=np.floor(position).astype(int);weight=(position-left)[:,None]
    table=np.array(d['table_by_ring_position'],float)/d['table_divisor']
    p=table[left]*(1-weight)+table[(left+1)%32]*weight
    y,u,v=z.T
    transformed=np.c_[y+p[:,4]*u+p[:,5]*v,p[:,0]*u+p[:,1]*v,p[:,2]*u+p[:,3]*v]
    return red_decode(transformed@D.T)
def stop_errors(p,t):
    ratio=lambda v:np.log2(np.c_[v[:,0]/v[:,1],v[:,2]/v[:,1]])
    return ratio(p)-ratio(t),np.log2((p@RWG[1])/(t@RWG[1]))
def summary_de(v):
    return dict(median=float(np.median(v)),p95=float(np.quantile(v,.95)),max=float(v.max()),below_1=int((v<1).sum()),below_2=int((v<2).sum()))
def calculate(data):
    d=data['slog3'];rows=d['samples'];M=np.array(d['matrix'],float)/d['matrix_divisor']
    xyz={}
    for key in ['reference_ycbcr','matrix_curve_only','hue_corrected']:
        codes=np.array([r[key] for r in rows]);rgb=(codes-[0,512,512])@np.linalg.inv(M).T
        xyz[key]=slog_decode(rgb)@CINE.T
    yw=xyz['reference_ycbcr'][[r['patch'] for r in rows].index(d['white_patch']),1]
    ref=lab(xyz['reference_ycbcr'],yw)
    errors={key:de2000(ref,lab(xyz[key],yw)) for key in ['matrix_curve_only','hue_corrected']}
    slog_summary={key:summary_de(v) for key,v in errors.items()}
    for key in errors:
        for metric,value in d['expected_summary'][key].items():assert abs(slog_summary[key][metric]-value)<.0051,(key,metric)
    d=data['log3g10'];conditions=list(dict.fromkeys(r['condition'] for r in d['samples']));rwg={}
    for condition in conditions:
        rows=[r for r in d['samples'] if r['condition']==condition]
        p=forward_rwg(np.array([r['model_input_linear'] for r in rows]),d)
        t=np.array([r['reference_linear_rwg'] for r in rows]);ids=[r['patch'] for r in rows]
        p=grey_match(p,t,[ids.index(k) for k in d['grey_patches']]);c,b=stop_errors(p,t)
        rwg[condition]=dict(predicted=p,reference=t,colour_errors=c,brightness_errors=b,patches=ids)
    c=np.concatenate([r['colour_errors'] for r in rwg.values()]);b=np.concatenate([r['brightness_errors'] for r in rwg.values()])
    duv=np.concatenate([np.linalg.norm(uv(r['predicted']@RWG.T)-uv(r['reference']@RWG.T),axis=1) for r in rwg.values()])*1000
    model_summary=dict(colour_rms=float(np.sqrt(np.mean(c*c))),brightness_rms=float(np.sqrt(np.mean(b*b))),colour_worst=float(np.abs(c).max()),brightness_worst=float(np.abs(b).max()),duv_median=float(np.median(duv)),duv_max=float(duv.max()))
    for key in ['colour_rms','brightness_rms','colour_worst','brightness_worst']:assert abs(model_summary[key]-d['expected_fixed'][key])<.00051,(key,model_summary[key])
    # Published matrices agree with source primaries; neutral white remains D65.
    assert np.max(np.abs(RWG@np.ones(3)-WHITE))<1e-12
    return xyz,errors,rwg,dict(slog3=slog_summary,log3g10_fixed_integer_model=model_summary,log3g10_cross_validation=d['cross_validation_quantized'],samples=dict(slog3=48,log3g10=288))

ZH = {'Recording colour spaces': '录像编码色彩空间对照', 'Encoding primaries and D65 white point': '原色坐标与 D65 白点', 'Spectral locus': '可见光谱轨迹', 'Triangles describe encoding coordinates, not measured sensor coverage.\nLocus: CIE 2019 (CC BY-SA 4.0).\nPrimaries: Nikon, Sony and RED technical documents.': '三角形表示编码坐标范围，不代表实测传感器色域覆盖。\n光谱轨迹：CIE 2019（CC BY-SA 4.0）。\n原色定义：Nikon、Sony 与 RED 技术资料。', 'N-RAW reference': 'N-RAW 参照', 'Recorded video': '实拍录像', 'Model prediction': '模型预测', 'Matrix and curve only': '仅使用矩阵与曲线', 'Current hue-corrected implementation': '加入当前色相修正', 'S-Log3 / S-Gamut3.Cine: measured chromaticity': 'S-Log3 / S-Gamut3.Cine：实拍色度偏差', '48 pigment patches | ISO 4000, 4000 K, 1/250 s | default clamp': '48 块颜料色片｜ISO 4000、4000 K、1/250 秒｜默认截断', 'Open circles: same-scene N-RAW reference. Crosses: recorded video. Arrows are not magnified.\nThe two panels share the same axes. CIE locus: CIE 2019, CC BY-SA 4.0.': '空心圆：同场 N-RAW 参照；叉号：实拍录像。连接线的偏差未放大。\n两图坐标范围相同。光谱轨迹：CIE 2019，CC BY-SA 4.0。', 'Matrix + curve': '矩阵与曲线', 'With hue correction': '加入色相修正', 'Median': '中位数', '95th percentile': '95% 分位', 'Maximum': '最大值', 'CIEDE2000 colour difference': 'CIEDE2000 色差', 'Patches below threshold (%)': '低于阈值的色片比例（%）', 'S-Log3: colour error across all 48 patches': 'S-Log3：全部 48 块色片的实拍色差', 'Measured video vs the same N-RAW reference; no per-patch fitting': '实拍录像与同场 N-RAW 比较；没有逐色片拟合', 'CIELAB is normalized to the reference white-patch luminance, with D65 chromaticity.\nThese are scene-referred errors before a display transform; the retained default clamp is used.': 'CIELAB 以参照白片亮度归一化，白点色度为 D65。\n评价的是显示变换前的场景色差，使用当前默认截断。', 'Fixed integer implementation: example set': '现用整数方案：一组固定示例', 'Fixed fit\n(integer)': '固定参数\n（整数）', 'Held-out light\n(integer)': '留出一种光源\n（整数）', 'Held-out hue sector\n(float)': '留出整段色相\n（浮点）', 'Colour ratio RMS': '色彩比例 RMS', 'Luminance RMS': '亮度 RMS', 'Error (stops)': '误差（档）', 'Log3G10 / REDWideGamutRGB: offline prediction': 'Log3G10 / REDWideGamutRGB：离线预测', 'Current integer matrix and hue table | 48 patches × 3 lights × 2 shutter speeds': '现用整数矩阵与色相表｜48 块色片 × 3 种光源 × 2 档快门', 'Left: first recorded lighting condition, 1/250 s; vectors are not magnified. Right: all 288 patch conditions.\nThree neutral patches align exposure and white balance per condition. Model predictions, not a new camera measurement.\nCIE locus: CIE 2019, CC BY-SA 4.0.': '左图：采集顺序第一种光源、1/250 秒，偏差未放大；右图：全部 288 个色片条件。\n每个条件用 3 块中性片对齐曝光和白平衡。这里是模型预测结果。\n光谱轨迹：CIE 2019，CC BY-SA 4.0。', 'Log3G10: fixed-model error in each recorded condition': 'Log3G10：各拍摄条件的固定模型误差', '48 patches per condition; the same integer implementation is used in all six sets': '每种条件 48 块色片；六组使用同一套整数方案', 'Offline, in-sample prediction after three-neutral alignment. This panel shows variation across the dataset;\nheld-out light and hue-sector results are reported separately.': '离线、样本内预测，已用 3 块中性片对齐。此图展示数据集内不同条件的差异；\n留出光源与色相的结果另列。'}

ZH.update({
    'Recording spaces + matrix reference':'录像编码色域与标定矩阵参考',
    'Encoding spaces and Adobe / LibRaw Z8 calibration reference':'标准编码空间与 Adobe / LibRaw Z8 标定参考',
    'Adobe / LibRaw Z8\n(calibration reference)':'Adobe / LibRaw Z8\n（标定矩阵参考）',
    'Purple: virtual basis coordinates from one Adobe / LibRaw Z8 matrix.\nNo assigned illuminant, dual-illuminant interpolation or individual-body match.\nVirtual reference only, not a measured sensor-coverage boundary.\nD65*: the three encoding spaces. Sources: Nikon, Sony, RED, LibRaw.\nLocus: CIE 2019 (CC BY-SA 4.0).':
    '紫色：Adobe / LibRaw Z8 单矩阵推算的虚拟基坐标。\n未指定校准光源，未做双光源插值或个体机身匹配。\n此参考不代表实测传感器覆盖边界。\nD65* 仅标记三种编码空间。来源：Nikon、Sony、RED、LibRaw。\n光谱轨迹：CIE 2019（CC BY-SA 4.0）。',
})

def render(data,xyz,errors,rwg,summary,language="en",chinese_font=None):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from PIL import Image
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.titlesize':13,'axes.labelsize':11,'figure.facecolor':'white','axes.facecolor':'white','axes.spines.top':False,'axes.spines.right':False,'axes.edgecolor':'#64748b','text.color':'#233345','axes.labelcolor':'#233345','xtick.color':'#45566c','ytick.color':'#45566c','grid.color':'#dce3e9','grid.linewidth':.65,'svg.hashsalt':'nikon-colour-report'})
    blue,orange,gray='#1768AC','#CE6A28','#617286'
    dest=ROOT/'docs/images';dest.mkdir(exist_ok=True)
    if language=='zh':
        from matplotlib import font_manager
        if chinese_font:
            font_manager.fontManager.addfont(str(chinese_font))
            zhfont=font_manager.FontProperties(fname=str(chinese_font))
        else:
            zhfont=font_manager.FontProperties(family=['Noto Sans CJK SC','Microsoft YaHei','Hiragino Sans GB','PingFang SC','SimHei'])
        font_manager.findfont(zhfont,fallback_to_default=False)
    cie=json.loads((DATA/'cie-1931.json').read_text());values=np.array(cie['values']);locus=xy(values[:,1:]);locus=np.vstack([locus,locus[0]])
    def save(fig,name):
        if language=='zh':
            from matplotlib.text import Text
            for ax in fig.axes:
                labels=[t.get_text() for t in ax.get_xticklabels()]
                if any(v in ZH or v.startswith('Light ') for v in labels):
                    labels=[ZH.get(v,v).replace('Light ','光源 ').replace(' s',' 秒') for v in labels]
                    ax.set_xticks(ax.get_xticks(),labels)
            for text in fig.findobj(match=Text):
                original=text.get_text()
                translated=ZH.get(original,original)
                for threshold in (1,2):
                    if original.endswith(f' below {threshold}'):
                        translated=original.split(' below ')[0]+f' 色片小于 {threshold}'
                if original.startswith('Light '):translated=original.replace('Light ','光源 ').replace(' s',' 秒')
                text.set_text(translated)
                size,weight=text.get_fontsize(),text.get_fontweight()
                text.set_fontproperties(zhfont);text.set_fontsize(size);text.set_fontweight(weight)
            name=name.replace('.png','-zh.png')
        buf=io.BytesIO();fig.savefig(buf,format='png',dpi=155,facecolor='white');buf.seek(0)
        with Image.open(buf) as im:im.convert('RGB').save(dest/name,optimize=True)
        plt.close(fig)
    def chroma(ax):
        ax.plot(locus[:,0],locus[:,1],color='#bdc8d2',lw=1,zorder=0)
        ax.set(xlim=(.05,.72),ylim=(.02,.78),xlabel='CIE 1931 x',ylabel='CIE 1931 y');ax.set_aspect('equal');ax.grid(alpha=.5)
    def arrows(ax,target,value,color,label="Recorded video"):
        ax.quiver(target[:,0],target[:,1],value[:,0]-target[:,0],value[:,1]-target[:,1],angles='xy',scale_units='xy',scale=1,width=.0025,color=color,alpha=.65,zorder=2)
        ax.scatter(target[:,0],target[:,1],s=30,facecolors='white',edgecolors='#334155',lw=.8,label='N-RAW reference',zorder=3)
        ax.scatter(value[:,0],value[:,1],s=16,color=color,marker='x',lw=1,label=label,zorder=4)
    fig,ax=plt.subplots(figsize=(7.8,9.4));fig.subplots_adjust(top=.87,bottom=.19,left=.10,right=.96)
    ax.plot(locus[:,0],locus[:,1],color=gray,lw=1.25,label='Spectral locus')
    for name,color,style,marker in [('BT.2020 (N-Log)','#348447','--','^'),('S-Gamut3.Cine',blue,'-','o'),('REDWideGamutRGB',orange,'-.','s')]:
        p=np.array(PRIMARIES[name]);q=np.vstack([p,p[0]]);ax.plot(q[:,0],q[:,1],color=color,lw=1.7,ls=style,label=name);ax.scatter(p[:,0],p[:,1],s=25,color=color,marker=marker)
        for label,point in zip('RGB',p):
            offset=(-15,-15) if name=='S-Gamut3.Cine' and label in 'RB' else ((-16,6) if name=='BT.2020 (N-Log)' else (6,6))
            ax.annotate(label,point,xytext=offset,textcoords='offset points',color=color,fontsize=10)
    p=adobe_reference_xy();q=np.vstack([p,p[0]]);purple='#8644A3'
    ax.plot(q[:,0],q[:,1],color=purple,lw=2.1,ls=':',label='Adobe / LibRaw Z8\n(calibration reference)',zorder=3)
    ax.scatter(p[:,0],p[:,1],s=30,color=purple,marker='D',zorder=4)
    for label,point,offset in zip(['R*','G*','B*'],p,[(-35,-28),(10,12),(-17,-15)]):
        if label=='R*':
            ax.annotate(label,point,xytext=(.55,.35),textcoords='data',color=purple,fontsize=10,arrowprops=dict(arrowstyle='-',color=purple,lw=.7))
        else:
            ax.annotate(label,point,xytext=offset,textcoords='offset points',color=purple,fontsize=10)
    ax.scatter(*D65,color='#233345',marker='+',s=90);ax.annotate('D65*',D65,xytext=(9,-15),textcoords='offset points')
    ax.set(xlim=(-.04,.85),ylim=(-.24,1.59),xlabel='CIE 1931 x',ylabel='CIE 1931 y');ax.set_aspect('equal');ax.grid(alpha=.5);ax.legend(loc='upper right',frameon=False,fontsize=9)
    fig.suptitle('Recording spaces + matrix reference',x=.10,ha='left',fontsize=18,fontweight='bold');fig.text(.10,.92,'Encoding spaces and Adobe / LibRaw Z8 calibration reference',fontsize=11,color=gray)
    fig.text(.10,.025,'Purple: virtual basis coordinates from one Adobe / LibRaw Z8 matrix.\nNo assigned illuminant, dual-illuminant interpolation or individual-body match.\nVirtual reference only, not a measured sensor-coverage boundary.\nD65*: the three encoding spaces. Sources: Nikon, Sony, RED, LibRaw.\nLocus: CIE 2019 (CC BY-SA 4.0).',fontsize=8.5,color=gray)
    save(fig,'log-colour-spaces.png')
    fig,axes=plt.subplots(1,2,figsize=(12.6,6.4));fig.subplots_adjust(top=.82,bottom=.19,wspace=.15,left=.07,right=.97)
    target=xy(xyz['reference_ycbcr'])
    for ax,key,title,color in zip(axes,['matrix_curve_only','hue_corrected'],['Matrix and curve only','Current hue-corrected implementation'],[orange,blue]):
        chroma(ax);arrows(ax,target,xy(xyz[key]),color);ax.set_title(title,pad=12);ax.legend(loc='upper right',fontsize=8,frameon=True)
    fig.suptitle('S-Log3 / S-Gamut3.Cine: measured chromaticity',x=.07,ha='left',fontsize=18,fontweight='bold')
    fig.text(.07,.89,'48 pigment patches | ISO 4000, 4000 K, 1/250 s | default clamp',color=gray,fontsize=11)
    fig.text(.07,.065,'Open circles: same-scene N-RAW reference. Crosses: recorded video. Arrows are not magnified.\nThe two panels share the same axes. CIE locus: CIE 2019, CC BY-SA 4.0.',fontsize=9,color=gray)
    save(fig,'log-slog3-chromaticity.png')
    fig,axes=plt.subplots(1,2,figsize=(12.6,5.9));fig.subplots_adjust(top=.79,bottom=.2,wspace=.3,left=.07,right=.97)
    ax=axes[0];metrics=['median','p95','max'];x=np.arange(3);width=.32
    for offset,key,color,label in [(-width/2,'matrix_curve_only',orange,'Matrix + curve'),(width/2,'hue_corrected',blue,'With hue correction')]:
        vals=[summary['slog3'][key][k] for k in metrics];bars=ax.bar(x+offset,vals,width,color=color,label=label)
        ax.bar_label(bars,labels=[f'{v:.2f}' for v in vals],padding=4,fontsize=10)
    ax.set(xticks=x,xticklabels=['Median','95th percentile','Maximum'],ylabel='CIEDE2000 colour difference',ylim=(0,31));ax.grid(axis='y',alpha=.6);ax.set_axisbelow(True);ax.legend(frameon=False,fontsize=9)
    ax=axes[1];vals=np.sort(errors['hue_corrected']);ax.step(np.r_[0,vals],np.r_[0,np.arange(1,49)/48*100],where='post',lw=2,color=blue)
    for threshold in [1,2]:
        count=int((vals<threshold).sum());ax.axvline(threshold,color='#a3afbb',lw=1,ls='--');ax.annotate(f'{count}/48 below {threshold}',(threshold,count/48*100),xytext=(7,-19 if threshold==2 else -22),textcoords='offset points',fontsize=10)
    ax.set(xlabel='CIEDE2000 colour difference',ylabel='Patches below threshold (%)',xlim=(0,3.1),ylim=(0,105));ax.grid(alpha=.5)
    fig.suptitle('S-Log3: colour error across all 48 patches',x=.07,ha='left',fontsize=18,fontweight='bold');fig.text(.07,.87,'Measured video vs the same N-RAW reference; no per-patch fitting',fontsize=11,color=gray)
    fig.text(.07,.055,'CIELAB is normalized to the reference white-patch luminance, with D65 chromaticity.\nThese are scene-referred errors before a display transform; the retained default clamp is used.',fontsize=9,color=gray)
    save(fig,'log-slog3-errors.png')
    fig,axes=plt.subplots(1,2,figsize=(12.6,6.5));fig.subplots_adjust(top=.81,bottom=.2,wspace=.26,left=.07,right=.97)
    first=next(iter(rwg));r=rwg[first];ax=axes[0];chroma(ax);arrows(ax,xy(r['reference']@RWG.T),xy(r['predicted']@RWG.T),blue,'Model prediction');ax.set_title('Fixed integer implementation: example set',pad=12);ax.legend(frameon=True,fontsize=8,loc='upper right')
    ax=axes[1];labels=['Fixed fit\n(integer)','Held-out light\n(integer)','Held-out hue sector\n(float)'];x=np.arange(3);width=.33
    f=summary['log3g10_fixed_integer_model'];lo=data['log3g10']['cross_validation_quantized'];ho=data['log3g10']['cross_validation_hue']['contiguous']
    for offset,key,color,label in [(-width/2,'colour_rms',blue,'Colour ratio RMS'),(width/2,'brightness_rms',orange,'Luminance RMS')]:
        vals=[s[key] for s in (f,lo,ho)];bars=ax.bar(x+offset,vals,width,color=color,label=label);ax.bar_label(bars,labels=[f'{v:.3f}' for v in vals],padding=4,fontsize=10)
    ax.set(xticks=x,xticklabels=labels,ylabel='Error (stops)',ylim=(0,.046));ax.grid(axis='y',alpha=.6);ax.set_axisbelow(True);ax.legend(frameon=False,fontsize=9,loc='upper left')
    fig.suptitle('Log3G10 / REDWideGamutRGB: offline prediction',x=.07,ha='left',fontsize=18,fontweight='bold')
    fig.text(.07,.88,'Current integer matrix and hue table | 48 patches × 3 lights × 2 shutter speeds',fontsize=11,color=gray)
    fig.text(.07,.06,'Left: first recorded lighting condition, 1/250 s; vectors are not magnified. Right: all 288 patch conditions.\nThree neutral patches align exposure and white balance per condition. Model predictions, not a new camera measurement.\nCIE locus: CIE 2019, CC BY-SA 4.0.',fontsize=9,color=gray)
    save(fig,'log-rwg-prediction.png')
    fig,ax=plt.subplots(figsize=(11.5,4.9));fig.subplots_adjust(top=.79,bottom=.23,left=.09,right=.97)
    names=list(rwg);x=np.arange(6);width=.34
    for offset,key,color,label in [(-width/2,'colour_errors',blue,'Colour ratio RMS'),(width/2,'brightness_errors',orange,'Luminance RMS')]:
        vals=[float(np.sqrt(np.mean(rwg[k][key]**2))) for k in names];bars=ax.bar(x+offset,vals,width,color=color,label=label);ax.bar_label(bars,labels=[f'{v:.3f}' for v in vals],padding=4,fontsize=10)
    ax.set(xticks=x,xticklabels=[f'Light {i//2+1}\n'+('1/250 s' if i%2==0 else '1/500 s') for i in range(6)],ylabel='Error (stops)',ylim=(0,.033));ax.legend(frameon=False,loc='upper right');ax.grid(axis='y',alpha=.6);ax.set_axisbelow(True)
    fig.suptitle('Log3G10: fixed-model error in each recorded condition',x=.09,ha='left',fontsize=17,fontweight='bold')
    fig.text(.09,.87,'48 patches per condition; the same integer implementation is used in all six sets',fontsize=11,color=gray)
    fig.text(.09,.065,'Offline, in-sample prediction after three-neutral alignment. This panel shows variation across the dataset;\nheld-out light and hue-sector results are reported separately.',fontsize=9,color=gray)
    save(fig,'log-rwg-conditions.png')
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true',help='Recompute numerical summary only');p.add_argument('--language',choices=['en','zh','both'],default='both');p.add_argument('--chinese-font',type=Path);a=p.parse_args()
    data=json.loads((DATA/'log-colour-samples.json').read_text());xyz,errors,rwg,summary=calculate(data)
    summary['data_sha256']=hashlib.sha256((DATA/'log-colour-samples.json').read_bytes()).hexdigest()
    if a.check:
        old=json.loads((DATA/'log-colour-summary.json').read_text());assert old==summary;print('Numerical report data match the saved summary');return
    (DATA/'log-colour-summary.json').write_text(json.dumps(summary,indent=2)+'\n');
    for language in (['en','zh'] if a.language=='both' else [a.language]):render(data,xyz,errors,rwg,summary,language,a.chinese_font)
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
