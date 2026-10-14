"""Figures, Markdown tables and the PDF page layout for the research note and appendix."""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph,Table,TableStyle
from reportlab.lib.utils import ImageReader
from . import __version__
from .note_content import AUTHOR,TITLE,SUBJECT
from .config import STRATEGIES,load_config
from .io import write_csv

COLORS={'ISK_HOLD':'#2367a1','AD_HOLD':'#e28b24','AD_HARVEST':'#36835a'}
LABELS={'ISK_HOLD':'ISK hold','AD_HOLD':'Depå hold','AD_HARVEST':'Depå harvest'}
SENSITIVITY=['baseline_sweden_lag6','cost_zero','cost_25bp','threshold_zero','threshold_10pct',
        'initial_100k','no_credit_capacity','sweden_lag12']
SENSITIVITY_LABELS=['Baseline','Cost 0','Cost 0.25% per trade','Harvest threshold 0%','Harvest threshold 10%',
               'W0 = 100,000 SEK','Tax-reduction capacity 0','Settlement lag 12 months']
INK='#273447';MUTED='#687789'

def fmt_interval(row,point,low,high,decimals=3):
    return f"{float(row[point])*100:.{decimals}f} [{float(row[low])*100:.{decimals}f}, {float(row[high])*100:.{decimals}f}]"

def _save(fig,out,name):
    fig.savefig(out/'figures'/f'{name}.png',dpi=220,bbox_inches='tight',facecolor='white',
                metadata={'Software':f'umea_risk {__version__} with Matplotlib','Author':AUTHOR})
    fig.savefig(out/'figures'/f'{name}.pdf',bbox_inches='tight',facecolor='white',
                metadata={'Creator':f'umea_risk {__version__} with Matplotlib','Author':AUTHOR,'CreationDate':None})
    plt.close(fig)

def figures(out,c,metrics,contrasts,baseline,supp_contrasts):
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,
        'axes.titleweight':'bold','font.family':'DejaVu Sans','pdf.fonttype':42,'text.color':INK,'axes.labelcolor':INK})
    delta={(r['scenario_id'],r['contrast']):r for r in contrasts}
    arm={(r['scenario_id'],r['strategy']):r for r in metrics}
    # Figure 1: tax schedule and settlement timing.
    cells=['baseline_sweden_lag6','sweden_lag0','symmetric_lag6','symmetric_lag0']
    labels=['Swedish rules, lag 6','Swedish rules, lag 0','Symmetric 30%, lag 6','Symmetric 30%, lag 0']
    fig,axes=plt.subplots(1,2,figsize=(9.2,3.0),layout='constrained')
    for ax,point,low,high,title in zip(axes,['delta_mean','delta_es95'],['delta_mean_ci_low','delta_es_ci_low'],
        ['delta_mean_ci_high','delta_es_ci_high'],['Mean return difference (higher is better)','ES95 difference (lower is better)']):
        rows=[delta[(sid,'harvest_minus_hold')] for sid in cells]
        y=np.arange(4);x=np.array([float(r[point])*100 for r in rows]);lo=np.array([float(r[low])*100 for r in rows]);hi=np.array([float(r[high])*100 for r in rows])
        ax.errorbar(x,y,xerr=np.array([x-lo,hi-x]),fmt='o',color=COLORS['AD_HARVEST'],capsize=3,lw=1.4,ms=6)
        ax.axvline(0,color=MUTED,lw=1,ls='--');ax.set_yticks(y,labels);ax.invert_yaxis();ax.set_xlabel('Harvest minus hold (percentage points)')
        ax.set_title(title,fontsize=10);ax.grid(axis='x',alpha=.18)
    fig.suptitle('Harvest minus hold: tax schedule and settlement lag',fontsize=13)
    _save(fig,out,'figure1_tax_and_lag')
    # Figure 2: distribution of baseline paired differences.
    d=baseline['AD_HARVEST'].net_return-baseline['AD_HOLD'].net_return;W0=c['baseline']['initial_wealth_sek']
    x=np.sort(d*100);y=np.arange(1,len(x)+1)/len(x)
    fig=plt.figure(figsize=(9.2,3.0));ax=fig.add_axes([.08,.2,.6,.66])
    ax.step(x,y,where='post',color=COLORS['AD_HARVEST'],lw=1.8);ax.axvline(0,color=MUTED,ls='--',lw=1)
    ax.set_xlabel('Harvest minus hold, two-year net return (percentage points)');ax.set_ylabel('Cumulative probability');ax.set_ylim(0,1.02);ax.grid(alpha=.2)
    lines=[f'Paths: {len(d):,}',f'Harvest better: {np.mean(d>0):.2%}',f'Hold better: {np.mean(d<0):.2%}',
           f'Equal (no harvest): {np.mean(d==0):.2%}',f'Mean difference: {d.mean()*100:.3f} pp',f'  = {d.mean()*W0:,.0f} SEK on {W0:,.0f} SEK']
    fig.text(.72,.80,'Baseline paired differences',fontsize=10.5,weight='bold')
    fig.text(.72,.72,'\n'.join(lines),fontsize=9.5,linespacing=1.65,va='top')
    fig.suptitle('Distribution of harvest-minus-hold differences in the baseline',fontsize=13,y=.98)
    _save(fig,out,'figure2_paired_difference')
    # Figure 4 (appendix): nine return models.
    grid=[s for s in c['scenarios'] if s['id'].startswith('grid_') or s['id']==cells[0]]
    es=[float(arm[(s['id'],st)]['es95_loss'])*100 for s in grid for st in STRATEGIES]
    mean=[float(arm[(s['id'],st)]['mean_net_return'])*100 for s in grid for st in STRATEGIES]
    style={'ISK_HOLD':dict(marker='o',s=46,facecolors=COLORS['ISK_HOLD'],edgecolors=COLORS['ISK_HOLD']),
           'AD_HOLD':dict(marker='s',s=95,facecolors='none',edgecolors=COLORS['AD_HOLD'],linewidths=1.6),
           'AD_HARVEST':dict(marker='^',s=24,facecolors=COLORS['AD_HARVEST'],edgecolors=COLORS['AD_HARVEST'])}
    fig,axes=plt.subplots(3,3,figsize=(9.2,5.6),sharex=True,sharey=True)
    for i,m in enumerate((.03,.06,.09)):
        for j,sigma in enumerate((.15,.25,.35)):
            scenario=next(s for s in grid if s['parameters']['annual_expected_simple_price_return']==m and s['parameters']['annual_diffusion_volatility']==sigma)
            ax=axes[i,j]
            for strategy in STRATEGIES:
                r=arm[(scenario['id'],strategy)]
                ax.scatter(float(r['es95_loss'])*100,float(r['mean_net_return'])*100,label=LABELS[strategy],zorder=3,**style[strategy])
            ax.set_title(f'm = {m:.0%}, σ = {sigma:.0%}'+(' (baseline)' if m==.06 and sigma==.25 else ''),fontsize=9.5)
            ax.grid(alpha=.2);ax.set_xlim(min(es)-3,max(es)+3);ax.set_ylim(min(mean)-1.5,max(mean)+1.5)
    handles,labels_=axes[0,0].get_legend_handles_labels()
    fig.legend(handles,labels_,loc='lower center',bbox_to_anchor=(.5,.004),ncol=3,frameon=False)
    fig.suptitle('Mean return and ES95 under nine return models',fontsize=13)
    fig.supxlabel('ES95 of two-year loss (%), lower is better',fontsize=10,y=.075)
    fig.supylabel('Mean two-year net return (%), higher is better',fontsize=10)
    fig.subplots_adjust(left=.095,right=.985,bottom=.16,top=.88,hspace=.38,wspace=.13)
    _save(fig,out,'figure4_return_models')
    # Figure 3: supplementary starting-wealth sweep and no-threshold counterfactual.
    hd=[r for r in supp_contrasts if r['contrast']=='harvest_minus_hold']
    sweep=[r for r in hd if r['experiment_role']=='starting_wealth'];cf=next(r for r in hd if r['experiment_role']=='counterfactual_tax_schedule')
    w=np.array([float(r['initial_wealth_sek']) for r in sweep])
    fig,axes=plt.subplots(1,2,figsize=(9.2,3.3),layout='constrained')
    for ax,point,low,high,title in zip(axes,['delta_mean','delta_es95'],['delta_mean_ci_low','delta_es_ci_low'],
        ['delta_mean_ci_high','delta_es_ci_high'],['Mean return difference (higher is better)','ES95 difference (lower is better)']):
        v=np.array([float(r[point]) for r in sweep])*100;lo=np.array([float(r[low]) for r in sweep])*100;hi=np.array([float(r[high]) for r in sweep])*100
        cv,cl,ch=(float(cf[k])*100 for k in (point,low,high))
        ax.axhspan(cl,ch,color='#b9c2cc',alpha=.45,lw=0)
        ax.axhline(cv,color=MUTED,ls=':',lw=1.4,label='No deficit threshold (counterfactual), W0 = 500,000')
        ax.axhline(0,color=MUTED,ls='--',lw=1)
        ax.errorbar(w,v,yerr=np.array([v-lo,hi-v]),fmt='o-',color=COLORS['AD_HARVEST'],capsize=3,lw=1.4,ms=5,label='Swedish rules')
        ax.set_xscale('log');ax.set_xticks(w,[f'{x/1e6:g}M' if x>=1e6 else f'{x/1e3:g}k' for x in w],rotation=45,fontsize=8.5);ax.minorticks_off()
        ax.set_xlabel('Initial investment W0 (SEK)');ax.set_ylabel('Harvest minus hold (pp)');ax.set_title(title,fontsize=10);ax.grid(alpha=.18)
    handles,labels_=axes[1].get_legend_handles_labels()
    fig.legend(handles,labels_,loc='outside lower center',ncol=2,frameon=False,fontsize=9)
    fig.suptitle('Supplementary analysis: starting wealth and the deficit threshold',fontsize=13)
    _save(fig,out,'figure3_wealth_threshold')

def tables(out,metrics,contrasts,supp_contrasts,supp_arms):
    draws=load_config()['monte_carlo_intervals']['resamples']
    def f(r,k):return float(r[k])
    base='baseline_sweden_lag6';arms=[r for r in metrics if r['scenario_id']==base];delta=[r for r in contrasts if r['scenario_id']==base]
    lines=['# Table 1. Baseline results','',
        f'Returns, losses and intervals are in percent; contrasts are in percentage points (pp). Intervals are approximate pointwise 95% Monte Carlo intervals conditional on the model (N = 20,000 paths, {draws:,} paired bootstrap draws). For ES95 differences (A minus B), negative values mean lower tail loss for A.','',
        '| Strategy | Mean return [MC interval] | ES95 [MC interval] | P(W < W0) | P(W ≤ 0) | Funding events | Mean fees, SEK | Harvest frequency |',
        '|---|---|---|---|---|---|---|---|']
    for r in arms:
        lines.append(f"| {LABELS[r['strategy']]} | {fmt_interval(r,'mean_net_return','mean_ci_low','mean_ci_high')} | {fmt_interval(r,'es95_loss','es_ci_low','es_ci_high')} | {f(r,'probability_loss'):.3%} | {f(r,'probability_nonpositive_W'):.3%} | {int(f(r,'count_funding'))} of {int(f(r,'n_paths')):,} | {f(r,'mean_fees_sek'):,.2f} | {f(r,'harvest_frequency'):.2%} |")
    lines+=['','No path required external funding. With zero events in N = 20,000 paths, an approximate one-sided 95% upper bound on the probability is 3/N = 0.015% under this model.','',
        '| Contrast | Mean difference [MC interval], pp | ES95 difference [MC interval], pp | P(difference > 0) | SE of mean difference, pp |',
        '|---|---|---|---|---|']
    names={'harvest_minus_hold':'Harvest − hold','harvest_minus_isk':'Harvest − ISK','hold_minus_isk':'Hold − ISK'}
    for r in delta:
        lines.append(f"| {names[r['contrast']]} | {fmt_interval(r,'delta_mean','delta_mean_ci_low','delta_mean_ci_high')} | {fmt_interval(r,'delta_es95','delta_es_ci_low','delta_es_ci_high')} | {f(r,'paired_probability_positive'):.2%} | {f(r,'delta_mean_mc_se')*100:.5f} |")
    (out/'tables/table1_baseline.md').write_text('\n'.join(lines)+'\n')
    rows=[];lines=['# Table 2. One-at-a-time sensitivity','',
        'Differences are in percentage points with approximate pointwise 95% Monte Carlo intervals conditional on the model. One input changes at a time. H = depå harvest, D = depå hold, I = ISK hold. Negative ES95 differences mean lower tail loss for H.','',
        '| Changed input | H − D mean [interval] | H − D ES95 [interval] | H − I mean [interval] | H − I ES95 [interval] | Harvest frequency |',
        '|---|---|---|---|---|---|']
    for sid,label in zip(SENSITIVITY,SENSITIVITY_LABELS):
        hd=next(r for r in contrasts if r['scenario_id']==sid and r['contrast']=='harvest_minus_hold')
        hi=next(r for r in contrasts if r['scenario_id']==sid and r['contrast']=='harvest_minus_isk')
        h=next(r for r in metrics if r['scenario_id']==sid and r['strategy']=='AD_HARVEST')
        row=dict(scenario_id=sid,changed_input=label,trigger_rate=f(h,'harvest_frequency'))
        for prefix,r in [('H_minus_D',hd),('H_minus_I',hi)]:
            for k in ('delta_mean','delta_mean_ci_low','delta_mean_ci_high','delta_es95','delta_es_ci_low','delta_es_ci_high'):row[prefix+'_'+k]=f(r,k)
        rows.append(row)
        lines.append(f"| {label} | {fmt_interval(hd,'delta_mean','delta_mean_ci_low','delta_mean_ci_high')} | {fmt_interval(hd,'delta_es95','delta_es_ci_low','delta_es_ci_high')} | {fmt_interval(hi,'delta_mean','delta_mean_ci_low','delta_mean_ci_high')} | {fmt_interval(hi,'delta_es95','delta_es_ci_low','delta_es_ci_high')} | {f(h,'harvest_frequency'):.2%} |")
    (out/'tables/table2_sensitivity.md').write_text('\n'.join(lines)+'\n')
    hd=[r for r in supp_contrasts if r['contrast']=='harvest_minus_hold']
    over={(r['experiment_id'],r['strategy']):r['paths_with_annual_deficit_over_100k'] for r in supp_arms}
    lines=['# Table S1. Starting wealth and the deficit threshold (harvest minus hold)','',
        'Supplementary experiments, separate from the 19 primary configurations. Each row uses the primary 20,000 innovation histories and the same 2,000 paired bootstrap draws; all other inputs are at baseline. SEK values are the percentage-point differences multiplied by W0. The last two columns count paths on which the hold or harvest strategy has a capital deficit (70% of a net loss) above 100,000 SEK in at least one tax year, out of 20,000. The mean difference is the average paired difference in final outcome; the ES95 difference is the difference between the two strategies’ tail averages, which need not involve the same paths.','',
        '| Experiment | W0, SEK | Mean difference [MC interval], pp | Mean difference, SEK | ES95 difference [MC interval], pp | ES95 difference, SEK | ES95 interval | Hold paths, deficit > 100k | Harvest paths, deficit > 100k |',
        '|---|---:|---|---:|---|---:|---|---:|---:|']
    word={'positive':'above zero (unfavorable)','negative':'below zero (favorable)','numerically_unresolved':'includes zero'}
    for r in hd:
        label='Swedish rules' if r['experiment_role']=='starting_wealth' else 'No deficit threshold (counterfactual)'
        lines.append(f"| {label} | {f(r,'initial_wealth_sek'):,.0f} | {fmt_interval(r,'delta_mean','delta_mean_ci_low','delta_mean_ci_high')} | {f(r,'delta_mean_sek'):,.0f} | {fmt_interval(r,'delta_es95','delta_es_ci_low','delta_es_ci_high')} | {f(r,'delta_es95_sek'):,.0f} | {word[r['es_direction']]} | {int(float(over[(r['experiment_id'],'AD_HOLD')])):,} | {int(float(over[(r['experiment_id'],'AD_HARVEST')])):,} |")
    (out/'supplementary/table_s1_wealth_threshold.md').write_text('\n'.join(lines)+'\n')
    return arms,delta,rows

class Note:
    """A4 pages with measured paragraph heights; content that would cross the bottom margin raises an error."""
    def __init__(self,path,pages,title=TITLE):
        self.pages=pages
        fonts=Path(matplotlib.get_data_path())/'fonts/ttf'
        for name,file in [('NoteSans','DejaVuSans.ttf'),('NoteSans-Bold','DejaVuSans-Bold.ttf'),('NoteSans-Oblique','DejaVuSans-Oblique.ttf')]:
            pdfmetrics.registerFont(TTFont(name,str(fonts/file)))
        pdfmetrics.registerFontFamily('NoteSans',normal='NoteSans',bold='NoteSans-Bold',italic='NoteSans-Oblique',boldItalic='NoteSans-Bold')
        self.c=canvas.Canvas(str(path),pagesize=A4,pageCompression=1)
        self.c.setTitle(title);self.c.setAuthor(AUTHOR);self.c.setSubject(SUBJECT)
        self.c.setCreator(f'umea_risk {__version__} with ReportLab');self.c.setKeywords('ISK, depå, tax-loss harvesting, expected shortfall, Monte Carlo, Sweden')
        self.width,self.height=A4;self.left=44;self.right=44;self.w=self.width-88;self.page=0;self.y=0
        self.body=ParagraphStyle('body',fontName='NoteSans',fontSize=10,leading=13.1,textColor=colors.HexColor(INK),spaceAfter=7)
    def new_page(self,title,footer):
        if self.page:self.c.showPage()
        self.page+=1;self.y=self.height-49
        self.c.setFillColor(colors.HexColor('#2367a1'));self.c.setFont('NoteSans-Bold',8)
        self.c.drawString(self.left,self.y,'SWEDISH INVESTMENT ACCOUNTS')
        self.c.setFillColor(colors.HexColor(INK));self.c.setFont('NoteSans',8)
        self.c.drawRightString(self.width-self.right,28,f'{footer} | {self.page} / {self.pages}')
        self.y-=30;self.heading(title,17)
    def heading(self,text,size=11):
        p=Paragraph(text,ParagraphStyle('heading',fontName='NoteSans-Bold',fontSize=size,leading=size+4,textColor=colors.HexColor('#173b61')))
        self.flow(p,gap=8)
    def flow(self,item,gap=6):
        w,h=item.wrap(self.w,self.y-45)
        if self.y-h<45:raise ValueError(f'PDF layout overflow on page {self.page}: y={self.y}, height={h}')
        item.drawOn(self.c,self.left,self.y-h);self.y-=h+gap
    def paragraph(self,text,size=None):
        style=self.body if size is None else ParagraphStyle('small',parent=self.body,fontSize=size,leading=size+2.3)
        # Explicit script sizes keep inline mathematics clear of adjacent lines.
        text=text.replace('<sub>','<sub rise="2" size="7">').replace('<super>','<super rise="4" size="7">')
        if '<br/>' in text:
            style=ParagraphStyle('equation',parent=style,leading=16)
        self.flow(Paragraph(text,style),gap=6)
    def table(self,data,widths=None,font=8):
        style=ParagraphStyle('cell',fontName='NoteSans',fontSize=font,leading=font+2)
        cells=[[Paragraph(str(x),style) for x in row] for row in data]
        table=Table(cells,colWidths=widths or [self.w/len(data[0])]*len(data[0]))
        table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e8eff5')),('VALIGN',(0,0),(-1,-1),'TOP'),
            ('LINEBELOW',(0,0),(-1,0),.6,colors.HexColor('#7490aa')),('LINEBELOW',(0,-1),(-1,-1),.4,colors.HexColor('#bdcbd7')),
            ('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3)]))
        self.flow(table,gap=8)
    def picture(self,path,max_height=None):
        reader=ImageReader(str(path));w,h=reader.getSize();height=self.w*h/w
        if max_height and height>max_height:height=max_height;width=height*w/h
        else:width=self.w
        if self.y-height<45:raise ValueError(f'Image overflow page {self.page}')
        self.c.drawImage(reader,self.left+(self.w-width)/2,self.y-height,width=width,height=height);self.y-=height+4
    def finish(self):
        if self.page!=self.pages:raise ValueError(f'Expected {self.pages} pages, produced {self.page}')
        self.c.save()

def generate_outputs(out,c,metrics,contrasts,baseline,validation,supp_contrasts,supp_arms):
    from .note_content import render_note
    out=Path(out);(out/'supplementary').mkdir(parents=True,exist_ok=True)
    figures(out,c,metrics,contrasts,baseline,supp_contrasts)
    arms,deltas,robust=tables(out,metrics,contrasts,supp_contrasts,supp_arms)
    render_note(out,c,metrics,contrasts,baseline,validation,arms,deltas,robust,supp_contrasts,Note,fmt_interval,LABELS)

def refresh_saved(out):
    """Rebuild tables, figures and documents from the saved results of a complete run; no simulation."""
    import csv
    from types import SimpleNamespace
    from .config import read_json
    out=Path(out)
    def read_rows(path):
        rows=list(csv.DictReader(path.open()))
        for row in rows:
            for k,v in row.items():
                if v=='':row[k]=None;continue
                try:row[k]=float(v)
                except ValueError:pass
        return rows
    metrics=read_rows(out/'tables/scenario_metrics.csv');contrasts=read_rows(out/'tables/contrasts.csv')
    supp=read_rows(out/'supplementary/supplementary_contrasts.csv');supp_arms=read_rows(out/'supplementary/supplementary_metrics.csv')
    baseline={}
    for strategy in STRATEGIES:
        with np.load(out/f'arrays/outcomes/baseline_sweden_lag6__{strategy}.npz',allow_pickle=False) as a:
            baseline[strategy]=SimpleNamespace(net_return=a['net_return'])
    generate_outputs(out,load_config(),metrics,contrasts,baseline,read_json(out/'validation/validation_results.json'),supp,supp_arms)
    print('Tables, figures and documents rebuilt from saved results; no simulation was run.')

if __name__=='__main__':
    import sys
    from .config import ROOT
    refresh_saved(Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'reproduction')
