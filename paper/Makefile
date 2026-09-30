# IEEE Internet of Things Journal manuscripts
#
# Primary target is main.tex (section files + refs.bib):
#   make            # or: make main
#   make iotj       # unrelated prior ETHA draft; do not merge
#
# Bibliography: refs.bib + IEEEtran.bst (texlive-publishers).

LATEX ?= pdflatex
BIBTEX ?= bibtex

MAIN  = main
HOLD  = iotj_et_hold

.PHONY: all main elqtp iotj clean figures

all: $(MAIN).pdf

main: $(MAIN).pdf

elqtp: $(MAIN).pdf
	cp -f $(MAIN).pdf elqtp.pdf

iotj: $(HOLD).pdf

figures:
	python3 fig_mechanism.py
	python3 fig2_mobility_fields.py
	python3 fig_results.py
	python3 fig7_trigger_trace.py

SECTIONS = abstract.tex keywords.tex ntp.tex authors.tex \
	sec1_introduction.tex sec2_preliminaries.tex sec3_design.tex \
	sec4_evaluation.tex sec4a_setup.tex sec4b_metrics.tex \
	sec4c_scenario1.tex sec4d_scenario2.tex sec4e_scenario3.tex \
	sec4f_ablation.tex sec4g_discussion.tex sec5_conclusion.tex \
	refs.bib \
	elqtp_fig1.tex elqtp_fig_mech.tex elqtp_fig2.tex elqtp_fig3.tex elqtp_fig4.tex \
	elqtp_fig5.tex elqtp_fig6.tex elqtp_fig7.tex \
	elqtp_table_params.tex elqtp_table_beta.tex \
	elqtp_table_s1.tex elqtp_table_s2_protocols.tex \
	elqtp_table_s2_drift.tex elqtp_table_s3_protocols.tex

$(MAIN).pdf: $(MAIN).tex $(SECTIONS)
	$(LATEX) -interaction=nonstopmode $(MAIN)
	-$(BIBTEX) $(MAIN)
	$(LATEX) -interaction=nonstopmode $(MAIN)
	$(LATEX) -interaction=nonstopmode $(MAIN)
	cp -f $(MAIN).pdf elqtp.pdf

$(HOLD).pdf: $(HOLD).tex
	$(LATEX) -interaction=nonstopmode $(HOLD)
	$(LATEX) -interaction=nonstopmode $(HOLD)

clean:
	rm -f $(MAIN).aux $(MAIN).log $(MAIN).out $(MAIN).blg \
		$(MAIN).bbl $(MAIN).pdf
	rm -f elqtp.aux elqtp.log elqtp.out elqtp.blg elqtp.bbl
	rm -f $(HOLD).aux $(HOLD).log $(HOLD).out $(HOLD).blg \
		$(HOLD).bbl $(HOLD).pdf
