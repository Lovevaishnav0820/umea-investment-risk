"""Text of the research note and appendix, rendered to PDF and to Markdown from the same source."""
from html import unescape
from pathlib import Path
import platform
import re
import sys

AUTHOR = 'Love Vaishnav'
REVISION_DATE = '2026-10-14'
TITLE = 'One loss realization, two tax years: Swedish investment accounts'
SUBJECT = 'Monte Carlo comparison of ISK holding, depå holding and one depå loss realization under Swedish 2026 tax rules'
FIGURES = ['figure1_tax_and_lag', 'figure2_paired_difference', 'figure3_wealth_threshold', 'figure4_return_models']
NOTE_PAGES = 5
APPENDIX_PAGES = 1
PROJECT_LIST_URL = ('https://www.umu.se/globalassets/organisation/fakulteter/teknat/institutionen-for-matematik-och-matematisk-statistik/'
                    'dokument/internshipprojects-autumn2026.pdf')
REFERENCES = [
    ('S1', 'Skatteverket. Kan jag kvitta vinst mot förlust när jag har sålt värdepapper? (Netting gains and losses on securities.)',
     'https://www.skatteverket.se/privat/etjansterochblanketter/svarpavanligafragor/vardepapper/privatvardepapperfaq/kanjagkvittavinstmotforlustnarjagharsaltvardepapper.5.2b543913a42158acf800015357.html'),
    ('S2', 'Skatteverket. Skattereduktioner (Tax reductions).',
     'https://www.skatteverket.se/privat/skatter/arbeteochinkomst/skattereduktioner.4.3810a01c150939e893f1a17e.html'),
    ('S3', 'Skatteverket. Räkna ut omkostnadsbelopp (Acquisition cost).',
     'https://www.skatteverket.se/privat/skatter/vardepapper/omkostnadsbelopp.4.12815e4f14a62bc048fa7bc.html'),
    ('S4', 'Skatteverket. Skatt på investeringssparkonto (Tax on investment savings accounts), income year 2026.',
     'https://www.skatteverket.se/privat/skatter/vardepapper/investeringssparkontoisk.4.5fc8c94513259a4ba1d800037851.html'),
    ('S5', 'Skatteverket. Betala kvarskatt (Paying tax owed after the final assessment).',
     'https://www.skatteverket.se/privat/deklaration/betalakvarskatt.4.12815e4f14a62bc048f106ca.html'),
    ('P1', 'Farago, A., Hjalmarsson, E. and Kiss, T. (2025). Understanding Wealth-Tax Rates: An Investor-Utility Mapping to Capital-Gains Taxes. European Financial Management 31(4), 1413–1420. DOI 10.1111/eufm.12541.',
     'https://doi.org/10.1111/eufm.12541'),
    ('P2', 'Dammon, R. M., Spatt, C. S. and Zhang, H. H. (2001). Optimal Consumption and Investment with Capital Gains Taxes. The Review of Financial Studies 14(3), 583–616. DOI 10.1093/rfs/14.3.583.',
     'https://doi.org/10.1093/rfs/14.3.583'),
    ('P3', 'Chaudhuri, S. E., Burnham, T. C. and Lo, A. W. (2020). An Empirical Evaluation of Tax-Loss-Harvesting Alpha. Financial Analysts Journal 76(3), 99–108. DOI 10.1080/0015198X.2020.1760064. Only the CFA Institute summary of this article was consulted.',
     'https://rpc.cfainstitute.org/research/financial-analysts-journal/2020/empirical-evaluation-tax-loss-harvesting-alpha'),
    ('P4', 'Rockafellar, R. T. and Uryasev, S. (2002). Conditional Value-at-Risk for General Loss Distributions. Journal of Banking &amp; Finance 26(7), 1443–1471. DOI 10.1016/S0378-4266(02)00271-6.',
     'https://doi.org/10.1016/S0378-4266(02)00271-6'),
    ('U1', 'Umeå University, Department of Mathematics and Mathematical Statistics. Internship Programme: project list for the calendar year 2027. Project “Analyzing risk and return of Swedish investment vehicles”, PDF page 13 (printed page 10).',
     PROJECT_LIST_URL),
]

def markdown(text):
    """Convert the PDF markup of a paragraph without mathematics to Markdown."""
    if '<sub>' in text or '<super>' in text: raise ValueError('Paragraphs with sub/superscripts need explicit Markdown')
    text = text.replace('<br/>', '\n\n')
    text = re.sub(r'<a href="([^"]+)">(.*?)</a>', r'[\2](\1)', text)
    text = re.sub(r'</?b>', '**', text)
    text = re.sub(r'</?i>', '*', text)
    return unescape(re.sub(r'<[^>]+>', '', text))

def environment_label():
    return f'{platform.system()} {platform.machine()}, Python {sys.version.split()[0]}'

def render_note(out, c, metrics, contrasts, base, validation, arms, deltas, robust, supp_contrasts, Note, fmt_interval, labels):
    out = Path(out); md = []
    footer = f'{AUTHOR} | {REVISION_DATE}'
    draws = c['monte_carlo_intervals']['resamples']; N = c['simulation']['paths']; W0 = c['baseline']['initial_wealth_sek']
    f = lambda r, k: float(r[k])
    pp = lambda x: f'{x*100:.3f}'
    hd = next(r for r in deltas if r['contrast'] == 'harvest_minus_hold')
    hi = next(r for r in deltas if r['contrast'] == 'harvest_minus_isk')
    h = next(r for r in arms if r['strategy'] == 'AD_HARVEST')
    tax_mode = {s['id']: s['parameters']['tax_mode'] for s in c['scenarios']}
    hd_all = [r for r in contrasts if r['contrast'] == 'harvest_minus_hold']
    swedish = [r for r in hd_all if tax_mode[r['scenario_id']] == 'sweden2026']
    mean_negative = sum(r['mean_direction'] == 'negative' for r in swedish)
    es_up = sum(r['es_direction'] == 'positive' for r in hd_all)
    es_down = sum(r['es_direction'] == 'negative' for r in hd_all)
    es_zero = sum(r['es_direction'] == 'numerically_unresolved' for r in hd_all)
    by_id = {r['scenario_id']: r for r in hd_all}
    hi_by_id = {r['scenario_id']: r for r in contrasts if r['contrast'] == 'harvest_minus_isk'}
    mean_sek = f(hd, 'delta_mean') * W0; es_sek = f(hd, 'delta_es95') * W0
    supp = [r for r in supp_contrasts if r['contrast'] == 'harvest_minus_hold']
    sweep = [r for r in supp if r['experiment_role'] == 'starting_wealth']; cf = next(r for r in supp if r['experiment_role'] == 'counterfactual_tax_schedule')
    sv = next(p for p in validation['property_tests'] if p['id'] == 'scalar_vector_agreement')
    resource = next(p for p in validation['property_tests'] if p['id'] == 'resource_conservation')
    counts = validation['counts']

    n = Note(out/'note/research_note.pdf', NOTE_PAGES)
    def page(title, first=False):
        n.new_page(title, footer); md.append(('# ' if first else '## ') + title)
    def para(text, size=None, md_text=None):
        n.paragraph(text, size); md.append(md_text if md_text is not None else markdown(text))
    def heading(text):
        n.heading(text); md.append('### ' + text)
    def table(rows, widths=None, font=9):
        n.table(rows, widths, font)
        md.append('\n'.join(['| ' + ' | '.join(markdown(str(v)) for v in rows[0]) + ' |',
            '| ' + ' | '.join('---' for _ in rows[0]) + ' |',
            *['| ' + ' | '.join(markdown(str(v)) for v in row) + ' |' for row in rows[1:]]]))
    def picture(stem, alt, caption, height):
        n.picture(out/'figures'/f'{stem}.png', height); n.paragraph(caption, 9)
        md.append(f'![{alt}](../figures/{stem}.png)\n\n*{markdown(caption)}* ([PDF version](../figures/{stem}.pdf))')

    # Page 1
    page('One loss realization, two tax years', first=True)
    para(f'<b>{AUTHOR}</b> | {REVISION_DATE}', 10)
    para('Does realizing a loss once, at month 12, and investing the resulting tax relief when it is received, change the two-year mean net return or the tail loss of a Swedish depå investment? The study compares that policy with holding in the depå and with holding in an investment savings account (ISK). The question is taken from the project “Analyzing risk and return of Swedish investment vehicles” in Umeå University’s internship project list [U1]; this is an independent study, not supervised by or affiliated with Umeå University.')
    para('<b>Strategies.</b> I = ISK hold; D = depå hold; H = depå harvest, which sells and immediately repurchases the whole position once, at month 12, if net sale proceeds are more than 5% below acquisition cost. All positions are sold at month 24 and every assessed tax is then settled.')
    para('<b>Outcomes.</b> W<sub>0</sub> is the initial investment and W the net investment outcome after all taxes are settled, less any external payments F that the investor makes to cover a tax bill the account cannot pay. The two-year return is r = W/W<sub>0</sub> − 1 and the loss is L = −r. ES95 (expected shortfall at 95%) is the mean of the worst 5% probability mass of L. Returns are not annualized.',
         md_text='**Outcomes.** $W_0$ is the initial investment and $W$ the net investment outcome after all taxes are settled, less any external payments $F$ that the investor makes to cover a tax bill the account cannot pay. The two-year return is $r = W/W_0 - 1$ and the loss is $L = -r$. ES95 (expected shortfall at 95%) is the mean of the worst 5% probability mass of $L$. Returns are not annualized.')
    table([['Table 1. Baseline', 'Mean return, % [MC interval]', 'ES95 loss, % [MC interval]'],
        *[[labels[r['strategy']], fmt_interval(r, 'mean_net_return', 'mean_ci_low', 'mean_ci_high'),
           fmt_interval(r, 'es95_loss', 'es_ci_low', 'es_ci_high')] for r in arms]], [120, 196, n.w - 316], 8.9)
    heading('Main results')
    para(f'<b>Mean return.</b> Harvesting lowers the baseline mean two-year return: harvest minus hold is {fmt_interval(hd,"delta_mean","delta_mean_ci_low","delta_mean_ci_high")} percentage points (pp), about {mean_sek:,.0f} SEK in mean final outcome on 500,000 SEK. Harvesting lowers the mean in {mean_negative} of the {len(swedish)} configurations with Swedish tax rules, with every interval below zero. In the baseline, harvesting does better than holding on {f(hd,"paired_probability_positive"):.2%} of paths.', 9.7)
    para(f'<b>Tail loss.</b> In the baseline, harvesting also lowers ES95: the difference is {fmt_interval(hd,"delta_es95","delta_es_ci_low","delta_es_ci_high")} pp, about {es_sek:,.0f} SEK in monetary ES95. This is the difference between the two strategies’ tail averages, not the mean of paired differences. The ES95 effect changes with starting wealth, settlement timing, tax-reduction capacity and return parameters: across all {len(hd_all)} configurations the ES95 interval lies above zero (harvesting worse) in {es_up}, below zero in {es_down} and includes zero in {es_zero}. The section on starting wealth and timing examines why.', 9.7)
    para(f'<b>Accounts.</b> ISK holding has a higher mean return and a higher ES95 than either depå strategy. The depå’s lower tail loss assumes that each year’s tax reduction can be used in full; with zero capacity the H − I ES95 difference shrinks from {pp(f(hi,"delta_es95"))} to {pp(f(hi_by_id["no_credit_capacity"],"delta_es95"))} pp. Because every position is sold at month 24, the study does not capture the depå’s ability to defer gains tax.', 9.7)
    para(f'MC = Monte Carlo. Brackets give approximate pointwise 95% MC intervals from {draws:,} paired bootstrap draws; they measure simulation error conditional on the model. Negative ES95 differences (A minus B) mean lower tail loss for A.', 9)

    # Page 2
    page('Model, tax rules and an analytical benchmark')
    para(f'<b>Prices.</b> {N:,} independent paths of 24 months. All strategies use the same price paths, and all configurations use the same standard-normal innovations Z<sub>t</sub>, transformed with their own parameters. With m the expected annual simple price return and σ the annual volatility,',
         9.6, md_text=f'**Prices.** {N:,} independent paths of 24 months. All strategies use the same price paths, and all configurations use the same standard-normal innovations $Z_t$, transformed with their own parameters. With $m$ the expected annual simple price return and $\\sigma$ the annual volatility,')
    para('log(S<sub>t</sub>/S<sub>t−1</sub>) = [log(1+m) − σ<super>2</super>/2]/12 + σZ<sub>t</sub>/√12,   so E[S<sub>12</sub>/S<sub>0</sub>] = 1+m.', 10.2,
         md_text='$$\\log(S_t/S_{t-1}) = \\frac{\\log(1+m) - \\sigma^2/2}{12} + \\frac{\\sigma Z_t}{\\sqrt{12}}, \\qquad E[S_{12}/S_0] = 1+m.$$')
    para('Baseline: W<sub>0</sub> = 500,000 SEK, S<sub>0</sub> = 100, m = 6%, σ = 25%, trading cost 0.1% per purchase or sale, six-month settlement lag, one non-dividend asset, fractional shares and no interest.', 9.6,
         md_text='Baseline: $W_0 = 500{,}000$ SEK, $S_0 = 100$, $m = 6\\%$, $\\sigma = 25\\%$, trading cost 0.1% per purchase or sale, six-month settlement lag, one non-dividend asset, fractional shares and no interest.')
    para('<b>Depå [S1–S3].</b> Gains and losses are netted within each tax year. A positive net gain is taxed at 30%. For a net loss, 70% forms a capital deficit D, and the tax reduction is 30% of D up to 100,000 SEK plus 21% of the excess, so residual raw losses receive 21% and then 14.7% relief. The threshold and the reduction capacity apply per individual taxpayer and per tax year; unused reductions are not carried forward. Acquisition cost includes purchase fees and follows the average-cost method; an eligible sale may instead deduct 20% of net proceeds, which does not change the acquisition cost of the remaining shares. In H, the sale is assumed to settle before the repurchase, so the repurchased shares get a new acquisition cost.', 9.5)
    para('<b>ISK [S4].</b> With Q<sub>yj</sub> the account value at the start of quarter j and D<sub>y</sub> the deposits in year y, the tax is T<sub>y</sub> = 0.01065 max(K<sub>y</sub> − 300,000, 0) with K<sub>y</sub> = (Q<sub>y1</sub> + … + Q<sub>y4</sub> + D<sub>y</sub>)/4. The rate is 30% of 3.55% (the government bond rate of 2.55% plus 1 percentage point). The 300,000 SEK allowance is assumed unused by other ISK, capital-insurance or PEPP savings. The ISK tax is paid by selling shares.', 9.5,
         md_text='**ISK [S4].** With $Q_{yj}$ the account value at the start of quarter $j$ and $D_y$ the deposits in year $y$, the tax is $T_y = 0.01065\\,\\max(K_y - 300{,}000,\\,0)$ with $K_y = (Q_{y1} + \\dots + Q_{y4} + D_y)/4$. The rate is 30% of 3.55% (the government bond rate of 2.55% plus 1 percentage point). The 300,000 SEK allowance is assumed unused by other ISK, capital-insurance or PEPP savings. The ISK tax is paid by selling shares.')
    para('<b>Timing.</b> Taxes are assessed at months 12 and 24 and settled after a fixed lag of 0, 6 or 12 months. Using the same lag for bills and refunds is a modelling convention; actual payment dates depend on the final tax decision [S5]. Credits received before month 24 are invested immediately; later credits stay in cash. Both model years use the 2026 rules.', 9.5)
    heading('Why a refund does not ensure a gain')
    para('Take one share with acquisition cost b, sold and repurchased at p &lt; b without costs. Let d = b − p, credit R = λd received when the price is s, terminal price z ≥ b and gains-tax rate τ. Reinvesting gives 1 + R/s shares with acquisition cost p + R, and', 9.5,
         md_text='Take one share with acquisition cost $b$, sold and repurchased at $p < b$ without costs. Let $d = b - p$, credit $R = \\lambda d$ received when the price is $s$, terminal price $z \\ge b$ and gains-tax rate $\\tau$. Reinvesting gives $1 + R/s$ shares with acquisition cost $p + R$, and')
    para('W<sub>D</sub> = (1−τ)z + τb,  W<sub>H</sub> = (1−τ)z(1+R/s) + τ(p+R),<br/>ΔW = W<sub>H</sub> − W<sub>D</sub> = d{λ[(1−τ)z/s + τ] − τ}.', 10.1,
         md_text='$$W_D = (1-\\tau)z + \\tau b, \\qquad W_H = (1-\\tau)z(1+R/s) + \\tau(p+R),$$\n\n$$\\Delta W = W_H - W_D = d\\{\\lambda[(1-\\tau)z/s + \\tau] - \\tau\\}.$$')
    para('This holds for 0 ≤ λ ≤ 1, 0 ≤ τ &lt; 1, b ≥ 0.2z and p + R ≥ 0.2z(1 + R/s), with the loss and the final gain in different tax years. For λ &gt; 0 harvesting breaks even at z/s = τ(1−λ)/[λ(1−τ)]; at λ = 0.21 and τ = 0.30 this is 79/49 ≈ 1.612, a price ratio measured from the refund date. With symmetric relief (λ = τ) the break-even ratio is 1.', 9.5,
         md_text='This holds for $0 \\le \\lambda \\le 1$, $0 \\le \\tau < 1$, $b \\ge 0.2z$ and $p + R \\ge 0.2z(1+R/s)$, with the loss and the final gain in different tax years. For $\\lambda > 0$ harvesting breaks even at $z/s = \\tau(1-\\lambda)/[\\lambda(1-\\tau)]$; at $\\lambda = 0.21$ and $\\tau = 0.30$ this is $79/49 \\approx 1.612$, a price ratio measured from the refund date. With symmetric relief ($\\lambda = \\tau$) the break-even ratio is 1.')
    table([['100 → 80 → 100, no costs', 'Credit', 'Final acquisition cost', 'Gains tax', 'Final W'],
        ['21% relief invested at 80', '4.2', '84.2', '6.315', '98.935'],
        ['21% relief kept as cash', '4.2', '80', '6', '98.200'],
        ['30% relief invested at 80', '6', '86', '6.45', '101.050']], [195, 49, 89, 82, n.w - 415], 8.8)
    para('Holding ends at 100 in all three cases. Harvesting lowers the acquisition cost, so the early credit must outweigh the later gains tax; with 21% relief and a 30% gains tax that requires the price to rise by more than about 61% after the refund. If the refund instead buys shares at 60, the first case ends at 100.16, so a later refund is not always worse.', 9.4)

    # Page 3
    page('Simulated comparisons')
    picture('figure1_tax_and_lag', 'Figure 1: harvest minus hold under two tax schedules and two settlement lags',
            'Figure 1. Harvest minus hold (pp) with pointwise 95% MC intervals, under Swedish rules and a counterfactual symmetric 30% schedule, with settlement lags of 6 and 0 months.', 155)
    picture('figure2_paired_difference', 'Figure 2: empirical distribution of baseline harvest-minus-hold differences',
            f'Figure 2. Empirical distribution of all {N:,} baseline harvest-minus-hold return differences. Paths without a harvest give exactly zero.', 150)
    table([['Table 2. Changed input', 'H − D mean / ES95, pp', 'H − I mean / ES95, pp', 'Harvests'],
        *[[r['changed_input'], f"{r['H_minus_D_delta_mean']*100:.3f} / {r['H_minus_D_delta_es95']*100:.3f}",
           f"{r['H_minus_I_delta_mean']*100:.3f} / {r['H_minus_I_delta_es95']*100:.3f}", f"{r['trigger_rate']:.2%}"] for r in robust]],
        [160, 136, 136, n.w - 432], 8.8)
    para(f'Table 2 changes one input at a time (intervals in tables/table2_sensitivity.md). Harvests occur on {f(h,"harvest_frequency"):.2%} of baseline paths; among those paths the mean H − D difference is {pp(f(hd,"triggered_paired_mean"))} pp. The full results for all {len(hd_all)} configurations, with intervals, are in tables/scenario_metrics.csv and tables/contrasts.csv.', 9.4)

    # Page 4
    page('Starting wealth, timing and the tail result')
    para('Per tax year, a capital deficit D receives the reduction R(D) = 0.21D + 0.09 min(D, 100,000). Realizing part of a loss in year 1 and the rest in year 2 gives each part its own 100,000 SEK threshold. Compared with realizing the same total deficit in one year, the split can add at most 0.09 × 100,000 = 9,000 SEK of relief: 1.8% of 500,000 SEK but only 0.45% of 2,000,000 SEK. Without the threshold the reduction is proportional, every depå quantity scales with W<sub>0</sub>, and the harvest-minus-hold comparison in percent does not depend on W<sub>0</sub>.', 9.5,
         md_text='Per tax year, a capital deficit $D$ receives the reduction $R(D) = 0.21D + 0.09\\min(D,\\,100{,}000)$. Realizing part of a loss in year 1 and the rest in year 2 gives each part its own 100,000 SEK threshold. Compared with realizing the same total deficit in one year, the split can add at most $0.09 \\times 100{,}000 = 9{,}000$ SEK of relief: 1.8% of 500,000 SEK but only 0.45% of 2,000,000 SEK. Without the threshold the reduction is proportional, every depå quantity scales with $W_0$, and the harvest-minus-hold comparison in percent does not depend on $W_0$.')
    picture('figure3_wealth_threshold', 'Figure 3: harvest minus hold against starting wealth, with the no-threshold counterfactual',
            f'Figure 3. Supplementary analysis. Harvest minus hold (pp) for eight starting amounts under Swedish rules, with pointwise 95% MC intervals, and the counterfactual without the deficit threshold at W0 = 500,000 SEK (dotted line, shaded interval). Same {N:,} innovations and {draws:,} bootstrap draws as the primary results.', 168)
    label = lambda w: f'{w/1e6:g}M' if w >= 1e6 else f'{w/1e3:g}k'
    wealth = ', '.join(f"{pp(f(r,'delta_es95'))} ({label(f(r,'initial_wealth_sek'))})" for r in sweep)
    para(f'<b>Starting wealth.</b> The supplementary experiments (Table S1) keep every baseline input except W<sub>0</sub>. The H − D ES95 differences, in pp, are {wealth}. At 100,000 SEK the threshold cannot be reached (the deficit is at most 70% of W<sub>0</sub>) and at 200,000 SEK only the most extreme paths reach it; at both, harvesting raises ES95 by the same amount as in the counterfactual below. At 300,000 SEK it still raises ES95; between about 500,000 and 1,000,000 SEK it lowers ES95; at 2,000,000 SEK harvesting raises ES95 again, consistent with the bounded extra relief being small relative to W<sub>0</sub>. In the counterfactual without the threshold, the difference at 500,000 SEK is {pp(f(cf,"delta_es95"))} pp [{pp(f(cf,"delta_es_ci_low"))}, {pp(f(cf,"delta_es_ci_high"))}]. Removing the threshold changes the mean difference only from {pp(f(hd,"delta_mean"))} to {pp(f(cf,"delta_mean"))} pp.', 9.4,
         md_text=f'**Starting wealth.** The supplementary experiments (Table S1) keep every baseline input except $W_0$. The H − D ES95 differences, in pp, are {wealth}. At 100,000 SEK the threshold cannot be reached (the deficit is at most 70% of $W_0$) and at 200,000 SEK only the most extreme paths reach it; at both, harvesting raises ES95 by the same amount as in the counterfactual below. At 300,000 SEK it still raises ES95; between about 500,000 and 1,000,000 SEK it lowers ES95; at 2,000,000 SEK harvesting raises ES95 again, consistent with the bounded extra relief being small relative to $W_0$. In the counterfactual without the threshold, the difference at 500,000 SEK is {pp(f(cf,"delta_es95"))} pp [{pp(f(cf,"delta_es_ci_low"))}, {pp(f(cf,"delta_es_ci_high"))}]. Removing the threshold changes the mean difference only from {pp(f(hd,"delta_mean"))} to {pp(f(cf,"delta_mean"))} pp.')
    para(f'<b>Reinvestment timing.</b> The settlement lag decides how much of the year-1 credit is exposed to year-2 price risk. With lag 0 the credit is invested at month 12, with lag 6 at month 18, and with lag 12 it arrives at month 24 and stays in cash. The H − D ES95 difference is {pp(f(by_id["sweden_lag0"],"delta_es95"))}, {pp(f(by_id["baseline_sweden_lag6"],"delta_es95"))} and {pp(f(by_id["sweden_lag12"],"delta_es95"))} pp for these lags, which is consistent with more exposure producing a larger tail loss. With zero tax-reduction capacity the difference is {pp(f(by_id["no_credit_capacity"],"delta_es95"))} pp.', 9.4)
    para('These experiments show that, in this model, the favorable baseline ES95 difference depends on the annual deficit threshold together with W<sub>0</sub>, and that reinvestment timing also moves the tail result. They do not separate every channel, and they are pointwise, model-conditional comparisons.', 9.4,
         md_text='These experiments show that, in this model, the favorable baseline ES95 difference depends on the annual deficit threshold together with $W_0$, and that reinvestment timing also moves the tail result. They do not separate every channel, and they are pointwise, model-conditional comparisons.')

    # Page 5
    page('Accounting, interpretation and references')
    para('<b>Cash accounting.</b> Signed tax T<sub>y</sub> is positive for an amount owed and negative for a credit; assessment and payment are separate events. If a bill exceeds everything in the account, the investor pays the remainder from outside the account; this external funding F is recorded separately, never invested, and trading stops. With price P&amp;L the sum over months of shares held times the price change,',
         9.4, md_text='**Cash accounting.** Signed tax $T_y$ is positive for an amount owed and negative for a credit; assessment and payment are separate events. If a bill exceeds everything in the account, the investor pays the remainder from outside the account; this external funding $F$ is recorded separately, never invested, and trading stops. With price P&L the sum over months of shares held times the price change,')
    para('W = W<sub>0</sub> + price P&amp;L − fees − Σ<sub>y</sub>T<sub>y</sub> = bank − F,', 10.1,
         md_text='$$W = W_0 + \\text{price P\\&L} - \\text{fees} - \\sum_y T_y = \\text{bank} - F,$$')
    para('where bank is the cash held after the account is closed and all taxes are settled. A deterministic ISK example with strictly positive prices ends with W = −1,130 SEK and F = 1,130 SEK, because the ISK tax is based on earlier, higher account values. No simulated path needed external funding (0 of 20,000 per strategy and configuration; approximate one-sided 95% upper bound 3/N = 0.015%).', 9.4)
    residual = resource['maximum_absolute_residual_sek']
    para(f'<b>Computational checks.</b> {counts["unit_examples_passed"]} unit examples and {counts["full_path_examples_passed"]} full-path examples are compared with values worked out by hand in docs/MATHEMATICAL_MODEL.md; these are the independent reference checks. A scalar engine and a vectorized engine implement the monthly state transitions separately (they share the tax functions) and agree on {sv["checked_paths"]:,} cases. All {counts["primary_strategy_path_outcomes"]:,} primary outcomes satisfy the accounting identity; the largest residual in this run ({environment_label()}) was {residual:.2e} SEK, and residuals of this size vary across platforms. Price moments and an independent baseline seed pass their checks.', 9.4)
    para(f'<b>Statistical interpretation.</b> Each of the {draws:,} bootstrap draws resamples complete paths, with one index matrix for every strategy and configuration, and recomputes both strategies’ means and ES95 values [P4]. The intervals are pointwise and conditional on each model; they do not cover parameter, return-model or tax-law uncertainty and are not simultaneous across comparisons. Mean and ES95 exist because every outcome is a finite piecewise-linear function of lognormal prices and price ratios with finite moments. Utility rankings are not calculated: CRRA utility needs positive wealth, and CARA utility needs an integrability argument (docs/MATHEMATICAL_MODEL.md).', 9.4)
    para('<b>Limitations.</b> Returns are illustrative and uncalibrated. The policies are fixed, the horizon is two years with a forced sale at month 24, the investor is assumed to have adequate tax-reduction capacity and an unused ISK allowance, and both years use the 2026 rules. Immediate sale and repurchase are assumed to be distinct recognized transactions at the modelled price; their treatment under Supreme Administrative Court (HFD) case law was not examined. The results identify no universally better account or optimal policy [P1–P3].', 9.4)
    heading('References')
    for label, text, url in REFERENCES:
        para(f'<b>[{label}]</b> <a href="{url}">{text}</a>', 8.3)
    para('Reproduction: Python 3.13.5 with requirements-lock.txt, then <b>python reproduce.py</b>; see README.md.', 8.8)
    n.finish()

    # Appendix
    a = Note(out/'note/research_appendix.pdf', APPENDIX_PAGES, title=f'{TITLE} (appendix)')
    a.new_page('Appendix: return models and baseline contrasts', footer)
    a.paragraph(f'{AUTHOR} | {REVISION_DATE}')
    cap4 = (f'Figure 4. Mean return and ES95 for nine illustrative return models (m, σ), all other inputs at baseline, using the same {N:,} innovations. '
            'Hollow squares (depå hold) and small triangles (depå harvest) nearly coincide because their differences are a fraction of a percentage point; tables/contrasts.csv gives them with intervals.')
    a.picture(out/'figures/figure4_return_models.png', 330)
    a.paragraph(cap4, 9.2)
    names = {'harvest_minus_hold': 'H − D', 'harvest_minus_isk': 'H − I', 'hold_minus_isk': 'D − I'}
    contrast_table = [['Baseline contrast', 'Mean difference, pp [MC interval]', 'ES95 difference, pp [MC interval]'],
        *[[names[r['contrast']], fmt_interval(r, 'delta_mean', 'delta_mean_ci_low', 'delta_mean_ci_high'),
           fmt_interval(r, 'delta_es95', 'delta_es_ci_low', 'delta_es_ci_high')] for r in deltas]]
    a.table(contrast_table, [96, 206, a.w - 302], 9)
    es_pdf = ('<b>Expected shortfall.</b> For an integrable loss L, ES95 = min<sub>v</sub> {v + E[(L − v)<super>+</super>]/0.05} [P4]. '
              f'With N = {N:,} equally weighted paths the estimator averages exactly the worst 5% of the sample, i.e. the largest {int(round(.05*N)):,} losses; '
              'ties are kept, and a fractional boundary observation is used when 0.05N is not an integer. A difference of two ES95 values is not the ES95 of the paired differences.')
    a.paragraph(es_pdf, 9.3)
    a.finish()

    n_tex = f'{N:,}'.replace(',', '{,}')
    md_es = ('**Expected shortfall.** For an integrable loss $L$, $\\mathrm{ES}_{95} = \\min_v \\{v + E[(L-v)^+]/0.05\\}$ [P4]. '
             f'With $N = {n_tex}$ equally weighted paths the estimator averages exactly the worst 5% of the sample, i.e. the largest {int(round(.05*N)):,} losses; '
             'ties are kept, and a fractional boundary observation is used when $0.05N$ is not an integer. A difference of two ES95 values is not the ES95 of the paired differences.')
    md.extend(['## Appendix: return models and baseline contrasts',
        f'![Figure 4: mean return and ES95 under nine return models](../figures/figure4_return_models.png)\n\n*{markdown(cap4)}* ([PDF version](../figures/figure4_return_models.pdf))',
        '\n'.join(['| ' + ' | '.join(contrast_table[0]) + ' |', '| --- | --- | --- |', *['| ' + ' | '.join(r) + ' |' for r in contrast_table[1:]]]),
        md_es,
        '## Complete tables',
        (out/'tables/table1_baseline.md').read_text().replace('# Table 1.', '### Table 1 (complete).').strip(),
        (out/'tables/table2_sensitivity.md').read_text().replace('# Table 2.', '### Table 2 (complete).').strip(),
        (out/'supplementary/table_s1_wealth_threshold.md').read_text().replace('# Table S1.', '### Table S1.').strip(),
        'All results: [strategy metrics](../tables/scenario_metrics.csv), [contrasts](../tables/contrasts.csv), '
        '[supplementary metrics](../supplementary/supplementary_metrics.csv) and [supplementary contrasts](../supplementary/supplementary_contrasts.csv). '
        'PDF versions: [research note](research_note.pdf) and [appendix](research_appendix.pdf). '
        'Further detail: [methodology](../../docs/METHODOLOGY.md), [mathematical model](../../docs/MATHEMATICAL_MODEL.md), '
        '[implementation](../../docs/IMPLEMENTATION.md) and [sources](../../docs/SOURCES.md).'])
    (out/'note/research_note.md').write_text('\n\n'.join(md) + '\n')
