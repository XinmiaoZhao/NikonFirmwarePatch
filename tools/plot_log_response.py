"""Recompute the public report from camera samples and separately labelled model outputs."""
import argparse
import io
import json
from pathlib import Path

import numpy as np
from plot_colour_report import de2000, lab, xy
from plot_colour_revision import PRIM, errors, linear, npm

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'docs/data'
MODES = ('log3g10','slog3')
NAMES = ('Log3G10 / RWG','S-Log3 / S-Gamut3.Cine')
ARMS = ('gamut_curve','stock_cpxs','identity_cpxs','complete')


def compare(video, reference, mode, grey):
    scale = np.exp(np.log(reference[grey] / video[grey]).mean(axis=0))
    transform = npm(PRIM[mode]).T
    actual = (video * scale) @ transform
    target = reference @ transform
    white = target[:,1].max()
    delta = de2000(lab(actual, white), lab(target, white))
    return dict(de=delta.tolist(), xy=xy(actual).tolist(), reference_xy=xy(target).tolist(),
                median=float(np.median(delta)), p95=float(np.percentile(delta,95)), maximum=float(delta.max()))


def compute():
    samples = json.loads((DATA/'log-camera.json').read_text())
    controls = json.loads((DATA/'log-controls.json').read_text())
    results = {}
    for mode in MODES:
        keys = samples['modes'][mode]['patches']
        assert keys == controls['patches']
        grey = [keys.index(k) for k in samples['grey_patches']]
        sims, camera = {}, {}
        for group, rows in controls['modes'][mode]['groups'].items():
            target = np.array(controls['groups'][group]['reference_rwg'])
            if mode == 'slog3':
                target = target @ np.linalg.solve(npm(PRIM[mode]), npm(PRIM['log3g10'])).T
            sims[group] = {arm:compare(linear(rows[arm],mode),target,mode,grey) for arm in ARMS}
        metrics = {}
        for group, observation in samples['modes'][mode]['groups'].items():
            clips = observation['clips']['current']
            video = np.mean([linear(clip['ycbcr'], mode) for clip in clips], axis=0)
            holdout = np.mean([linear(clip['holdout_ycbcr'], mode) for clip in clips], axis=0)
            refs = observation['references']
            field = 'preF' if mode == 'log3g10' else 'cine'
            targets = {t:np.asarray(refs[t][field]) for t in ('pre','post')}
            targets['mean'] = (targets['pre'] + targets['post']) / 2
            camera[group], metrics[group] = {}, {}
            for timing, target in targets.items():
                camera[group][timing] = compare(video, target, mode, grey)
                minimum = samples['ratio_metric_min_linear'] if mode == 'slog3' else None
                stats, details = errors(video,target,keys,samples['grey_patches'],mode,minimum)
                chosen = ('pre','post') if timing == 'mean' else (timing,)
                hold_target = np.mean([refs[t]['holdout_linear'] for t in chosen],axis=0)
                residual = np.log2(holdout * details['scale'] / hold_target)
                stats['holdout_colour_max'] = float(np.max(np.abs(residual[:,[0,2]] - residual[:,[1]])))
                if mode == 'slog3':
                    code = np.mean([clip['ycbcr'] for clip in clips],axis=0)
                    code_target = np.mean([refs[t]['M'] for t in chosen],axis=0)
                    keep = [k not in samples['code_metric_excluded_patches'] for k in keys]
                    stats['code_rms_45'] = float(np.sqrt(np.mean((code-code_target)[keep]**2)))
                metrics[group][timing] = stats
        results[mode] = dict(model=sims, camera=camera, metrics=metrics)
    return results


def join_camera_panels(directory, suffix):
    """Place the two identically scaled measured panels side by side at native size."""
    from PIL import Image
    with Image.open(directory/f'log-camera-xy-log3g10{suffix}.png') as left, \
            Image.open(directory/f'log-camera-xy-slog3{suffix}.png') as right:
        assert left.size == right.size
        combined = Image.new('RGB', (2*left.width, left.height), 'white')
        combined.paste(left, (0, 0))
        combined.paste(right, (left.width, 0))
        combined.save(directory/f'log-camera-xy{suffix}.png', optimize=True)


def render(results, zh, font):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    from PIL import Image
    def t(en,cn): return cn if zh else en
    if zh and font:
        font_manager.fontManager.addfont(font)
    family = font_manager.FontProperties(fname=font).get_name() if zh and font else ('Hiragino Sans GB' if zh else 'DejaVu Sans')
    plt.rcParams.update({'font.family':family,'font.size':10,'axes.spines.top':False,
                         'axes.spines.right':False,'axes.unicode_minus':False,'text.color':'#263d4a'})
    def save(fig,stem):
        stream=io.BytesIO()
        fig.savefig(stream,format='png',dpi=150,bbox_inches='tight',pad_inches=.22)
        stream.seek(0)
        suffix='-zh' if zh else ''
        with Image.open(stream) as image:
            image.convert('RGB').save(ROOT/'docs/images'/f'{stem}{suffix}.png',optimize=True)
        plt.close(fig)
    labels=[t('Gamut matrix + curve','仅换色域矩阵与曲线'),t('Factory Cpxs','保留原厂 Cpxs'),t('Identity Cpxs','Cpxs 恒等'),t('Complete chain','完整链路')]
    fig,axes=plt.subplots(1,2,figsize=(10.8,4.4),sharex=True,layout='constrained')
    for ax,mode,name in zip(axes,MODES,NAMES):
        for i,arm in enumerate(ARMS):
            values=np.concatenate([g[arm]['de'] for g in results[mode]['model'].values()])
            lo,hi=np.percentile(values,[50,95])
            ax.plot([lo,hi],[i,i],color='#507d91',lw=2)
            ax.plot(lo,i,'o',color='#17698a');ax.plot(hi,i,'|',ms=14,color='#17698a')
        ax.set(yticks=range(4),yticklabels=labels,ylim=(3.7,-.7),xlim=(0,None),xlabel=t('Scene-referred ΔE00','场景参照色差 ΔE00'),title=name)
        ax.grid(axis='x',alpha=.22)
    fig.suptitle(t('Model predictions · median (dot) to 95th percentile (tick)\n48 patches × 3 lighting/exposure conditions','模型预测 · 从中位数（点）到 95% 分位（竖线）\n48 块色片 × 3 个光照与曝光条件'),fontsize=14)
    save(fig,'log-control-errors')
    def chromaticity(ax, data, label, colour):
        video = np.array(data['xy'])
        raw = np.array(data['reference_xy'])
        ax.quiver(*raw.T, *(video-raw).T, angles='xy', scale_units='xy', scale=1,
                  width=.003, color='#89959c')
        ax.scatter(*raw.T,s=32,facecolors='none',edgecolors='#384953',label=t('N-RAW reference','N-RAW 参照'))
        ax.scatter(*video.T,s=22,marker='x',color=colour,label=label)
        ax.set(xlim=(.065,.605),ylim=(-.005,.535),xlabel='CIE 1931 x',ylabel='CIE 1931 y')
        ax.set_aspect('equal')
        ax.grid(alpha=.18)

    for mode, name in zip(MODES,NAMES):
        fig, axes = plt.subplots(2,2,figsize=(9,9),layout='constrained',sharex=True,sharey=True)
        for ax, arm, label in zip(axes.flat,ARMS,labels):
            chromaticity(ax,results[mode]['model']['K250'][arm],t('Prediction','模拟输出'),'#ba532c')
            ax.set_title(label)
        axes[0,0].legend(fontsize=9)
        fig.suptitle(name + t(' · simulated shifts\nCool light, 1/250 s · 48 patches · actual displacement',
                              ' · 模拟色度偏移\n冷光 1/250 秒 · 48 块色片 · 偏差原比例'))
        save(fig,'log-control-xy-'+mode)
        fig,ax = plt.subplots(figsize=(5,5),layout='constrained')
        chromaticity(ax,results[mode]['camera']['K250']['mean'],t('Recording','录像'),'#17698a')
        ax.legend(fontsize=9)
        ax.set_title(name+t(' · recorded, cool 1/250 s',' · 实拍，冷光 1/250 秒'))
        save(fig,'log-camera-xy-'+mode)

    join_camera_panels(ROOT/'docs/images', '-zh' if zh else '')

    fig, axes = plt.subplots(1,2,figsize=(10,4.7),layout='constrained',sharex=True,sharey=True)
    conditions = [('K250',t('Cool 1/250 s','冷光 1/250 秒')),('K500',t('Cool 1/500 s','冷光 1/500 秒')),
                  ('W250',t('Warm 1/250 s','暖光 1/250 秒')),('W500',t('Warm 1/500 s (extra)','暖光 1/500 秒（加拍）'))]
    for ax,mode,name in zip(axes,MODES,NAMES):
        for (g,label),style in zip(conditions,['-','--','-.',':']):
            if g in results[mode]['camera']:
                values = np.sort(results[mode]['camera'][g]['mean']['de'])
                ax.step(np.r_[0,values],np.arange(len(values)+1),where='post',label=label,linestyle=style)
        ax.set(title=name,xlabel=t('Scene-referred ΔE00','场景参照色差 ΔE00'),yticks=[0,12,24,36,48],ylim=(0,50),xlim=(0,None))
        ax.grid(alpha=.18)
        ax.legend(loc='lower right',fontsize=9)
    axes[0].set_ylabel(t('Patches at or below ΔE00','色差小于或等于横轴值的色片数'))
    fig.suptitle(t('Camera recordings · cumulative colour difference (48 patches per condition)',
                   '当前实拍 · ΔE00 累计分布（每个条件 48 片）'))
    save(fig,'log-camera-de-cdf')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--check',action='store_true');ap.add_argument('--chinese-font')
    args=ap.parse_args();results=compute()
    compact={m:{'model':{},'camera':{}} for m in MODES}
    for m in MODES:
        for arm in ARMS:
            v=np.concatenate([g[arm]['de'] for g in results[m]['model'].values()])
            compact[m]['model'][arm]=np.percentile(v,[50,95,100]).tolist()
        for g,refs in results[m]['camera'].items():
            compact[m]['camera'][g]={ref:[v[k] for k in ['median','p95','maximum']] for ref,v in refs.items()}
        compact[m]['linear_metrics'] = results[m]['metrics']
    file=DATA/'log-response-summary.json'
    if args.check:
        assert json.loads(file.read_text())==compact
        return
    file.write_text(json.dumps(compact,indent=2)+'\n')
    for zh in [False,True]:render(results,zh,args.chinese_font)


if __name__=='__main__':main()
