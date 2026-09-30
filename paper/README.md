# IEEE IoT Journal manuscripts

## E-LQTP (primary)

[`main.tex`](main.tex) is the driver. Every section is a separate
`.tex` file; [`elqtp.tex`](elqtp.tex) is an alias of the same
inputs. Layout follows LQARP *IEEE Internet of Things Journal*:

| Section | File | Content |
| --- | --- | --- |
| Authors | `authors.tex` | Xuefei Ma (first); Ghulam Ali (corresponding) |
| Abstract | `abstract.tex` | Validated point: trigger on, $\beta_1=\beta_2=0$ |
| I Introduction | `sec1_introduction.tex` | Related work, contributions, organization |
| II Preliminaries | `sec2_preliminaries.tex` | Architecture, Bellhop/LQARP channel, Q-learning, estimation gap |
| III Design | `sec3_design.tex` | Dual-track EKF, trigger, reward, Algorithm 1 |
| IV Evaluation | `sec4_evaluation.tex` plus `sec4a`--`sec4g` | Setup, metrics, Scenarios I--III, ablation, discussion |
| V Conclusion | `sec5_conclusion.tex` | Control-plane gain; scoped negative reward result |
| Bibliography | `refs.bib` | $\ge 40$ journal articles, year $\ge 2023$, no conferences, no MDPI |

Do not merge with [`iotj_et_hold.tex`](iotj_et_hold.tex) (unrelated ETHA draft).

### Build the PDF

```bash
sudo apt-get install -y texlive-latex-base texlive-publishers \
  texlive-fonts-recommended texlive-latex-extra texlive-science

cd paper
make            # main.pdf (also copied to elqtp.pdf)
make figures    # regenerate elqtp_figs/
make iotj       # ETHA draft only
```

`IEEEtran.cls` and `IEEEtran.bst` are required. Compile from this
directory so `\includegraphics{elqtp_figs/...}` resolves.

### Figures (captions live in `elqtp_fig*.tex`, not on the artwork)

Figure numbers follow first appearance in the PDF (IEEE order):

| File | PDF Fig. | Section | Content |
| --- | --- | --- | --- |
| `elqtp_figs/fig1_network_architecture.*` | 1 | II-A | Architecture: shared current and Rankine eddy |
| `elqtp_figs/fig_mechanism.*` | 2 | III | Themed Sense–Forward blocks: dual-track EKF, rising-edge HELLO, Q-learning |
| `elqtp_figs/fig7_trigger_trace.*` | 3 | III-B | Dual-track trigger trace on a representative Scenario III pair |
| `elqtp_figs/fig2_mobility_fields.*` | 4 | IV-A | $N=40$ velocity fields |
| `elqtp_figs/fig3_scenario2_protocols.*` | 5 | IV-D | Scenario II hops / delay / $O_{\mathrm{ctrl}}$ |
| `elqtp_figs/fig4_scenario2_drift.*` | 6 | IV-D | Scenario II vs.\ drift magnitude |
| `elqtp_figs/fig5_scenario3_protocols.*` | 7 | IV-E | Scenario III hops / delay / $O_{\mathrm{ctrl}}$ |
| `elqtp_figs/fig6_reward_ablation.*` | 8 | IV-F | $\beta_1$, $\beta_2$ sweeps |

Rebuild:

```bash
python3 fig_mechanism.py
python3 fig2_mobility_fields.py
python3 fig_results.py
python3 fig7_trigger_trace.py
```

### Reported results

- Scenario I ($N=40$, $1600\,\mathrm{s}$, identity): E-LQTP bit-identical to LQARP, $O_{\mathrm{ctrl}}=0$; Fixed-Periodic $442.03\,\mathrm{byte/s}$.
- Scenario II ($v=2\,\mathrm{m/s}$): data plane $=$ LQARP; $O_{\mathrm{ctrl}}=135\pm 23$ vs $413.42$ ($0.33\times$).
- Scenario III (eddy $2\,\mathrm{m/s}$): hops $1.002\times$ LQARP; $O_{\mathrm{ctrl}}=211\pm 34$ ($0.51\times$).
- Reward terms: no tested $(\beta_1,\beta_2)$ improves LQARP; validated default is $(0,0)$.
