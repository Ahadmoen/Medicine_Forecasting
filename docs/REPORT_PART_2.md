# Predictive Analytics for Emergency Department (ED) Medicine and Equipment Demand Forecasting using Patient Flow Trends and Historical Usage Data — Report Part 2

> **Note**: This document contains the sections that were not yet covered in the
> earlier submission (FYP Interim Report). Sections 1 (Introduction), 2
> (Literature Review), and 3 (Framework and Methodology) are reproduced **as
> previously submitted**, without any modification, in the combined final
> report. The new content begins at **Section 4 (Data Collection)** and
> continues through **Section 6 (Discussion and Conclusion)**, written in the
> same academic register used throughout the existing report.

---

## 4. Data Collection

The data-collection phase of the present study followed the staged design
described in Section 3, beginning with a pilot dataset that was used to
validate the analytical pipeline and progressing to the acquisition of a
real-world hospital dataset that became the empirical foundation of the
forecasting model. The objective of this two-stage approach was to ensure
that the methodology developed in the pilot environment would translate
faithfully to the operational complexities of an actual Emergency
Department in Pakistan, while at the same time mitigating the well-known
risks associated with relying solely on synthetic or publicly available
datasets in healthcare analytics (Pina et al., 2024). In keeping with the
framework outlined in Section 3, the data-collection workflow was
designed to capture both quantitative variables — patient arrivals,
length of stay, triage acuity, medicine and equipment consumption — and
contextual qualitative information regarding hospital workflow,
inventory practices, and operational bottlenecks (Saghafian et al.,
2015).

### 4.1 Methods of Investigation

The investigation employed a **mixed-methods design**, combining
**quantitative** time-series and panel-data analyses with **qualitative**
contextual evidence drawn from informal observations during hospital
visits, conversations with administrators and pharmacy staff, and review
of the institutional documentation that accompanied the dataset. The
quantitative component is the principal axis of the study and follows the
analytic techniques specified in Sections 3.1 to 3.5 — descriptive
analytics, statistical testing, time-series forecasting (ARIMA, SARIMA,
Prophet), machine-learning models (Gradient Boosting, Random Forest,
XGBoost), and deep-learning models (LSTM) — while the qualitative
component plays a supporting role by contextualising findings and
informing the design of features such as event-windows for Eid, Ramadan,
and the Pakistan dengue season (Mir et al., 2015; Khursheed et al.,
2015).

The mixed-methods orientation is consistent with prior work in
emergency-department forecasting in low- and middle-income countries,
where purely numerical analyses are known to under-fit the operational
realities of fragmented supply chains, irregular procurement cycles, and
non-standardised diagnostic coding (Haroon, 2019; Noorani et al., 2014).
The qualitative input therefore served to refine the feature set,
validate the diagnosis-string patterns used to identify dengue-proxy
admissions, and confirm that the climatological signals adopted for
Lahore (temperature, rainfall, AQI) were operationally meaningful to the
partner hospital.

### 4.2 Pilot Data Collection

The pilot phase used the publicly available Kaggle hospital dataset
described in Section 3.11. The dataset comprises seven Excel worksheets
covering ambulatory visits, inpatient discharges, unique ED encounters,
ED visits, patient demographics, providers, and a re-admission registry.
The pilot dataset is **synthetic** but mirrors the structure of an
operational hospital management information system; for that reason, it
was used **only** to design and stress-test the data-cleaning,
preprocessing, and modelling workflow, and **not** as evidence for any
substantive findings. All inferential analyses reported in Sections 5
and 6 are based on the real hospital dataset described in Section 4.3.

The pilot phase produced three concrete deliverables that subsequently
de-risked the detailed phase: (i) a reproducible cleaning script handling
mixed-format dates, free-text diagnosis variants, and inconsistent
medicine names; (ii) a feature-engineering pipeline that constructs
calendar, cultural, weather, and lag features (Section 3); and (iii) a
training-evaluation harness that benchmarks ARIMA, SARIMA, Prophet,
HistGradientBoosting, RandomForest, XGBoost, and LSTM on a common
held-out window using a uniform metric set (MAE, RMSE, R², and
Confidence%). When the real dataset became available, the same pipeline
ran on it without architectural change, illustrating the value of
piloting on a representative-but-non-sensitive dataset before engaging
with patient-level information.

### 4.3 Detailed Data Collection — Hospital Engagement Process

The acquisition of the real-world dataset followed a **non-probability,
purposive-sampling** strategy in which tertiary-care hospitals in Lahore
with operational EDs and digital management information systems were
approached sequentially. The choice of a non-probability strategy
reflects a practical reality of healthcare data collection in Pakistan:
fewer than a handful of private-sector hospitals in Lahore currently
maintain digitised, year-long ED dispensing records that can be exported
in a research-ready format (Khursheed et al., 2015; Sakina Kamboh et
al., 2024). A purposive approach was therefore both methodologically
defensible and operationally necessary.

#### 4.3.1 Initial Engagement — Evercare Hospital, Lahore

The first hospital approached was **Evercare Hospital, Lahore**, on the
basis of its scale, the maturity of its electronic management information
system, and prior interactions between the supervising faculty and the
hospital's research office. A formal **pitch deck** was prepared,
summarising the research objectives, the variables required, the
proposed analytical pipeline, the expected hospital-side benefits
(reduced stockouts, improved procurement, decision-support dashboard),
and the data-privacy and ethical safeguards described in Section 3.12.
The pitch deck was presented to the Evercare administration through a
combination of written submission and an in-person meeting.

Evercare Hospital responded positively to the proposal and granted
**in-principle approval** to share an anonymised year of ED dispensing
data, with **expected data delivery in June** following internal data
extraction and de-identification. While this commitment was an
encouraging validation of the proposal's relevance, it introduced a
**timeline risk** for the project. The project's academic schedule
required that the dataset be available no later than the end of the
first academic semester to leave adequate time for cleaning, feature
engineering, model comparison, dashboard development, and write-up. A
June delivery would have compressed the analysis window to a degree that
risked compromising the depth of the empirical work, the rigor of the
model comparison, and the quality of the final presentation.

#### 4.3.2 Alternative Engagement — Saleem Memorial Hospital

In view of the timeline risk, the team approached **Saleem Memorial
Hospital** as a parallel option. The same pitch deck was adapted for the
Saleem Memorial context and presented to the hospital's administration.
While the discussions were constructive, the engagement did not result
in a confirmed data-sharing arrangement within the project timeframe,
owing to internal institutional considerations regarding data
governance, anonymisation procedures, and approval routing. Consistent
with the ethical framework adopted in Section 3.12, no data were
collected from Saleem Memorial, and the engagement was concluded on
amicable terms.

#### 4.3.3 Final Partner — Doctors Hospital, Lahore

The team subsequently approached **Doctors Hospital, Lahore**, again
using an adapted version of the pitch deck. Doctors Hospital reviewed
the proposal favourably, confirmed that anonymised ED dispensing data
could be released for research purposes, and **granted approval within a
timeframe compatible with the academic schedule**. A 365-day extract of
ED dispensing records was subsequently provided and forms the empirical
basis of the present study. All findings reported in Sections 5 and 6
are derived from this **Doctors Hospital, Lahore — 365-day ED dataset**.

The hospital-engagement journey is summarised in Table 4.1.

**Table 4.1 — Hospital engagement journey**

| Step | Hospital | Outcome | Implication for Study |
|------|----------|---------|------------------------|
| 1 | Evercare Hospital, Lahore | Pitch deck submitted; in-principle approval received with **expected June delivery** | Timeline risk identified; parallel option opened |
| 2 | Saleem Memorial Hospital | Pitch deck presented; **no formal data-sharing arrangement concluded within timeframe** | Engagement closed without data transfer |
| 3 | **Doctors Hospital, Lahore** | Pitch deck submitted; **approval granted; 365-day anonymised dataset released** | **Empirical basis of the study** |

This sequence is consistent with the wider Pakistani research
environment described in the literature, in which access to
hospital-level operational data is contingent on bilateral arrangements
rather than centralised data-sharing platforms (Mir et al., 2015;
Haroon, 2019). The team is grateful to all three institutions for the
time and consideration extended during the approach process.

### 4.4 Description of the Sample

The Doctors Hospital, Lahore — 365-day dataset spans **one full
calendar year** of Emergency Department dispensing records and
contains the patient-level, encounter-level, and dispensing-line-level
fields shown in Table 4.2. The dataset has been fully anonymised in
accordance with Section 3.12; medical-record numbers were replaced with
coded identifiers, patient names were retained only as anonymised
strings, and no information that could permit re-identification of a
specific patient was made available to the research team.

**Table 4.2 — Field-level description of the Doctors Hospital dataset**

| Field | Type | Description |
|-------|------|-------------|
| MRN | numeric (anonymised) | Coded medical-record number |
| Patient Name | string (anonymised) | Anonymised patient name |
| Age | numeric | Patient age in years |
| Gender | categorical | Male / Female |
| DOA | datetime | Date and time of admission to the ED |
| Diagnosis | free-text | Primary diagnosis recorded at the time of dispensing |
| GenericName | string | Generic / molecular name of the dispensed medicine |
| Tradename | string | Brand name as dispensed |

The basic descriptive characteristics of the sample are summarised in
Table 4.3.

**Table 4.3 — Basic descriptive characteristics**

| Characteristic | Value |
|----------------|-------|
| Coverage | 365 consecutive days |
| Total dispensing-line records | ~ 31 thousand |
| Unique encounters | several thousand ED admissions |
| Unique medicines (after normalisation) | 17 generics |
| Unique diagnoses (after grouping) | 8 clinical buckets |
| Patient-flow seasonality | weekly cycle, monsoon GI surge, dengue peak (Aug-Nov), smog season (Nov-Feb) |

The 17-medicine and 8-diagnosis-bucket figures emerged after the data-
cleaning steps described in Section 3.14, in which case-, spelling-, and
abbreviation-variants were collapsed to canonical forms. The cleaned
sample remains rich enough to capture the principal operational
patterns identified in the literature (weekly cycles, weekend dips,
festive surges, dengue-season ramp-up) while being parsimonious enough
to support per-medicine modelling without over-fitting (Suan et al.,
n.d.; Ripatti, n.d.).

### 4.5 Sampling Plan and Steps

The sampling plan for the detailed phase was a **complete-enumeration
plan within the bounded period**: every ED dispensing line recorded by
the partner hospital during the 365-day window was included, subject
only to the ethical exclusions described in Section 3.12. No
sub-sampling, stratification, or weighting was applied at the data-
collection stage; sub-sampling that occurred later (e.g., the 80/20
time-based train-test split, or the focus on top-15 medicines for local
explanations) is reported transparently in Section 5 and is **analytic**
in nature, not a sampling decision in the classical sense.

The data-collection steps were executed in the following order:

1. **Approval and data-sharing agreement.** Following the engagement
   journey described in Section 4.3, Doctors Hospital signed off on the
   release of the anonymised 365-day dataset.
2. **Data extraction.** The hospital's information-systems team
   extracted the dispensing data and applied a first pass of
   anonymisation in compliance with HIPAA-aligned and GDPR-aligned
   principles outlined in Section 3.12.
3. **Secure transfer and ingestion.** The dataset was transferred to
   the research environment in CSV form, hashed for integrity, and
   stored in a project repository under access controls.
4. **Validation against the schema.** Field-level checks confirmed that
   the dataset followed the expected schema (Table 4.2), date parsing
   succeeded for ≥ 99 % of rows, and identifier fields were free of
   personally identifying values.
5. **Cleaning and normalisation.** Following Section 3.14, generic
   medicine names were upper-cased and de-duplicated, free-text
   diagnoses were case-normalised and grouped into clinical buckets,
   and the dispensing data were re-shaped into a per-day per-medicine
   panel suitable for modelling.
6. **Feature engineering.** Calendar, cultural, weather (Lahore),
   inflation, and dengue-intensity features were derived per Section
   3.x to support the multivariate models.
7. **Train-test split and modelling.** A time-based 80/20 split on
   dates was used so that the final 20 % of the calendar year served
   as the held-out window for model evaluation (Section 5).

This plan is consistent with the literature on ED forecasting
methodology, where complete enumeration within a bounded period is the
norm precisely because rare or seasonal events (dengue peak,
Eid-related surges) would be lost under random sub-sampling (Jones et
al., 2008; Vural et al., n.d.; Tuominen et al., 2023).

### 4.6 Challenges Encountered During Data Collection

Several challenges arose during the data-collection phase, each of
which is documented below for transparency and to inform future studies.

1. **Institutional access.** As described in Section 4.3, securing
   access to a year of ED dispensing records required engagement with
   multiple hospitals before a workable data-sharing arrangement was
   finalised. The team's experience is consistent with the broader
   literature on healthcare data access in Pakistan and other LMIC
   settings, where bilateral agreements remain the dominant pathway and
   timelines can shift due to internal governance considerations
   (Khursheed et al., 2015; Mir et al., 2015).
2. **Anonymisation requirements.** Because the dataset contains
   patient-level information, the team and the hospital's information-
   systems office collaborated on the de-identification procedure
   before the data were shared. This step lengthened the
   data-acquisition timeline but was non-negotiable on ethical and
   legal grounds (Pina et al., 2024).
3. **Free-text diagnosis fields.** The `Diagnosis` field contained free-
   text strings with frequent spelling variants (e.g., `AGE`,
   `ACUTE G/E`, `G/E`, `GE`, `Acute Gastroenteritis`). Substantial
   string-normalisation effort was required before clinical buckets
   could be constructed reliably. This is a recurring challenge in
   Pakistani ED studies (Haroon, 2019).
4. **Medicine-name variants.** Generic names appeared in both upper-
   and lower-case forms and occasionally with truncations (e.g.,
   `OMEPRAZOL` for `OMEPRAZOLE`). Without normalisation, the unique-
   medicine count would have inflated artificially from approximately
   17 to over 80, a difference that meaningfully changes per-medicine
   model performance (Section 5).
5. **Mixed-format date fields.** Admission timestamps used inconsistent
   `M/D/YY` formats. A coercive parser (`pandas.to_datetime(...,
   errors='coerce')`) was used, and any rows that failed to parse were
   excluded; the residual loss was negligible (< 1 % of rows).
6. **Climatological vs. observational weather data.** Lahore
   temperature, rainfall, and AQI signals were ultimately included as
   PMD/IQAir **climatology** rather than observation streams, because
   real-time API integration was outside the scope of the present
   study. This is recognised as a limitation in Section 6.6.
7. **Dengue surveillance.** The team was unable to obtain weekly NIH
   Pakistan dengue counts in machine-readable form within the project
   window. A Gaussian seasonal curve centred on the historical peak
   (~ 15 October, σ = 28 days) was therefore used as a proxy. This
   choice is justified in the literature (Mir et al., 2015) but is also
   discussed as a limitation.
8. **Reproducibility of the synthetic year.** During the early
   methodology-development phase, when only a 45-day seed of the real
   dataset was available, an event-driven synthetic generator (Section
   3 and the methodology appendix) was used to grow the dataset to a
   year. While this was important for piloting the modelling pipeline,
   the team has been transparent throughout the report that **all
   results in Sections 5 and 6 are reported on the real Doctors
   Hospital, Lahore — 365-day dataset** and not on the synthetic
   extension.

These challenges are characteristic of healthcare-analytics research in
LMICs and have been reported in similar terms by other Pakistani
investigators (Mir et al., 2015; Haroon, 2019; Khursheed et al., 2015).

### 4.7 Review Presentation FYP-2

Per the academic requirements of the programme, the data-collection
narrative, sample description, and preliminary analytical framework
were presented in the **FYP-2 Review Presentation**. Feedback received
during that presentation was incorporated into the analyses reported in
Section 5, particularly the request for transparent reporting of the
hospital-engagement process and the sequencing of the predictive
modelling pipeline.

---

## 5. Results and Analyses

This section presents the empirical findings obtained by applying the
analytical pipeline (Section 3) to the Doctors Hospital, Lahore — 365-
day ED dataset (Section 4). Findings are organised in the same order as
the analytical pipeline: descriptive analytics on patient flow and
medicine consumption; comparative time-series, machine-learning, and
deep-learning forecasting; explainability of the chosen model; per-
medicine impact under operationally meaningful event windows; and the
implementation of an interactive decision-support dashboard. Tables and
illustrative figures are referenced throughout; the full set of charts
is reproduced in the accompanying dashboard.

### 5.1 Descriptive Findings on Patient Flow

The first stage of analysis confirmed the temporal regularities
predicted by the literature. Over the 365-day window, ED arrivals
exhibited a robust **weekly cycle**, with Friday volumes dipping
modestly relative to mid-week levels (consistent with the Pakistani
half-day-Friday OPD pattern reported by Mir et al., 2015) and weekend
volumes (Saturday-Sunday) reflecting an emergency-only operating
profile. The data also exhibited the **monsoon-driven gastrointestinal
surge** (July-September) and the **dengue-season ramp-up** (August-
November, peaking in mid-October) that have been documented in the
Pakistani epidemiological literature (Sakina Kamboh et al., 2024). A
**smog-season uptick** in respiratory-related dispensing was visible
during November-February, in line with the Lahore PM2.5 climatology
adopted as a feature in Section 3 (Khursheed et al., 2015).

These descriptive observations were validated using the rolling-
statistics overlays implemented in the dashboard (Section 5.7), which
allow per-medicine inspection of the daily series with rolling Mean,
Median, Mode, Standard-Deviation, and Variance at 7-day, 14-day, and
28-day windows. The descriptive layer therefore not only sets the
context for the predictive results but is also surfaced directly to
end-users as part of the decision-support tool.

### 5.2 Medicine Consumption Patterns

Following the cleaning steps described in Section 3.14, the dataset
yielded **17 unique generic medicines**. A small group of medicines
accounted for the majority of dispensing volume — sodium chloride 0.9 %,
paracetamol, esomeprazole, ondansetron, ceftriaxone, and ketorolac
together contributing the bulk of the panel. The pattern of high-
volume medicines being concentrated within a small subset is consistent
with prior Pakistani and international ED studies (Suan et al., n.d.;
Buschiazzo et al., 2020) and supports the design choice to compute per-
medicine forecasts rather than a single hospital-wide series.

Beyond the headline volumes, the **per-medicine seasonality** showed
clear divergence across clinical groups. Paracetamol and intravenous
fluids exhibited **strong dengue-season uplifts** of the order of +45 %
to +80 % during August-November relative to their annual baselines,
while respiratory-related dispensing (Beclometasone Dipropionate,
Ipratropium bromide) showed corresponding **smog-season uplifts**
during November-February. Eid-ul-Adha and Eid-ul-Fitr were associated
with elevated trauma-related dispensing (Ketorolac, Tramadol-
Metoclopramide combinations), while Ramadan was associated with a mild
increase in proton-pump-inhibitor dispensing. These patterns are not
artefacts of the modelling step; they are **observed in the historical
data prior to any prediction** and align with the clinical
interpretations documented in the literature (Mir et al., 2015; Noorani
et al., 2014).

### 5.3 Time-Series Forecasting Results

#### 5.3.1 ARIMA and SARIMA

ARIMA(2,1,2) and SARIMA(1,1,1)(1,1,1,7) were trained per medicine and
evaluated on the time-based held-out window. SARIMA's incorporation of
weekly seasonality produced a measurable improvement over ARIMA:
SARIMA achieved a held-out **R² of 0.81** with a Confidence% of 73 %
and an MAE of 1.80 units per day, compared with ARIMA's R² of 0.78,
Confidence% of 73 %, and MAE of 1.82. These figures are competitive
with the SARIMA results reported by Suan et al. (n.d.) for French
hospital pharmacy data and validate the literature's argument that
weekly seasonality is the dominant short-cycle pattern in ED
dispensing (Jones et al., 2008; Wargon et al., 2010).

#### 5.3.2 Prophet

Prophet's additive seasonality + holiday-effects formulation produced
the lowest score among the seven candidates: an R² of 0.64, Confidence%
of 65 %, and MAE of 2.35. Inspection of the Prophet residuals
demonstrated systematic under-shooting during the September-October
dengue ramp-up; the additive formulation appears to be unable to
capture the multiplicative interaction between the dengue intensity
curve and the underlying volume base, a known limitation in the
forecasting literature (Ripatti, n.d.).

#### 5.3.3 Machine-Learning Models

Three tabular machine-learning models were trained on the full
engineered feature set: HistGradientBoosting (sklearn), Random Forest,
and XGBoost. RandomForest produced the **best machine-learning result
on this dataset** (R² 0.80, Confidence% 74 %, MAE 1.72), narrowly
outperforming HistGradientBoosting (R² 0.79, Confidence% 73 %, MAE 1.79)
and XGBoost (R² 0.77, Confidence% 70 %, MAE 1.89). The ranking is
consistent with several recent comparative studies in healthcare and
pharmaceutical demand forecasting in which a tuned bagged-tree model
matches or marginally outperforms boosted-tree models on irregular,
high-variance series (Zhu et al., 2021; Suan et al., n.d.).

#### 5.3.4 Deep-Learning (LSTM)

A per-medicine LSTM with sequence length 28, hidden state 24, and 20
epochs (single-threaded to avoid contention with concurrent joblib
workers) achieved an R² of 0.74, Confidence% of 68 %, and an MAE of
2.01. This places the LSTM **below the tabular and SARIMA baselines on
this dataset**, which is consistent with the wider observation that
recurrent neural networks tend to require larger training corpora than
were available here to outperform well-engineered tabular models on
short, highly-seasonal series (Tuominen et al., 2023; Moreno-Sánchez et
al., 2024). The result should not be read as a verdict against deep
learning in ED forecasting in general; rather, it suggests that for a
single-hospital, single-year dataset, the marginal benefit of a
recurrent architecture does not yet outweigh the additional training
cost.

### 5.4 Comparative Model Performance

Table 5.1 consolidates the held-out performance of the seven candidate
models on the same time-based 20 % holdout. Models are sorted by R² in
descending order.

**Table 5.1 — Comparative held-out performance of forecasting models**

| Model | Type | R² | Confidence% | MAE | RMSE |
|-------|------|----|-------------|-----|------|
| **SARIMA** | (1,1,1)(1,1,1,7) | **0.81** | 73 % | 1.80 | ≈ 2.95 |
| **RandomForest** | bagged decision trees | 0.80 | **74 %** | **1.72** | ≈ 2.91 |
| HistGradientBoosting | gradient-boosted trees (sklearn) | 0.79 | 73 % | 1.79 | ≈ 2.94 |
| ARIMA | (2,1,2) | 0.78 | 73 % | 1.82 | ≈ 2.99 |
| XGBoost | gradient-boosted trees (xgboost) | 0.77 | 70 % | 1.89 | ≈ 3.04 |
| LSTM | 28-step, hidden 24 | 0.74 | 68 % | 2.01 | ≈ 3.18 |
| Prophet | additive | 0.64 | 65 % | 2.35 | ≈ 3.45 |

**Confidence%** is defined as the share of held-out days on which the
prediction lies within ±25 % (or ±2 units, whichever is larger) of the
actual demand; this metric was developed specifically for the project
to translate the abstract notion of forecast quality into a procurement-
friendly read-out.

The most important methodological observation from Table 5.1 is that
the top four models (SARIMA, RandomForest, HistGradientBoosting,
ARIMA) cluster within a narrow ~3 % band of R². The literature has
repeatedly cautioned against committing to a single "best" model when
performance differences are this small; a more robust strategy is to
retain all candidate models, expose them through the dashboard, and
allow the decision-maker to reason about them transparently
(Buschiazzo et al., 2020; Tello et al., 2022). The dashboard described
in Section 5.7 implements precisely this principle.

### 5.5 Feature Importance and Local Explainability

Permutation-based **global feature importance** (sklearn's
`permutation_importance`, n_repeats = 3) on the held-out window
identified the per-medicine baseline (`medicine_avg`), the 14-day lag
(`lag_14`), the cyclical month encoding (`month_sin`), the day-of-week
indicator, and the 28-day lag (`lag_28`) as the five most influential
features. The dominance of lag and rolling features is consistent with
ED-forecasting work elsewhere (Jones et al., 2008; Vural et al., n.d.),
while the prominence of the cyclical month encoding confirms that
**annual seasonality** — driven in this dataset principally by the
dengue and smog seasons — is captured smoothly by the model.

**Local explanations** were generated using a finite-difference
implementation in the spirit of LIME for the top-15 medicines. For each
medicine, the eight features with the largest absolute contribution to
its most recent prediction were retained. A representative pattern: for
paracetamol on a date inside the dengue-peak window, the dengue-
intensity feature contributed approximately +1.4 units to the predicted
demand; for Beclometasone Dipropionate on a smog-season date, the AQI
feature contributed approximately +1.1 units. These contributions are
clinically intuitive and serve as a sanity check on the model's
reasoning (Tuominen et al., 2023).

### 5.6 Per-Medicine × Event Impact Analysis

A **per-medicine event-impact table** was constructed to bridge the gap
between abstract model output and operational decision-making. For each
of the 17 medicines, the table reports historical average daily
consumption inside ten event windows (`dengue_peak`, `dengue_season`,
`monsoon`, `summer_heat`, `smog_season`, `ramadan`, `eid_fitr`,
`eid_adha`, `muharram`, `weekend`), the corresponding **uplift % vs.
overall baseline**, and the **forecast totals** projected by the active
model for the next instance of that window, computed for each of the
3-, 4-, 5-, and 6-month horizons.

Selected illustrative findings (sign indicates direction of effect
relative to the medicine's annual baseline):

| Medicine | Event | Historical uplift | Operational implication |
|----------|-------|-------------------|--------------------------|
| Paracetamol | Dengue peak | +80 % | Increased procurement Sep-Nov |
| Paracetamol | Dengue season | +45 % | Sustained higher level Aug-Nov |
| Ondansetron | Monsoon | +38 % | Anticipated GI surge Jul-Sep |
| Ondansetron | Dengue peak | +33 % | Cross-effect with febrile illness |
| Sodium Chloride 0.9 % | Dengue peak | +32 % | Major fluids surge Oct |
| Beclometasone Dipropionate | Smog season | sizeable + | Procurement Nov-Feb |
| Ipratropium bromide | Smog season | sizeable + | Procurement Nov-Feb |
| Ketorolac | Eid-ul-Adha | + | Trauma-related uplift |
| Esomeprazole | Ramadan | + (mild) | PPI increase, fasting-related |
| Most medicines | Weekend | – (≈ –29 %) | Emergency-only profile |

The complete table is rendered as an interactive matrix in the
dashboard (Section 5.7) with three views — Uplift %, Forecast units,
and Historical avg/day — and per-cell hover detail. This artefact is
the most directly useful output of the project from the perspective of
hospital procurement, and operationalises the framework's central
hypothesis that **patient-flow trends and event-windows can be
quantitatively linked to item-level dispensing demand** (Suan et al.,
n.d.; Zhu et al., 2021; Buschiazzo et al., 2020).

### 5.7 Decision-Support Dashboard

To translate the forecasting results into an operational tool — and to
respond to the literature's repeated observation that predictive value
is realised only when integrated into workflow (Hurwitz et al., 2016;
Eckerson, n.d.; Buschiazzo et al., 2020) — an interactive decision-
support dashboard was implemented. The dashboard is a static Next.js
14 application rendered to HTML at build time, deployed via Vercel,
and consuming a single JSON artefact (`forecasts.json`) produced by the
training pipeline. The principal panels of the dashboard, and the
research questions each panel addresses, are summarised in Table 5.2.

**Table 5.2 — Decision-support dashboard panels**

| Panel | Question Answered |
|-------|--------------------|
| KpiCards | What is the data range, the test-MAE/RMSE, and the top medicines? |
| HistoryChart | What is the long-run shape of total daily dispensing? |
| **PreprocessingChart** | What is the per-medicine daily series, with rolling Mean / Median / Mode / Std / Variance overlays? |
| **CalendarHeatmap** | A GitHub-style daily heatmap revealing dengue peaks, weekend dips, and event surges at a glance |
| **ForecastSection** | A horizon toggle (3 / 4 / 5 / 6 months) and a model selector |
| ModelComparison | Sortable, ranked R² / Confidence / MAE / RMSE for the seven candidate models |
| ForecastChart | Per-medicine daily forecast line; monthly tags switch with the selected model |
| MonthlyHeatmap | Medicine × month forecast totals (clipped to active horizon) |
| **MedicineFeatureImpact** | Medicine × event uplift / forecast matrix |
| LahoreTrendsChart | Dengue × temperature × rainfall × AQI × Ramadan × Eid overlay |
| TopMedicinesTable | Demand-sorted list of medicines |
| ShapChart | Global feature importance |
| LimePanel | Per-medicine local explanations |

Three panels — the **PreprocessingChart**, the **CalendarHeatmap**, and
the **ModelComparison** with its model-selector — are direct
implementations of stakeholder requirements identified during the FYP-2
review presentation. By exposing both the descriptive and predictive
layers of the analysis, the dashboard satisfies the long-standing call
for BI tools that embed forecasts rather than merely report on the past
(Hurwitz et al., 2016; Tello et al., 2022).

### 5.8 Final Presentation

The empirical findings, the comparative model performance, and the
decision-support dashboard were demonstrated in the **Final Presentation**
of the project. The presentation included a live walk-through of the
dashboard with the partner hospital's operational profile and concluded
with a discussion of stakeholder benefits and recommendations, both of
which are elaborated in Section 6.

---

## 6. Discussion and Conclusion

### 6.1 Answers to the Research Questions

The research set out to answer four questions, each of which is
addressed in turn below.

**RQ1 — Can patient-flow trends in a Pakistani Emergency Department be
modelled accurately enough to support short-term forecasting of medicine
demand?**

The empirical results in Section 5 answer this question affirmatively.
The top four models (SARIMA, RandomForest, HistGradientBoosting,
ARIMA) produced held-out R² values in the 0.78–0.81 range, with
Confidence% values in the 73–74 % band, indicating that on three out of
four held-out days the forecast lies within a quarter of the actual
demand. These figures are competitive with prior international results
in ED arrival forecasting (Wargon et al., 2010; Vural et al., n.d.) and,
to the team's knowledge, are among the first reported for **item-
level** ED dispensing forecasting in a Pakistani hospital.

**RQ2 — Which class of model is best suited to ED dispensing data of
this scale?**

The honest answer is that **no single model dominates**: SARIMA and
the tabular machine-learning models are operationally
indistinguishable on the metrics adopted. This finding is consistent
with the wider literature, which notes that on short, highly-seasonal,
single-site series the marginal benefit of more complex architectures
(deep learning in particular) is small or negative (Tuominen et al.,
2023; Moreno-Sánchez et al., 2024). The methodological recommendation
is therefore to **retain multiple models and expose the comparison to
the user**, as implemented in the ModelComparison panel.

**RQ3 — Can the link between operational/clinical events and medicine
consumption be quantified and surfaced in a way that is useful to a
procurement officer?**

Yes. The medicine × event impact table (Section 5.6) translates the
seasonal and event-driven structure observed in the data into uplifts
expressed in percentage terms relative to baseline, alongside forecast
totals per horizon. This artefact is the most operationally direct
output of the project and was developed specifically in response to
the gap identified in the literature, where forecasting research and
inventory research have largely proceeded in parallel without
intersecting (Buschiazzo et al., 2020; Silva et al., 2023).

**RQ4 — Can the predictive output be embedded in a decision-support
tool that hospital administrators can use without ML expertise?**

Yes. The dashboard described in Section 5.7 is intentionally
deployable on a static-hosting platform (Vercel) with no Python or
backend at runtime, which is a deliberate choice in response to the
infrastructure constraints common in Pakistani hospitals (Khursheed et
al., 2015; Mir et al., 2015). The panels are read-only by default,
horizon and model selection are surfaced through a single horizontal
toggle and a sortable table respectively, and per-cell hover detail
provides natural-language readouts of all forecast figures.

### 6.2 Commentary on Findings — Confirming and Contradicting the
Literature

Several findings are **consistent** with the existing literature:

* The dominance of weekly and seasonal cycles in ED dispensing
  (Jones et al., 2008; María Patón Arévalo et al., 2012) is reproduced
  cleanly in the Doctors Hospital dataset.
* The strong dengue-season uplift in paracetamol and fluids dispensing
  matches the Pakistani epidemiological literature on dengue case-loads
  (Mir et al., 2015; Sakina Kamboh et al., 2024).
* The marginal under-performance of LSTM relative to well-engineered
  tabular models on a single-site, single-year dataset confirms a
  pattern documented in healthcare deep-learning benchmarks
  (Moreno-Sánchez et al., 2024).
* The need to integrate forecasts into BI-style decision-support tools,
  rather than ship them as static reports, is reinforced by the
  practical reception of the dashboard during the final presentation
  (Hurwitz et al., 2016; Eckerson, n.d.).

Two findings **partially complicate** earlier claims:

* Prophet's relatively poor performance on this dataset is at odds with
  the model's strong reputation in popular forecasting practice
  (Ripatti, n.d.). The most plausible explanation is that Prophet's
  additive formulation cannot capture the multiplicative interaction
  between the dengue intensity curve and the underlying volume base, a
  hypothesis that should be tested in future work using a multi-year
  dataset.
* The narrow performance band among the top four models suggests that
  the procurement value of a single-best-model strategy is small and
  that ensemble or model-blend approaches deserve fuller study —
  particularly the per-medicine model selection or weighted-blend
  recommended by Zhu et al. (2021).

### 6.3 Theoretical Contributions

The project makes three modest but defensible theoretical contributions
to the literature:

1. **An item-level forecasting framework that explicitly links patient-
   flow trends, cultural calendars, climatology, and ED dispensing.**
   Earlier work has connected each of these signals to ED operations in
   isolation; the present work integrates them into a single, end-to-
   end pipeline that begins with raw dispensing records and ends with a
   per-medicine, per-event uplift table.
2. **A Confidence% metric** translating R² into a procurement-friendly
   quantity. The metric is not a calibrated probability and should not
   be over-interpreted, but it is a pragmatic translation that
   facilitates conversations with non-technical stakeholders.
3. **An empirical demonstration in a Pakistani hospital setting**, an
   environment that has been substantially under-represented in the
   ED-forecasting literature relative to North American and European
   contexts (Khursheed et al., 2015; Haroon, 2019; Mir et al., 2015).

### 6.4 Practical Implications

For the partner hospital and similar Pakistani EDs, the practical
implications are as follows:

* **Procurement planning** can be tied directly to forecast totals at
  the medicine × horizon level. The MedicineFeatureImpact panel makes
  the dengue-season and smog-season signals explicit, so that
  paracetamol and IV fluids can be staged for August-November and
  respiratory medicines for November-February.
* **Stockout risk** can be reduced by aligning reorder points with the
  Confidence%-aware forecast, with appropriate safety stock for
  medicines whose Confidence is below 70 %.
* **Decision-support adoption** is achievable without departmental
  retraining, because the dashboard's read-only design and natural-
  language hover detail do not require any data-science skill from the
  end user.

### 6.5 Recommendations

For hospital administrators:

1. Use the Forecast Section's horizon toggle to align ordering cadence
   with operational reality (3 months for fast-moving supplies, 6
   months for budget planning).
2. Treat the model-comparison ranking as a **diagnostic** rather than
   a recommendation: when more than one model agrees within ~3 % R²,
   the procurement decision should not be sensitive to the choice of
   model.
3. Track **forecast vs. actual** weekly, and re-train the pipeline
   whenever a fresh year of dispensing data is available.

For supply-chain teams:

1. Couple the MedicineFeatureImpact uplifts with current stock levels
   to derive **dynamic reorder points**.
2. Stage extra safety stock for medicines whose Confidence% is below
   70 %, particularly during dengue-peak and smog-season windows.

For the academic community:

1. **Replicate the pipeline** on data from additional Pakistani
   hospitals (Saleem Memorial, Evercare, Aga Khan University Hospital)
   to produce a multi-site benchmark.
2. **Substitute climatology for live observations** by integrating
   PMD/IQAir and NIH Pakistan dengue feeds, then re-evaluate model
   performance under the richer feature set.
3. **Investigate model-blend strategies** in the narrow-performance-
   band regime documented above.

### 6.6 Limitations

The principal limitations of the present study are summarised below.

1. **Single hospital, single year of data.** The generalisability of
   the empirical findings to other Pakistani EDs is established by
   analogy with the literature rather than directly tested; multi-site
   replication is needed.
2. **Lahore weather and AQI used as climatology, not observation.**
   Real-time PMD and IQAir feeds were out of scope; monthly normals
   smooth out the actual smog spikes, monsoon bursts, and heat-wave
   episodes that drive ED admissions.
3. **Dengue intensity used as a Gaussian seasonal curve rather than a
   live NIH Pakistan feed.** This choice was forced by the
   unavailability of machine-readable weekly dengue counts within the
   project window.
4. **Recursive forecast accumulates error past ~ 90 days**, which is
   the principal reason horizon offers were capped at six months.
5. **No medicine-substitution modelling.** When one medicine runs
   out, the dispensing basket commonly shifts to a clinically
   equivalent alternative (e.g., ondansetron ↔ metoclopramide); the
   current model treats every medicine as an independent series.
6. **Confidence% is a coverage proxy, not a calibrated interval.**
   For a calibrated probabilistic forecast, quantile regression or
   conformal prediction is required.
7. **No real-time data ingest.** The current workflow refreshes
   forecasts via a manual rerun of the training pipeline; live HL7 /
   FHIR ingest is left for future work.
8. **No authentication or multi-tenant isolation.** The deployed
   dashboard is read-only and unauthenticated, suitable for a single-
   hospital pilot but not yet for multi-hospital use.

### 6.7 Future Research Directions

The project suggests a clear research agenda:

1. **Multi-site replication** across Pakistani hospitals to test
   generalisability.
2. **CSV upload directly from the dashboard** to remove the manual
   training-pipeline step, allowing administrators to drop a fresh
   year of dispensing data and watch the forecasts re-render.
3. **User authentication and multi-tenant data isolation**, with
   role-based views for procurement, pharmacy, and administration —
   a pre-requisite for a production deployment serving multiple
   hospitals from the same instance.
4. **Live signal ingestion** for PMD/IQAir weather, NIH Pakistan
   dengue counts, and SBP CPI updates, replacing the current
   climatological proxies.
5. **Inventory integration** that pairs the forecast with current
   stock levels and lead-times to produce reorder-point reports and
   stock-out risk windows.
6. **Per-prediction calibrated confidence intervals** via quantile
   regression or conformal prediction.
7. **Model-blend or per-medicine model selection** to exploit the
   narrow performance band documented in Section 5.4.
8. **Mobile-first procurement view** for use during morning standups.
9. **Alerts and notifications** when the forecast crosses operational
   thresholds (e.g., predicted >50 % spike over the next 14 days).
10. **Audit and versioning** of every retrain so that "why did this
    number change" is answerable from metadata alone.
11. **Reinforcement-learning- or NLP-based extensions** for adaptive
    procurement and richer extraction of clinical information from the
    free-text Diagnosis field, in line with the directions sketched in
    Section 1.5.

### 6.8 Conclusion

This study set out to develop, deploy, and test a predictive analytics
system that forecasts ED medicine demand by integrating patient-flow
trends, cultural calendars, climatology, and historical dispensing —
and to embed the results in a decision-support tool fit for use in a
Pakistani hospital. The empirical results, drawn from a 365-day
anonymised dispensing dataset provided by Doctors Hospital, Lahore,
demonstrate that the integrated framework can produce held-out R²
values of approximately 0.80 with Confidence% values around 73-74 %,
that the seasonal and event-driven structure of demand can be
quantified at the medicine × event level, and that the resulting
forecasts can be embedded in a static, read-only dashboard that does
not require any data-science skill from the end user. The principal
limitations — single-site coverage, climatological rather than
observational weather inputs, the absence of authentication and CSV
upload — are well-defined and translate directly into the future-work
agenda set out in Section 6.7. The team is grateful to Doctors
Hospital, Lahore, for its support of the project, and to Evercare
Hospital, Lahore, and Saleem Memorial Hospital for their consideration
during the engagement process.

The broader contribution of the project is, perhaps, the demonstration
that the gap between forecasting research and inventory practice in
Pakistani EDs — long noted in the literature — can be closed in a
single academic project provided that data access, rigorous
methodology, and deliberately operational design choices are pursued
together. We hope that the open-source pipeline, the methodology
document, and the dashboard described in this report are of use to
future researchers and practitioners working on the same problem.
