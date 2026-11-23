# 07 · Design references, parameter provenance and topology optimisation

The code-level source of truth is [`design/registry.py`](../design/registry.py): every parameter and each of the
20 reference designs carries a `source` and a `status`. `python design/registry.py` fails if anything has no
provenance or does not build as one watertight solid.

| Status | Meaning |
|---|---|
| verified | checked against a primary source or the paper's own files |
| cited | from a published source read through a secondary summary; the primary is not yet checked |
| unverified | recalled from a known source but not yet checked; **must be checked before CFD** |
| assumption | our choice; the registry note gives the reason |

Current count (2026-11-23, revision 2): 11 verified, 14 cited, 1 unverified, 16 assumption.

**Rule:** every reference has control surfaces, as practical vehicles do. Only two bare hulls are allowed, each with a
stated reason (`BARE_ALLOWED`):
- SUBOFF bare, because it has published experiments;
- the paper's swordfish1, because the paper's dataset is finless.

The bio set focuses on fast swimmers: tuna, swordfish (flat bill, about 41 % of length), sailfish (bill 17 %, sail
folded), wahoo (fineness 8.4) and manta. The two fish that are not fast swimmers were dropped: boxfish and eel.

## Literature found (2026-11-23)
- **REMUS 100:** Prestero 2001, MIT SM thesis ([DSpace](https://dspace.mit.edu/handle/1721.1/65068),
  [DTIC](https://apps.dtic.mil/sti/pdfs/ADA409034.pdf)).
  - Myring hull, code 15/55/1.25/0.4363 according to secondary sources. Dimensionalised values are in Table 2.1.
  - **DTIC was under maintenance today**, so Table 2.1 and the fin data are *not yet read*.
  - The values we recalled give L = 1.386 m, which conflicts with the 1.33 m envelope, so at least one is wrong.
- **DARPA SUBOFF:** Groves, Huang & Chang 1989, DTRC/SHD-1298-01 ([DTIC ADA210642](https://apps.dtic.mil/sti/tr/pdf/ADA210642.pdf)).
  - Cited via secondary sources: L 4.356 m, D 0.508 m.
  - Breakpoints: bow 3.333 ft (1.016 m), parallel body to 10.646 ft, afterbody to 13.979 ft, cap to 14.292 ft.
  - The exact bow, stern and cap polynomials, the appendages and the sail are **not yet read**. Our `suboff_approx`
    uses placeholder curves.
  - Experimental data: DTIC ADA359226 (summary of the SUBOFF experimental programme).
- **Hull families:** an AUV hull review in JMSE 2026 ([doi](https://doi.org/10.3390/jmse14201883)) covers
  Myring/DREA/Haack as fewer-than-10-parameter families, with Myring + RANS + DREA validation as the mature workflow.
- **Flat stern:** JMSE 2026 ([doi](https://doi.org/10.3390/jmse14161456)), Myring forebody with nose exponent 1–3.
- **Fish:**
  - Scombrid fineness ratios: about 4.5 for Thunnus, up to 8.4 for Acanthocybium (Magnuson 1978, via a secondary summary).
  - Caudal-fin aspect ratio: anguilliform 0–1.61, thunniform 5.5–7.9
    ([CCU thesis](https://digitalcommons.coastal.edu/cgi/viewcontent.cgi?article=1188&context=etd)).
  - Boxfish: CFD shows the carapace is *destabilising* and its drag is not unusually low
    ([Van Wassenbergh et al. 2015](https://pmc.ncbi.nlm.nih.gov/articles/PMC4305415)).
- **Swordfish / sailfish:** [Sagong et al. 2013, PLOS ONE](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0081323).
  - Wind-tunnel C_D on wetted area: **0.009 for swordfish and 0.0075 for sailfish**. These are direct validation
    targets for the bio references.
  - Bills are about 17 % (sailfish) to 44 % (swordfish) of total length, and do not reduce drag at cruise speed.
  - Swordfish pectoral fins are about 15 % of wetted area but add about 51 % drag.
- **Manta:** a manta-ray UUV CFD study with 1 m span and pectoral-fin AR 2.5
  ([Bardera Mora et al. 2023](https://www.scipedia.com/wd/images/1/1b/Bardera_Mora_et_al_2023a_1121_hydro.pdf)).
  Gliding, aspect-ratio and fin-bending studies: [JMSE 2026](https://doi.org/10.3390/jmse14050406),
  [manta glider](https://www.researchgate.net/publication/314196133_Hydrodynamic_performance_analysis_of_a_biomimetic_manta_ray_underwater_glider).
- **Paper dataset (verified here):**
  - a 53–597 mm, c 53–592 mm, d 50–200 mm, n 1–5, θ 1–50°, L 1.0–2.0 m, L/d 5.1–38.9.
  - The swordfish1 case: L 1.107 m, d 0.052 m, volume 2.143 L. Our Myring fit gives 2.05 L (−4 %); use their STL as ground truth.

## To do before any CFD
1. Read Prestero Table 2.1 and the fin data; fix `REMUS_HULL` and `REMUS_FINS`.
2. Read the Groves 1989 equations; replace `suboff_approx` with the exact polynomials; add the sail and stern
   appendages from the report.
3. Replace the fish and manta assumptions with morphometric data where available. Use CT-based geometry for the boxfish
   if the study shares it.
4. Implement ITTC/TEOS-10 ρ(T, S) and ν(T, S), and check them against the paper's ρ = 1027 and ν = 1.736e-6.

## Topology optimisation: how it fits
Strictly, *topology* optimisation lets material appear anywhere, so the number of bodies and holes can change. For
external flow at Re ~ 10⁶–10⁷ that is still research-grade: density-based methods (Borrvall & Petersson 2003) work
for Stokes/laminar flow and struggle with RANS turbulence and wall functions. The practical options, from most
to least ready:

| Level | What changes | Tool | Fits where |
|---|---|---|---|
| 1. Parametric optimisation | registry parameters (lengths, n, θ, fin planform, deflection) | the surrogate + Bayesian optimisation / GA (the paper's approach) | the whole corpus, cheap |
| 2. Free-form shape optimisation | smooth deformation of a reference surface (FFD control points, B-spline radius) | OpenFOAM adjoint (`adjointOptimisationFoam`, ESI v2112+) or surrogate gradients | hull and fin shape beyond the families |
| 3. Topology optimisation, laminar/Stokes | material distribution in a 2D/axisymmetric domain | FEniCS + dolfin-adjoint (density method) | low-Re concept study, PINN comparison, blood-flow case later |
| 4. Topology optimisation of internal structure | ribs, frames and pressure-hull layout under depth load | FEniCS/dolfin-adjoint structural (SIMP) | depth matters here (structure, not drag) |

Recommendation:
- Corpus and surrogate support levels 1 and 2 directly.
- Do level 3 as a small, honest research add-on: "what does topology optimisation give at low Re, and how close does
  the best parametric family get?"
- Level 4 links depth/pressure to design properly, through structure.
