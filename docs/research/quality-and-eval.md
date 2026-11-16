# Research: code-quality levers and eval rigor

Scope: what the evidence says improves maintainability, and how to measure it more rigorously than
the current benchmark (8 single-file Exercism tasks, n = 16 runs per arm, see README "Evaluation").
Gating and process control are out of scope. Sources were checked against the venue, the author
page, or the official docs (November 2026). Power numbers come from `results/bench/v2.1`.

## A. Code quality

### A1. Comments and docstrings

**Finding.** Nurvitadhi et al. ran a controlled experiment with 103 students and found that method
comments improved low-level understanding, while class comments did not improve high-level
understanding. Woodfield et al. tested 48 programmers on 8 program versions with and without
comments. The abstract reports that modularization around abstract data types worked best; the size
of the comment effect could not be checked from the abstract. None of this evidence favors comment
*density*. The quality literature treats
coherence with the code as the main attribute. Code-comment inconsistency, where code changes and
the comment does not, is common and well studied. Most of these studies are Java-only and rely on
student raters.

**Sources.**
- Woodfield, Dunsmore, Shen, "The Effect of Modularization and Comments on Program Comprehension", ICSE 1981, pp. 215–223. https://bibtex.github.io/ICSE-1981-WoodfieldDS.html
- Nurvitadhi, Leung, Cook, "Do class comments aid Java program understanding?", FIE 2003. doi:10.1109/FIE.2003.1263332
- Steidl, Hummel, Jürgens, "Quality analysis of source code comments", ICPC 2013 (criteria: consistency, completeness, coherence, usefulness). doi:10.1109/ICPC.2013.6613836
- Wen, Nagy, Bavota, Lanza, "A Large-Scale Empirical Study on Code-Comment Inconsistencies", ICPC 2019. doi:10.1109/ICPC.2019.00019
- Rani et al., "A decade of code comment quality assessment: A systematic literature review", JSS 195, 2023. doi:10.1016/j.jss.2022.111515
- Tools: ruff pydocstyle rules D100–D107 (https://docs.astral.sh/ruff/rules/#pydocstyle-d); interrogate, which measures docstring coverage (https://github.com/econchick/interrogate, MIT).

**Confidence.** Medium. The direction is consistent, but the studies are old, small, and mostly Java.

**Apply here.** Stop treating comment ratio as a target. Measure public-API docstring coverage
(`ruff --select D1` or interrogate), and ask the judge to rate whether each comment says *why* and
matches the code.

### A2. Design-level metrics (coupling and cohesion)

**Finding.** The CK metrics, coupling (CBO) among them, predicted fault-proneness in early
validations. El Emam et al. showed that after controlling for class size, none of the metrics they
studied stayed associated with faults. Change coupling, meaning files that change together in git,
correlates with defects. Sjøberg et al. measured actual maintenance effort and found that none of 12
code smells increased effort after adjusting for file size and number of changes. Size is the
confound to control for in every comparison.

**Sources.**
- Basili, Briand, Melo, "A Validation of Object-Oriented Design Metrics as Quality Indicators", IEEE TSE 22(10), 1996. doi:10.1109/32.544352
- El Emam, Benlarbi, Goel, Rai, "The Confounding Effect of Class Size on the Validity of Object-Oriented Metrics", IEEE TSE 27(7), 2001. doi:10.1109/32.935855
- D'Ambros, Lanza, Robbes, "On the Relationship Between Change Coupling and Software Defects", WCRE 2009. doi:10.1109/WCRE.2009.19
- Sjøberg, Yamashita, Anda, Mockus, Dybå, "Quantifying the Effect of Code Smells on Maintenance Effort", IEEE TSE 39(8), 2013. doi:10.1109/TSE.2012.89
- Python tools: `cohesion` (class cohesion, flake8 plugin, GPL-3.0) https://github.com/mschwager/cohesion; `lcom` (LCOM4) https://pypi.org/project/lcom; `module-coupling-metrics` (instability and abstractness, v0.0.1, AGPL-3.0) https://github.com/Oaz/module_coupling_metrics; code-maat (git change coupling) https://github.com/adamtornhill/code-maat.

**Confidence.** High that size confounds these metrics. Medium for change coupling. Low for the
maturity of the Python tooling.

**Apply here.** In multi-file tasks, report coupling and LCOM next to SLOC, and test the arm
difference with size as a covariate.

### A3. Static typing

**Finding.** Gao et al. found that about 15% of public JavaScript bugs (95% CI 11.5–18.5%) would
have been caught by Flow or TypeScript. Khan et al. estimate that mypy could have prevented 15% of
defects in 210 Python projects, and call that a lower bound. Both studies measure *detectable*
bugs. Neither shows that annotating code reduces defects in practice.

**Sources.**
- Gao, Bird, Barr, "To Type or Not to Type: Quantifying Detectable Bugs in JavaScript", ICSE 2017, pp. 758–769. doi:10.1109/ICSE.2017.75
- Khan, Chen, Varró, McIntosh, "An Empirical Study of Type-Related Defects in Python Projects", IEEE TSE 48(8), 2022. https://rebels.cs.uwaterloo.ca/papers/tse2021_khan.pdf

**Confidence.** High for the 15% detectability figure. Low for any effect on maintenance.

**Apply here.** Add `mypy --strict` error count and annotation coverage (ruff `ANN`) as metrics
before writing any typing rule, so that a rule can be judged by its effect on those numbers.

### A4. Mutation testing

**Finding.** Just et al. found that mutant detection correlates with real-fault detection
independently of coverage (357 real faults; 73% coupled to mutants). Papadakis et al. found that
the correlation becomes weak once suite size is controlled. Suites selected by mutation score still
detected significantly more faults than random suites of the same size. Mutation score is therefore
a good guide for improving tests and a weak absolute measure. At Google, mutants are restricted to
covered, changed lines to keep the cost manageable.

**Sources.**
- Just, Jalali, Inozemtseva, Ernst, Holmes, Fraser, "Are Mutants a Valid Substitute for Real Faults in Software Testing?", FSE 2014. https://homes.cs.washington.edu/~mernst/pubs/mutation-effectiveness-fse2014.pdf
- Papadakis, Shin, Yoo, Bae, "Are Mutation Scores Correlated with Real Fault Detection?", ICSE 2018. doi:10.1145/3180155.3180183
- Petrović, Ivanković, "State of Mutation Testing at Google", ICSE-SEIP 2018. doi:10.1145/3183519.3183521
- mutmut (BSD-3) requires `fork`, so on Windows it runs only inside WSL: https://github.com/boxed/mutmut. Cosmic Ray (MIT) supports distributed runs: https://cosmic-ray.readthedocs.io

**Confidence.** High.

**Apply here.** Only useful where the agent writes its own tests. Add a phase-2 step in which the
agent writes tests for its own change, then score them with mutmut in WSL. Each task is about
100 lines, so a run takes minutes.

### A5. Efficiency of LLM-generated code

**Finding.** LLM-written code is correct but slow. In EffiBench, GPT-4 code took on average 3.12
times as long to execute as the human canonical solutions. In Mercury, leading models score 65% on
Pass but below 50% on the efficiency-weighted Beyond metric. EvalPerf found that model scale does
not improve efficiency, while instruction tuning improves both correctness and efficiency. ECCO
tested interventions available at inference time: natural-language feedback gave the largest
efficiency gains, and execution feedback best preserved correctness.

**Sources.**
- Huang, Zhang, Qing, Cui, "EffiBench: Benchmarking the Efficiency of Automatically Generated Code", NeurIPS 2024. arXiv:2402.02037
- Du, Luu, Ji, Liu, Ng, "Mercury: A Code Efficiency Benchmark for Code LLMs", NeurIPS 2024 Datasets & Benchmarks. arXiv:2402.07844
- Liu et al., "Evaluating Language Models for Efficient Code Generation" (DPE / EvalPerf), COLM 2024. arXiv:2408.06450; https://github.com/evalplus/evalplus
- Waghjale, Veerendranath, Wang, Fried, "ECCO: Can We Improve Model-Generated Code Efficiency Without Sacrificing Functional Correctness?", EMNLP 2024. doi:10.18653/v1/2024.emnlp-main.859

**Confidence.** High that the gap exists. Medium on which interventions close it.

**Apply here.** `runtime_ms` on Exercism tests measures noise. If efficiency matters, run the
EvalPerf tasks with their performance-exercising inputs as a separate arm.

## B. Eval rigor

### B1. Sample size and statistical power

**Finding.** Miller recommends clustered standard errors, paired per-question differences, and a
power analysis before running an eval. Bowyer et al. show that CLT-based intervals are too narrow
below a few hundred items, and recommend Bayesian or exact methods (`bayes_evals`).

The `results/bench/v2.1` data show three things:

- **Tasks are the unit that matters.** Between-task variance accounts for 66–90% of total variance
  in cognitive complexity, max CC, and lint severity, so adding tasks reduces error far more than
  adding runs.
- **The current design is at its floor.** A sign-flip test over 8 tasks cannot produce a two-sided
  p below 2/256 ≈ 0.008, and the 0.009 values in the README are at that floor.
- **Required tasks per effect size.** For 80% power at α = 0.05 (paired, normal approximation, from
  observed per-task SDs):

| Metric | Tasks needed, 30% effect | Tasks needed, 20% effect |
|---|---|---|
| Tokens | 9 | 17 |
| Max CC | 15 | 31 |
| Cognitive complexity | 17 | 37 |
| Cost | 18 | 37 |
| Halstead volume | 47 | 103 |
| Lint severity | 66 | 146 |

**Sources.**
- Miller, "Adding Error Bars to Evals: A Statistical Approach to Language Model Evaluations", arXiv:2411.00640, 2024.
- Bowyer, Aitchison, Ivanova, "Position: Don't Use the CLT in LLM Evals With Fewer Than a Few Hundred Datapoints", ICML 2025, PMLR 267. https://proceedings.mlr.press/v267/bowyer25a.html

**Confidence.** High for the method. Medium for the n values, which come from one version's
variance.

**Apply here.** Move to about 32 tasks × 1 run, keeping the pairing, and report bootstrap or
exact-permutation CIs alongside p.

### B2. Multi-file and repo-scale benchmarks

**Finding.**
- **SWE-bench / Verified:** the harness requires Docker, x86_64, 120 GB of disk, 16 GB of RAM, and
  8 or more cores. The docs do not mention Windows. Evaluation can run in the cloud through
  `--modal true` or sb-cli on AWS. MIT license.
- **Aider Polyglot:** 225 hard Exercism exercises in 6 languages. It is meant to run inside Docker
  for safety. The aider repo is Apache-2.0. The exercise repo shows no license on GitHub, though
  the Exercism tracks are MIT. It is still mostly single-file.
- **SWE-EVO:** 48 release-level tasks averaging 21 files each. Too hard and too costly for an A/B.

**Sources.**
- Jimenez et al., "SWE-bench: Can Language Models Resolve Real-World GitHub Issues?", ICLR 2024. Harness docs: https://swebench.com/SWE-bench/reference/harness
- Aider benchmark README: https://github.com/Aider-AI/aider/blob/main/benchmark/README.md; https://aider.chat/2024/12/21/polyglot.html
- Le et al., "SWE-EVO", arXiv:2512.18470, 2025.

**Confidence.** High.

**Apply here.** Use SWE-bench Verified, about 30 instances, evaluated through Modal. That avoids
running Docker locally on Windows. Treat the Polyglot Python subset as a cheap step up in
difficulty, not as a multi-file benchmark.

### B3. Measuring maintainability by follow-up changes

**Finding.**
- **MaintainBench:** pairs requirement changes with dynamic maintenance-effort metrics. Its authors
  find that static metrics can contradict each other, while their dynamic metrics are consistent.
- **Regression accumulation:** over 8-turn change chains, 40–73% of tasks lose previously correct
  behavior. The changes that hurt most add input validation or broaden the accepted inputs.
  Checking each change against all prior tests was the only strategy that helped every model.
- **Sjøberg et al.:** effort tracks size and number of changes (see A2).

**Sources.**
- Wang et al., "MaintainCoder: Maintainable Code Generation Under Dynamic Requirements", NeurIPS 2025. arXiv:2503.24260; https://github.com/IAAR-Shanghai/MaintainCoder
- Huang et al., "Regression Accumulation in Multi-Turn LLM Programming Conversations", arXiv:2607.01855, 2026 (preprint).
- Sjøberg et al. 2013 (see A2).

**Confidence.** Medium. These are new benchmarks with one preprint.

**Apply here.** Replace the single follow-up with a chain of 3–5 changes that cut across the
design, and score regressions on prior tests plus cumulative tokens, not the pass rate alone.

### B4. LLM-as-judge for code

**Finding.**
- **Agreement with humans:** GPT-4 matched human preferences more than 80% of the time, the same
  level as human-human agreement. Zheng et al. also document position, verbosity, and self-preference
  (self-enhancement) biases.
- **Self-recognition:** judges recognize their own outputs, and the strength of self-preference
  rises with that ability.
- **CALM:** quantifies 12 bias types by perturbing the content being judged.
- **Code-specific results:**
  - Wang et al.: correlation with humans is 68.5 (Pearson) for code generation, and alignment varies
    by task.
  - Crupi et al.: even the best judge frequently misjudges code correctness and summary quality.
- **Mitigations:** order swapping (already in place), length control, a judge from a different model
  family, and calibration against a human-labelled sample using Cohen's κ.

**Sources.**
- Zheng et al., "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena", NeurIPS 2023 D&B. arXiv:2306.05685
- Panickssery, Bowman, Feng, "LLM Evaluators Recognize and Favor Their Own Generations", NeurIPS 2024.
- Ye et al., "Justice or Prejudice? Quantifying Biases in LLM-as-a-Judge", ICLR 2025. arXiv:2410.02736
- Wang et al., "Can LLMs Replace Human Evaluators? An Empirical Study of LLM-as-a-Judge in Software Engineering", ISSTA 2025. doi:10.1145/3728963
- Crupi et al., "On the Effectiveness of LLM-as-a-judge for Code Generation and Summarization", IEEE TSE 51(8), 2025. arXiv:2507.16587

**Confidence.** High that the biases exist. Medium on how large they are for code.

**Apply here.** Both arms come from the same model, so self-preference largely cancels. Verbosity
bias would favor the longer no-standards code, so the 12–1 result goes against that bias. The
missing step is human calibration: label 20 pairs and report κ.

## Ranked experiments

1. **More tasks, one run each.**
   - Change: grow to about 32 Exercism Python tasks, 1 run per arm, and keep the pairing.
   - Measure: the current metrics, with exact-permutation p and bootstrap CIs.
   - Cost: about 64 agent runs plus follow-ups, roughly $10–15 per variant.
   - Why first: it lifts the p-value floor and gives about 80% power for 30% effects on CC and
     cognitive complexity.
2. **Change chains in phase 2.**
   - Change: 3 sequential follow-ups per task. At least one adds input validation or broadens the
     accepted inputs.
   - Measure: prior-test regressions, cumulative tokens and turns, and CC after the last change.
   - Cost: about 3× the current phase 2, roughly $10 per variant.
   - Why: removes the 100% pass ceiling.
3. **Judge calibration.**
   - Change: a human labels 20 blinded pairs; the same pairs go to a second judge from another model
     family.
   - Measure: Cohen's κ between judge and human, and between the two judges; win rate with code
     length as a control.
   - Cost: about 2 hours of human time plus about $2.
4. **Comment quality instead of comment quantity.**
   - Change: replace the "docstrings on public APIs" variant with "explain *why*; docstring only
     where the contract is not obvious from the signature".
   - Measure: D1 coverage on public API, judge-rated comment coherence and usefulness, and the
     existing metrics.
   - Cost: one bench variant, about $5.
5. **Repo-scale check.**
   - Change: about 30 SWE-bench Verified instances, run by the agent locally and evaluated through
     Modal.
   - Measure: resolve rate, and coupling and LCOM with SLOC as a covariate.
   - Cost: about $30–60 of agent runs plus Modal credits, and about a day of setup.
