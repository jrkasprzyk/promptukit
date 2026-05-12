"""
Generate a 60-question multiple choice exam PDF for CVEN 4333 Engineering Hydrology.
Designed for use with Gradescope's bubble sheet system: students answer on the
separate Gradescope Bubble Sheet Template (A-E choices). This PDF is the question
booklet only.

Requires: reportlab  (pip install reportlab)
Run: python create_exam.py  ->  produces cven4333_exam.pdf
"""

from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib import colors
import argparse
import json
import re
from pathlib import Path
import sys
from collections import OrderedDict

from promptukit.questions.text_audit import reportlab_safe_text

# --- Styles ---
styles = getSampleStyleSheet()

title_style = ParagraphStyle('ExamTitle', parent=styles['Title'],
    fontSize=16, spaceAfter=4, alignment=TA_CENTER)
subtitle_style = ParagraphStyle('ExamSubtitle', parent=styles['Normal'],
    fontSize=11, spaceAfter=2, alignment=TA_CENTER)
instructions_style = ParagraphStyle('Instructions', parent=styles['Normal'],
    fontSize=9, spaceAfter=6, leftIndent=18, rightIndent=18, alignment=TA_JUSTIFY)
question_style = ParagraphStyle('Question', parent=styles['Normal'],
    fontSize=10, spaceBefore=18, spaceAfter=2, fontName='Helvetica-Bold')
choice_style = ParagraphStyle('Choice', parent=styles['Normal'],
    fontSize=10, spaceBefore=4, spaceAfter=4, leftIndent=24)
section_style = ParagraphStyle('Section', parent=styles['Heading2'],
    fontSize=12, spaceBefore=14, spaceAfter=6, fontName='Helvetica-Bold',
    textColor=colors.HexColor('#1a1a1a'))
code_style = ParagraphStyle('Code', parent=styles['Normal'],
    fontSize=9, spaceBefore=4, spaceAfter=4, leftIndent=18,
    fontName='Courier', leading=12,
    backColor=colors.HexColor('#f5f5f5'))

# --- LaTeX-to-unicode substitution table ---
# Converts common inline LaTeX math patterns to readable Unicode equivalents.
# This covers the most frequently used math symbols in exam questions.
_LATEX_SUBS = [
    # Greek letters
    (re.compile(r'\\alpha\b'), 'α'), (re.compile(r'\\beta\b'), 'β'),
    (re.compile(r'\\gamma\b'), 'γ'), (re.compile(r'\\Gamma\b'), 'Γ'),
    (re.compile(r'\\delta\b'), 'δ'), (re.compile(r'\\Delta\b'), 'Δ'),
    (re.compile(r'\\epsilon\b'), 'ε'), (re.compile(r'\\varepsilon\b'), 'ε'),
    (re.compile(r'\\zeta\b'), 'ζ'), (re.compile(r'\\eta\b'), 'η'),
    (re.compile(r'\\theta\b'), 'θ'), (re.compile(r'\\Theta\b'), 'Θ'),
    (re.compile(r'\\lambda\b'), 'λ'), (re.compile(r'\\Lambda\b'), 'Λ'),
    (re.compile(r'\\mu\b'), 'μ'), (re.compile(r'\\nu\b'), 'ν'),
    (re.compile(r'\\xi\b'), 'ξ'), (re.compile(r'\\pi\b'), 'π'),
    (re.compile(r'\\Pi\b'), 'Π'), (re.compile(r'\\rho\b'), 'ρ'),
    (re.compile(r'\\sigma\b'), 'σ'), (re.compile(r'\\Sigma\b'), 'Σ'),
    (re.compile(r'\\tau\b'), 'τ'), (re.compile(r'\\phi\b'), 'φ'),
    (re.compile(r'\\Phi\b'), 'Φ'), (re.compile(r'\\chi\b'), 'χ'),
    (re.compile(r'\\psi\b'), 'ψ'), (re.compile(r'\\Psi\b'), 'Ψ'),
    (re.compile(r'\\omega\b'), 'ω'), (re.compile(r'\\Omega\b'), 'Ω'),
    # Operators and symbols
    (re.compile(r'\\times\b'), '×'), (re.compile(r'\\cdot\b'), '·'),
    (re.compile(r'\\div\b'), '÷'), (re.compile(r'\\pm\b'), '±'),
    (re.compile(r'\\mp\b'), '∓'), (re.compile(r'\\leq\b'), '≤'),
    (re.compile(r'\\geq\b'), '≥'), (re.compile(r'\\neq\b'), '≠'),
    (re.compile(r'\\approx\b'), '≈'), (re.compile(r'\\equiv\b'), '≡'),
    (re.compile(r'\\infty\b'), '∞'), (re.compile(r'\\sum\b'), 'Σ'),
    (re.compile(r'\\int\b'), '∫'), (re.compile(r'\\partial\b'), '∂'),
    (re.compile(r'\\nabla\b'), '∇'), (re.compile(r'\\sqrt\{([^}]+)\}'), r'√(\1)'),
    (re.compile(r'\\frac\{([^}]+)\}\{([^}]+)\}'), r'(\1)/(\2)'),
    # Superscripts/subscripts — braced forms before bare numeric shortcuts
    (re.compile(r'\^\{([^}]+)\}'), r'^(\1)'),
    (re.compile(r'_\{([^}]+)\}'), r'_(\1)'),
    (re.compile(r'\^2\b'), '²'), (re.compile(r'\^3\b'), '³'),
    (re.compile(r'\^n\b'), 'ⁿ'),
    # Strip remaining braces and backslash commands
    (re.compile(r'\\[a-zA-Z]+'), ''), (re.compile(r'[{}]'), ''),
]

# Matches inline LaTeX: $...$ or \(...\)
_LATEX_INLINE_RE = re.compile(r'\$([^$]+?)\$|\\\((.+?)\\\)', re.DOTALL)


def latex_to_reportlab(text: str) -> str:
    """Convert inline LaTeX math (``$...$`` or ``\\(...\\)``) in *text* to a
    plain-text Unicode approximation suitable for ReportLab Paragraph markup.

    Unrecognised commands are stripped so output is always printable.
    """
    def _replace(m: re.Match) -> str:
        inner = m.group(1) or m.group(2) or ''
        for pattern, repl in _LATEX_SUBS:
            inner = pattern.sub(repl, inner)
        return inner

    return _LATEX_INLINE_RE.sub(_replace, text)


# --- Choice marker helpers ---
# Mapping from metadata ``choice_marker`` value to a callable that formats
# a lettered choice. "letter" is the default legacy style.
def _choice_label_letter(idx: int) -> str:
    """Return 'A) ', 'B) ', … label."""
    return f"{chr(ord('A') + idx)}) "


def _choice_label_circle(idx: int) -> str:
    """Return '○ A  ' Gradescope-style circle marker."""
    return f"○ {chr(ord('A') + idx)}  "


def _choice_label_square(idx: int) -> str:
    """Return '□ A  ' Gradescope-style square marker."""
    return f"□ {chr(ord('A') + idx)}  "


_CHOICE_LABEL_FNS = {
    "letter": _choice_label_letter,
    "circle": _choice_label_circle,
    "square": _choice_label_square,
}


def _get_choice_label_fn(metadata: dict):
    """Return the appropriate choice-label function for the exam metadata."""
    marker = (metadata.get("choice_marker") or "letter").lower().strip()
    return _CHOICE_LABEL_FNS.get(marker, _choice_label_letter)


# --- Answer-space helper ---
_ANSWER_SPACE_INCHES = {"small": 1.0, "medium": 2.0, "large": 4.0}


def _answer_space_inches(answer_space) -> float:
    """Convert an answer_space value to a float number of inches."""
    if answer_space is None:
        return 2.0  # default
    if isinstance(answer_space, str):
        return _ANSWER_SPACE_INCHES.get(answer_space.lower(), 2.0)
    try:
        val = float(answer_space)
        return max(0.25, val)
    except (TypeError, ValueError):
        return 2.0

# --- Questions ---
# Each entry: {"q": "N. question text", "choices": ["A) ...", "B) ...", ...]}
# ReportLab Paragraph supports HTML-like tags: <sub>, <super>, &mdash;, &minus;, etc.
questions = [
    # === HYDROLOGIC CYCLE & GLOBAL WATER BALANCE (1-8) ===
    {"q": "1. Which of the following represents the largest reservoir of fresh water on Earth?",
     "choices": ["A) Oceans", "B) Glaciers and ice caps", "C) Groundwater",
                 "D) Lakes and rivers", "E) Atmospheric water vapor"]},
    {"q": "2. The basic water balance equation for a watershed over a given time period is:",
     "choices": ["A) P = Q + ET + &Delta;S", "B) P = Q &minus; ET + &Delta;S",
                 "C) Q = P + ET + &Delta;S", "D) ET = P + Q + &Delta;S",
                 "E) P = Q + ET &minus; &Delta;S"]},
    {"q": "3. On a global annual basis, which statement is TRUE about the hydrologic cycle?",
     "choices": ["A) More precipitation falls on land than on the oceans",
                 "B) More water evaporates from the ocean surface than precipitates onto it",
                 "C) Runoff from land to oceans exactly equals precipitation over the oceans",
                 "D) Evaporation from land surfaces exceeds precipitation over land",
                 "E) The volume of water stored in the atmosphere is increasing each year"]},
    {"q": "4. Approximately what percentage of all water on Earth is fresh water?",
     "choices": ["A) About 0.3%", "B) About 2.5%", "C) About 10%",
                 "D) About 25%", "E) About 50%"]},
    {"q": "5. More than 100 times more water is stored in _____ than in surface water bodies such as lakes.",
     "choices": ["A) The atmosphere", "B) Soil moisture", "C) Ice and snow",
                 "D) Rivers and streams", "E) Biological organisms"]},
    {"q": "6. Which process in the hydrologic cycle converts water vapor directly to ice without passing through the liquid phase?",
     "choices": ["A) Sublimation", "B) Condensation", "C) Deposition",
                 "D) Evaporation", "E) Transpiration"]},
    {"q": "7. The residence time of water in the atmosphere is approximately:",
     "choices": ["A) 1 hour", "B) 9&ndash;10 days", "C) 1 year",
                 "D) 100 years", "E) 10,000 years"]},
    {"q": "8. In the water balance, &Delta;S represents:",
     "choices": ["A) Streamflow discharge", "B) Change in storage within the control volume",
                 "C) Surface runoff only", "D) Deep percolation losses",
                 "E) Evapotranspiration losses"]},

    # === PRECIPITATION (9-16) ===
    {"q": "9. Which of the following is NOT a standard method for estimating areal average precipitation over a watershed?",
     "choices": ["A) Arithmetic mean", "B) Thiessen polygon method",
                 "C) Isohyetal method", "D) Muskingum method",
                 "E) Inverse distance weighting"]},
    {"q": "10. A double-mass curve analysis is primarily used to:",
     "choices": ["A) Estimate missing precipitation data",
                 "B) Check for consistency and detect changes in a precipitation station record",
                 "C) Determine the probable maximum precipitation",
                 "D) Convert point rainfall to areal rainfall",
                 "E) Develop intensity-duration-frequency curves"]},
    {"q": "11. The Thiessen polygon method weights each rain gauge by:",
     "choices": ["A) The elevation of the gauge",
                 "B) The area of the polygon surrounding the gauge relative to the total watershed area",
                 "C) The inverse of the distance from the gauge to the watershed centroid",
                 "D) The average annual precipitation at the gauge",
                 "E) Equal weight for all gauges"]},
    {"q": "12. An intensity-duration-frequency (IDF) curve shows that for a given return period, as storm duration increases:",
     "choices": ["A) Rainfall intensity increases", "B) Rainfall intensity decreases",
                 "C) Rainfall intensity remains constant", "D) Total rainfall depth decreases",
                 "E) The curve cannot predict this relationship"]},
    {"q": "13. A 100-year storm event has a probability of being equaled or exceeded in any given year of:",
     "choices": ["A) 100%", "B) 10%", "C) 1%", "D) 0.1%", "E) 0.01%"]},
    {"q": "14. The probability that a 50-year flood will be equaled or exceeded at least once in a 50-year period is approximately:",
     "choices": ["A) 100%", "B) 64%", "C) 50%", "D) 36%", "E) 2%"]},
    {"q": "15. Orographic precipitation is caused primarily by:",
     "choices": ["A) Heating of the land surface",
                 "B) Frontal boundary interactions between air masses",
                 "C) Air being forced upward over elevated terrain",
                 "D) Intense localized convective activity",
                 "E) Convergence of trade winds"]},
    {"q": "16. Which type of precipitation measurement device provides a continuous record of rainfall accumulation over time?",
     "choices": ["A) Standard rain gauge (non-recording)", "B) Tipping-bucket rain gauge",
                 "C) Graduated cylinder", "D) Evaporation pan", "E) Lysimeter"]},

    # === EVAPOTRANSPIRATION & INFILTRATION (17-24) ===
    {"q": "17. Potential evapotranspiration (PET) is defined as:",
     "choices": ["A) The actual amount of water lost from a surface in a given period",
                 "B) The maximum rate of evapotranspiration when water supply is unlimited",
                 "C) The evaporation from open water bodies only",
                 "D) Transpiration from crops minus soil evaporation",
                 "E) The rate of evaporation measured by a Class A pan"]},
    {"q": "18. Which of the following factors does NOT directly influence evapotranspiration rates?",
     "choices": ["A) Solar radiation", "B) Wind speed", "C) Soil hydraulic conductivity",
                 "D) Relative humidity", "E) Air temperature"]},
    {"q": "19. The Penman-Monteith equation for estimating evapotranspiration accounts for:",
     "choices": ["A) Energy balance only", "B) Aerodynamic (mass transfer) effects only",
                 "C) Both energy balance and aerodynamic effects",
                 "D) Soil moisture content only",
                 "E) Precipitation intensity and duration"]},
    {"q": "20. In the Horton infiltration equation, as time progresses during a storm event, the infiltration rate:",
     "choices": ["A) Increases exponentially toward a maximum value",
                 "B) Remains constant throughout the event",
                 "C) Decreases exponentially toward a minimum constant rate",
                 "D) Oscillates depending on rainfall intensity",
                 "E) Drops immediately to zero"]},
    {"q": "21. Which soil type would generally have the HIGHEST saturated hydraulic conductivity?",
     "choices": ["A) Clay", "B) Silty clay loam", "C) Silt loam",
                 "D) Sandy loam", "E) Sand"]},
    {"q": "22. The Green-Ampt infiltration model assumes:",
     "choices": ["A) A gradually varying moisture profile in the soil column",
                 "B) A sharp wetting front that moves downward as a piston",
                 "C) Infiltration rate is independent of soil moisture",
                 "D) All rainfall immediately becomes surface runoff",
                 "E) Evapotranspiration is the dominant loss mechanism"]},
    {"q": "23. Rainfall excess (effective rainfall) is defined as:",
     "choices": ["A) Total rainfall minus baseflow",
                 "B) Total rainfall minus all abstractions (infiltration, interception, depression storage)",
                 "C) Total rainfall times a runoff coefficient",
                 "D) The portion of rainfall that infiltrates into the soil",
                 "E) Rainfall that occurs after the soil is fully saturated"]},
    {"q": "24. The &phi;-index method for computing rainfall excess assumes:",
     "choices": ["A) Infiltration varies exponentially with time",
                 "B) A constant rate of abstraction throughout the storm",
                 "C) Infiltration follows the Green-Ampt model",
                 "D) Abstractions occur only at the beginning of the storm",
                 "E) Rainfall excess equals total rainfall"]},

    # === RUNOFF & UNIT HYDROGRAPH (25-36) ===
    {"q": "25. The rational method formula Q = CiA is typically used for:",
     "choices": ["A) Large river basin flood forecasting",
                 "B) Small urban watershed peak discharge estimation",
                 "C) Reservoir storage design",
                 "D) Groundwater recharge estimation",
                 "E) Sediment transport calculations"]},
    {"q": "26. In the rational method, the time of concentration is significant because:",
     "choices": ["A) It determines the total volume of runoff",
                 "B) Peak discharge occurs when the entire watershed contributes flow at the outlet",
                 "C) It is used to calculate infiltration losses",
                 "D) It determines the baseflow separation point",
                 "E) It equals the lag time of the unit hydrograph"]},
    {"q": "27. An SCS (NRCS) Curve Number of 98 indicates:",
     "choices": ["A) A highly permeable, well-vegetated watershed",
                 "B) A nearly impervious surface with very high runoff potential",
                 "C) A forested watershed with excellent infiltration",
                 "D) An average agricultural watershed",
                 "E) A watershed with deep sandy soils"]},
    {"q": "28. In the SCS Curve Number method, the initial abstraction I<sub>a</sub> is commonly estimated as:",
     "choices": ["A) I<sub>a</sub> = 0.1S", "B) I<sub>a</sub> = 0.2S",
                 "C) I<sub>a</sub> = 0.5S", "D) I<sub>a</sub> = S", "E) I<sub>a</sub> = 2S"]},
    {"q": "29. A unit hydrograph (UH) represents the direct runoff hydrograph resulting from:",
     "choices": ["A) 1 inch of rainfall over the watershed",
                 "B) 1 inch of rainfall excess uniformly distributed over the watershed for a specified duration",
                 "C) The maximum possible flood for the watershed",
                 "D) 1 inch of rainfall excess concentrated at the watershed outlet",
                 "E) 1 cubic foot per second of baseflow"]},
    {"q": "30. Which assumption is fundamental to unit hydrograph theory?",
     "choices": ["A) Rainfall intensity varies spatially across the watershed",
                 "B) The watershed response is nonlinear",
                 "C) The principle of superposition (linearity) applies",
                 "D) Baseflow is the dominant component of the hydrograph",
                 "E) Antecedent moisture conditions do not affect runoff"]},
    {"q": "31. To derive a 2-hour unit hydrograph from a 1-hour unit hydrograph, one would use:",
     "choices": ["A) The S-curve (S-hydrograph) method", "B) The Muskingum method",
                 "C) The rational method", "D) Horton's equation",
                 "E) The Penman-Monteith equation"]},
    {"q": "32. The rising limb of a direct runoff hydrograph primarily represents:",
     "choices": ["A) Groundwater contributions increasing over time",
                 "B) An increasing proportion of the watershed contributing surface runoff to the outlet",
                 "C) The recession of interflow from the soil",
                 "D) Evapotranspiration losses decreasing during the storm",
                 "E) Channel storage filling up"]},
    {"q": "33. For a unit hydrograph, the volume under the hydrograph curve must equal:",
     "choices": ["A) The total rainfall depth times the watershed area",
                 "B) 1 inch (or 1 cm) of rainfall excess times the watershed area",
                 "C) The peak discharge times the time of concentration",
                 "D) The baseflow volume plus direct runoff volume",
                 "E) The rational method peak flow times storm duration"]},
    {"q": "34. Lag time (t<sub>L</sub>) of a watershed is defined as the time between:",
     "choices": ["A) The start of rainfall and the start of direct runoff",
                 "B) The centroid of rainfall excess and the peak of the direct runoff hydrograph",
                 "C) The end of rainfall and the end of direct runoff",
                 "D) Peak rainfall intensity and peak discharge",
                 "E) The start of baseflow and the peak discharge"]},
    {"q": "35. In the SCS dimensionless unit hydrograph method, the peak discharge Q<sub>p</sub> is estimated using:",
     "choices": ["A) Q<sub>p</sub> = CIA",
                 "B) Q<sub>p</sub> = 484A / t<sub>p</sub> (in US customary units)",
                 "C) Q<sub>p</sub> = 2.08A / t<sub>p</sub> (in SI units)",
                 "D) Both B and C, depending on the unit system used",
                 "E) Q<sub>p</sub> = nA<sup>0.8</sup>"]},
    {"q": "36. Convolution of a rainfall excess hyetograph with a unit hydrograph produces:",
     "choices": ["A) The baseflow hydrograph",
                 "B) The direct runoff hydrograph for the given storm",
                 "C) The unit hydrograph for a different duration",
                 "D) The infiltration capacity curve",
                 "E) The evapotranspiration time series"]},

    # === FLOOD FREQUENCY ANALYSIS (37-44) ===
    {"q": "37. In flood frequency analysis, the Weibull plotting position formula assigns a return period T to the m-th ranked (largest first) annual maximum flood in a record of n years as:",
     "choices": ["A) T = n / m", "B) T = (n + 1) / m", "C) T = n / (m + 1)",
                 "D) T = (n &minus; 1) / m", "E) T = m / (n + 1)"]},
    {"q": "38. The Log-Pearson Type III distribution is recommended by U.S. federal guidelines for:",
     "choices": ["A) Estimating drought severity",
                 "B) Fitting annual maximum flood series",
                 "C) Modeling daily temperature variations",
                 "D) Predicting groundwater levels",
                 "E) Estimating snow water equivalent"]},
    {"q": "39. A flood with a return period of 25 years has an annual exceedance probability of:",
     "choices": ["A) 0.25 or 25%", "B) 0.10 or 10%", "C) 0.04 or 4%",
                 "D) 0.01 or 1%", "E) 0.004 or 0.4%"]},
    {"q": "40. When plotting flood frequency data on log-probability paper, a good fit to a straight line suggests the data follow a:",
     "choices": ["A) Normal distribution", "B) Uniform distribution",
                 "C) Log-normal distribution", "D) Exponential distribution",
                 "E) Poisson distribution"]},
    {"q": "41. The skewness coefficient in the Log-Pearson Type III distribution primarily affects:",
     "choices": ["A) The mean of the distribution only",
                 "B) The shape and asymmetry of the fitted distribution",
                 "C) The variance of annual peak flows",
                 "D) The plotting position formula used",
                 "E) The number of data points required"]},
    {"q": "42. If a stream gauge has 40 years of annual peak flow records, the largest reliable return period that can reasonably be estimated from the data is approximately:",
     "choices": ["A) 10 years", "B) 40 years", "C) 80 years",
                 "D) 200 years", "E) 500 years"]},
    {"q": "43. Which of the following is an assumption of annual maximum series flood frequency analysis?",
     "choices": ["A) Flood peaks are correlated from year to year",
                 "B) The flood record is stationary (statistical properties do not change over time)",
                 "C) All floods above a certain threshold are included",
                 "D) Only winter floods are analyzed",
                 "E) The drainage area changes significantly over the record period"]},
    {"q": "44. The probability that a 200-year flood will NOT occur in any single year is:",
     "choices": ["A) 0.200", "B) 0.500", "C) 0.900",
                 "D) 0.950", "E) 0.995"]},

    # === FLOOD ROUTING (45-52) ===
    {"q": "45. Flood routing is the procedure used to determine:",
     "choices": ["A) The infiltration rate of a soil",
                 "B) The time and magnitude of flow at a downstream point given an upstream hydrograph",
                 "C) The evapotranspiration rate from a reservoir",
                 "D) The annual flood frequency distribution",
                 "E) The unit hydrograph of a watershed"]},
    {"q": "46. The continuity equation used in hydrologic routing is:",
     "choices": ["A) I &minus; O = dS/dt", "B) I + O = dS/dt", "C) I = O + ET",
                 "D) I &times; O = S", "E) dI/dt = dO/dt"]},
    {"q": "47. The Level Pool (Modified Puls) routing method is most appropriate for:",
     "choices": ["A) Routing flow through a long river reach",
                 "B) Routing flow through a reservoir with a horizontal water surface",
                 "C) Estimating infiltration in a floodplain",
                 "D) Computing unit hydrographs",
                 "E) Determining rainfall excess from a storm"]},
    {"q": "48. In the Level Pool routing method, the storage-indication curve relates:",
     "choices": ["A) Inflow to outflow directly",
                 "B) (2S/&Delta;t + O) to outflow O",
                 "C) Storage to rainfall intensity",
                 "D) Reservoir elevation to precipitation",
                 "E) Channel slope to flow velocity"]},
    {"q": "49. The Muskingum routing method uses two parameters, K and X. The parameter K primarily represents:",
     "choices": ["A) The storage time constant (travel time) of the reach",
                 "B) The weighting factor between inflow and outflow",
                 "C) The Manning's roughness coefficient",
                 "D) The channel bed slope",
                 "E) The watershed area"]},
    {"q": "50. In the Muskingum method, the parameter X typically ranges from:",
     "choices": ["A) 0 to 0.5", "B) 0.5 to 1.0", "C) 1.0 to 2.0",
                 "D) &minus;1.0 to 0", "E) 0 to 10"]},
    {"q": "51. If the Muskingum parameter X = 0, the storage in the reach depends on:",
     "choices": ["A) Inflow only", "B) Outflow only",
                 "C) The average of inflow and outflow",
                 "D) Neither inflow nor outflow",
                 "E) Precipitation minus evaporation"]},
    {"q": "52. Compared to the inflow hydrograph, a hydrograph routed through a reservoir will generally have:",
     "choices": ["A) A higher peak and earlier timing",
                 "B) A lower, attenuated peak and later timing",
                 "C) The same peak but a longer duration",
                 "D) A higher peak and later timing",
                 "E) No change in shape"]},

    # === GROUNDWATER & BASEFLOW (53-57) ===
    {"q": "53. Darcy's Law states that groundwater flow velocity is proportional to:",
     "choices": ["A) The square of the hydraulic gradient",
                 "B) The hydraulic gradient and hydraulic conductivity",
                 "C) The porosity squared",
                 "D) The aquifer thickness only",
                 "E) The precipitation rate over the recharge area"]},
    {"q": "54. A confined aquifer is one that is:",
     "choices": ["A) Open to the atmosphere at its upper boundary",
                 "B) Bounded above and below by impermeable (or very low permeability) layers",
                 "C) Partially saturated at all times",
                 "D) Recharged directly by precipitation on the land surface above it",
                 "E) Always at atmospheric pressure"]},
    {"q": "55. Specific yield of an unconfined aquifer represents:",
     "choices": ["A) The total volume of voids per unit volume of aquifer",
                 "B) The volume of water released from storage per unit decline in water table per unit area",
                 "C) The rate of groundwater flow per unit hydraulic gradient",
                 "D) The ratio of horizontal to vertical hydraulic conductivity",
                 "E) The maximum pumping rate from a well"]},
    {"q": "56. Baseflow in a stream is primarily sustained by:",
     "choices": ["A) Direct precipitation onto the stream surface",
                 "B) Groundwater discharge into the stream",
                 "C) Overland flow from impervious surfaces",
                 "D) Snowmelt occurring on the watershed",
                 "E) Interception by vegetation"]},
    {"q": "57. In baseflow separation, the straight-line method assumes that direct runoff:",
     "choices": ["A) Continues indefinitely after the storm",
                 "B) Ends at the inflection point on the recession limb of the hydrograph",
                 "C) Begins and ends at specified points connected by a straight line beneath the hydrograph",
                 "D) Is equal to baseflow at all times",
                 "E) Is computed using the Muskingum equation"]},

    # === WATERSHED CHARACTERISTICS & APPLICATIONS (58-60) ===
    {"q": "58. The time of concentration of a watershed is defined as:",
     "choices": ["A) The time between the peak rainfall and peak discharge",
                 "B) The time for water to travel from the hydraulically most distant point in the watershed to the outlet",
                 "C) The average residence time of water in the watershed soil",
                 "D) The duration of the design storm",
                 "E) The lag time minus the time to peak"]},
    {"q": "59. Manning's equation relates flow velocity in an open channel to:",
     "choices": ["A) Channel slope, hydraulic radius, and roughness coefficient",
                 "B) Channel slope and rainfall intensity",
                 "C) Hydraulic conductivity and porosity",
                 "D) Evapotranspiration rate and wind speed",
                 "E) Watershed area and curve number"]},
    {"q": "60. A watershed with a high drainage density (total stream length per unit area) would generally have:",
     "choices": ["A) Slower response to rainfall and more infiltration",
                 "B) Faster response to rainfall and higher peak flows",
                 "C) No effect on hydrologic response",
                 "D) Lower peak flows but longer baseflow duration",
                 "E) Higher evapotranspiration rates"]},
]

DEFAULT_METADATA = {
    "title": "Exam Title",
    "institution": "Your Institution",
    "instructor": "Instructor Name",
    "exam_type": "Multiple Choice Examination",
    "header_fields": [
        ["Name: ________________________________________", "Date: ___________________"],
        ["Student ID: ___________________________________", "Version:  A  /  B  /  C  /  D  /  E"],
    ],
    "instructions": (
        "<b>Instructions:</b> Record your answers on the answer sheet provided. "
        "Each question has exactly one correct answer. There is no penalty for guessing."
    ),
    "footer": "<b>END OF EXAM</b>",
    "choice_marker": "letter",
}


def load_metadata_from_json(path):
    p = Path(path)
    with p.open('r', encoding='utf-8') as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"Metadata file must be a JSON object, got {type(data).__name__}")
    # Merge with defaults so omitted fields fall back gracefully
    merged = dict(DEFAULT_METADATA)
    merged.update({k: v for k, v in data.items() if v is not None})
    return merged


def effective_metadata(metadata=None):
    meta = dict(DEFAULT_METADATA)
    if metadata:
        meta.update({k: v for k, v in metadata.items() if v is not None})
    return meta


def save_json_artifact(path, data):
    p = Path(path)
    if p.parent and not p.parent.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('w', encoding='utf-8') as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write('\n')


def questions_artifact(questions_to_use):
    if isinstance(questions_to_use, list) and questions_to_use and isinstance(questions_to_use[0], dict) and 'questions' in questions_to_use[0]:
        return {'sections': questions_to_use}
    if isinstance(questions_to_use, dict) and 'sections' in questions_to_use:
        return questions_to_use
    if isinstance(questions_to_use, dict) and 'questions' in questions_to_use:
        return questions_to_use
    return {'questions': questions_to_use}


# --- Build PDF ---
def build_exam_pdf(sections_or_questions, output_path, metadata=None):
    # Ensure output directory exists (creating it if necessary). This
    # protects against FileNotFoundError when writing to a new path.
    p = Path(output_path)
    parent = p.parent
    if not parent.exists():
        try:
            parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise OSError(f"Unable to create parent directory '{parent}': {e}") from e
    elif not parent.is_dir():
        raise OSError(f"Output parent exists and is not a directory: {parent}")

    doc = SimpleDocTemplate(str(p), pagesize=letter,
        topMargin=0.6*inch, bottomMargin=0.6*inch,
        leftMargin=0.75*inch, rightMargin=0.75*inch)

    meta = effective_metadata(metadata)

    story = []

    # Header
    story.append(Paragraph(reportlab_safe_text(meta["title"]), title_style))
    subtitle_parts = [reportlab_safe_text(meta["institution"]), reportlab_safe_text(meta["instructor"])]
    story.append(Paragraph(" &mdash; ".join(part for part in subtitle_parts if part), subtitle_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph(reportlab_safe_text(meta["exam_type"]), subtitle_style))
    story.append(Spacer(1, 10))

    # Name / ID box
    header_data = meta["header_fields"]
    header_table = Table(header_data, colWidths=[3.6*inch, 3.0*inch])
    header_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOX', (0,0), (-1,-1), 1, colors.black),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 10))

    # Instructions
    story.append(Paragraph(reportlab_safe_text(meta["instructions"]), instructions_style))
    story.append(Spacer(1, 4))
    # If input provided as sections/categories, use them. Otherwise accept
    # a flat list of questions (optionally with 'category' keys) and group
    # into sections. Each section is {'title': str, 'questions': [...]}
    processed_sections = []
    if isinstance(sections_or_questions, dict):
        if 'sections' in sections_or_questions:
            processed_sections = sections_or_questions['sections']
        elif 'questions' in sections_or_questions:
            processed_sections = [{'title': 'Section 1', 'questions': sections_or_questions['questions']}]
    elif isinstance(sections_or_questions, list):
        # list of sections?
        if len(sections_or_questions) > 0 and isinstance(sections_or_questions[0], dict) and 'questions' in sections_or_questions[0]:
            processed_sections = sections_or_questions
        else:
            # flat list of questions: group by 'category' if present
            if any(isinstance(q, dict) and q.get('category') for q in sections_or_questions):
                groups = OrderedDict()
                for q in sections_or_questions:
                    cat = q.get('category') or 'Uncategorized'
                    groups.setdefault(cat, []).append(q)
                for title, qlist in groups.items():
                    processed_sections.append({'title': title, 'questions': qlist})
            else:
                processed_sections = [{'title': 'Section 1', 'questions': sections_or_questions}]
    else:
        processed_sections = [{'title': 'Section 1', 'questions': []}]

    # Render sections and questions in order; number questions sequentially
    question_counter = 1
    choice_label_fn = _get_choice_label_fn(meta)
    for sec in processed_sections:
        sec_title = sec.get('title') or ''
        for q_data in sec.get('questions', []):
            if isinstance(q_data, dict):
                q_text = q_data.get('q') or q_data.get('prompt') or q_data.get('question') or q_data.get('text') or ''
                choices_iter = q_data.get('choices') or q_data.get('options') or []
                raw_qtype = (q_data.get('question_type') or '').lower().replace('_', '').replace(' ', '')
                if not raw_qtype:
                    if choices_iter:
                        raw_qtype = 'multiplechoice'
                    elif q_data.get('pairs'):
                        raw_qtype = 'matching'
                    elif isinstance(q_data.get('answers'), list):
                        raw_qtype = 'fillintheblank'
                    elif q_data.get('code') is not None:
                        raw_qtype = 'code'
                    elif 'answer' in q_data:
                        ans = q_data['answer']
                        if isinstance(ans, bool):
                            raw_qtype = 'truefalse'
                        elif isinstance(ans, (int, float)):
                            raw_qtype = 'calculation'
                        else:
                            raw_qtype = 'shortanswer'
            else:
                q_text = str(q_data)
                choices_iter = []
                raw_qtype = 'multiplechoice'

            # Apply LaTeX conversion before any other text processing
            q_text = latex_to_reportlab(q_text)

            if raw_qtype == 'fillintheblank':
                q_text = q_text.replace('[blank]', '________________________')

            if re.match(r'^\s*\d+\.', str(q_text).strip()) is None:
                q_text = f"{question_counter}. {q_text}"
            question_counter += 1

            block = [Paragraph(reportlab_safe_text(q_text), question_style)]

            # Render stimulus reference if present
            if isinstance(q_data, dict) and q_data.get('has_stimulus'):
                stim_loc = q_data.get('stimulus_location') or ''
                stim_text = f"[Refer to stimulus: {stim_loc}]" if stim_loc else "[Refer to accompanying stimulus]"
                block.append(Paragraph(
                    reportlab_safe_text(stim_text),
                    ParagraphStyle('Stimulus', parent=styles['Normal'],
                                   fontSize=9, leftIndent=18, fontName='Helvetica-Oblique',
                                   textColor=colors.HexColor('#555555')),
                ))

            if raw_qtype == 'truefalse':
                block.append(Paragraph(f"{choice_label_fn(0)}True", choice_style))
                block.append(Paragraph(f"{choice_label_fn(1)}False", choice_style))
            elif raw_qtype == 'shortanswer':
                space_in = _answer_space_inches(q_data.get('answer_space') if isinstance(q_data, dict) else None)
                block.append(Spacer(1, space_in * inch))
            elif raw_qtype == 'matching':
                pairs = q_data.get('pairs') or []
                if pairs:
                    table_data = [['Answer', 'Left', 'Right']]
                    for pair in pairs:
                        if isinstance(pair, (list, tuple)) and len(pair) == 2:
                            table_data.append([
                                '_______',
                                reportlab_safe_text(latex_to_reportlab(str(pair[0]))),
                                reportlab_safe_text(latex_to_reportlab(str(pair[1]))),
                            ])
                    t = Table(table_data, colWidths=[1.0 * inch, 2.75 * inch, 2.75 * inch])
                    t.setStyle(TableStyle([
                        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                        ('FONTSIZE', (0, 0), (-1, -1), 10),
                        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.grey),
                        ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e0e0e0')),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('TOPPADDING', (0, 0), (-1, -1), 3),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                    ]))
                    block.append(t)
            elif raw_qtype == 'calculation':
                unit = reportlab_safe_text(str(q_data.get('unit') or '')) if isinstance(q_data, dict) else ''
                suffix = f' {unit}' if unit else ''
                space_in = _answer_space_inches(q_data.get('answer_space') if isinstance(q_data, dict) else None)
                block.append(Paragraph(f"Answer: {'_' * 40}{suffix}", choice_style))
                if space_in > 0.5:
                    block.append(Spacer(1, (space_in - 0.5) * inch))
            elif raw_qtype == 'code':
                code_text = q_data.get('code') or '' if isinstance(q_data, dict) else ''
                language = q_data.get('language') or '' if isinstance(q_data, dict) else ''
                if language:
                    block.append(Paragraph(
                        reportlab_safe_text(f"[{language}]"),
                        ParagraphStyle('CodeLang', parent=styles['Normal'],
                                       fontSize=8, leftIndent=18, fontName='Helvetica-Oblique',
                                       textColor=colors.HexColor('#888888')),
                    ))
                for code_line in code_text.splitlines():
                    block.append(Paragraph(
                        reportlab_safe_text(code_line) if code_line.strip() else '&nbsp;',
                        code_style,
                    ))
                block.append(Spacer(1, 1.5 * inch))
            elif raw_qtype != 'fillintheblank':
                for j, c in enumerate(choices_iter):
                    raw_choice = str(c).strip()
                    chs = reportlab_safe_text(latex_to_reportlab(raw_choice))
                    # If the choice already has a letter prefix (A) or A.) don't add another
                    if re.match(r'^[A-Za-z][\)\.]\s*', raw_choice):
                        block.append(Paragraph(chs, choice_style))
                    else:
                        block.append(Paragraph(f"{choice_label_fn(j)}{chs}", choice_style))

            story.append(KeepTogether(block))

    # Footer
    story.append(Spacer(1, 20))
    story.append(Paragraph(
        reportlab_safe_text(meta["footer"]),
        ParagraphStyle('EndNote', parent=styles['Normal'],
                       fontSize=10, alignment=TA_CENTER, fontName='Helvetica-Bold')
    ))

    try:
        doc.build(story)
    except Exception as e:
        print(f"Failed to build PDF at {output_path}: {e}")
        raise
    print(f"Exam PDF created at: {output_path}")


def _collect_answer_key(sections_or_questions) -> list[dict]:
    """Flatten sections/questions into a list of dicts that have an answer field."""
    flat: list[dict] = []
    processed_sections = []
    if isinstance(sections_or_questions, dict):
        if 'sections' in sections_or_questions:
            processed_sections = sections_or_questions['sections']
        elif 'questions' in sections_or_questions:
            processed_sections = [{'title': '', 'questions': sections_or_questions['questions']}]
    elif isinstance(sections_or_questions, list):
        if sections_or_questions and isinstance(sections_or_questions[0], dict) and 'questions' in sections_or_questions[0]:
            processed_sections = sections_or_questions
        else:
            processed_sections = [{'title': '', 'questions': sections_or_questions}]
    for sec in processed_sections:
        for q in sec.get('questions', []):
            flat.append(q if isinstance(q, dict) else {'q': str(q)})
    return flat


def build_answer_key_pdf(sections_or_questions, output_path, metadata=None):
    """Generate a compact answer-key PDF from the same question data used by
    ``build_exam_pdf``.

    For each numbered question the key shows:
    - MultipleChoice: the letter of the correct answer
    - TrueFalse: True / False
    - ShortAnswer: the answer string
    - FillInTheBlank: the ordered list of blank answers
    - Matching: the left→right pairs
    - Calculation: the numeric answer, unit, and tolerance if any
    - Code: the expected answer / output string if provided
    """
    p = Path(output_path)
    parent = p.parent
    if not parent.exists():
        try:
            parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise OSError(f"Unable to create parent directory '{parent}': {e}") from e

    doc = SimpleDocTemplate(str(p), pagesize=letter,
        topMargin=0.6 * inch, bottomMargin=0.6 * inch,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch)

    meta = effective_metadata(metadata)
    story = []

    key_title_style = ParagraphStyle('KeyTitle', parent=styles['Title'],
        fontSize=14, spaceAfter=4, alignment=TA_CENTER)
    key_subtitle_style = ParagraphStyle('KeySubtitle', parent=styles['Normal'],
        fontSize=10, spaceAfter=6, alignment=TA_CENTER)
    key_row_style = ParagraphStyle('KeyRow', parent=styles['Normal'],
        fontSize=10, spaceBefore=2, spaceAfter=2)

    story.append(Paragraph(reportlab_safe_text(f"ANSWER KEY — {meta['title']}"), key_title_style))
    story.append(Paragraph(
        reportlab_safe_text(f"{meta['institution']} — {meta['instructor']}"),
        key_subtitle_style,
    ))
    story.append(Spacer(1, 12))
    story.append(Paragraph("<b>CONFIDENTIAL — FOR INSTRUCTOR USE ONLY</b>", key_subtitle_style))
    story.append(Spacer(1, 12))

    flat_qs = _collect_answer_key(sections_or_questions)

    table_data = [['#', 'Type', 'Answer']]
    for i, q_data in enumerate(flat_qs, 1):
        choices_iter = q_data.get('choices') or q_data.get('options') or []
        raw_qtype = (q_data.get('question_type') or '').lower().replace('_', '').replace(' ', '')
        if not raw_qtype:
            if choices_iter:
                raw_qtype = 'multiplechoice'
            elif q_data.get('pairs'):
                raw_qtype = 'matching'
            elif isinstance(q_data.get('answers'), list):
                raw_qtype = 'fillintheblank'
            elif q_data.get('code') is not None:
                raw_qtype = 'code'
            elif 'answer' in q_data:
                ans = q_data['answer']
                if isinstance(ans, bool):
                    raw_qtype = 'truefalse'
                elif isinstance(ans, (int, float)):
                    raw_qtype = 'calculation'
                else:
                    raw_qtype = 'shortanswer'

        if raw_qtype == 'multiplechoice':
            ans = q_data.get('answer')
            if isinstance(ans, int) and 0 <= ans < len(choices_iter):
                answer_str = f"{chr(ord('A') + ans)} — {choices_iter[ans]}"
            elif isinstance(ans, str) and len(ans) == 1 and ans.upper() in 'ABCDE':
                idx = ord(ans.upper()) - ord('A')
                answer_str = f"{ans.upper()}" + (f" — {choices_iter[idx]}" if idx < len(choices_iter) else '')
            else:
                answer_str = str(ans) if ans is not None else '(none)'
        elif raw_qtype == 'truefalse':
            answer_str = str(q_data.get('answer'))
        elif raw_qtype == 'shortanswer':
            answer_str = str(q_data.get('answer') or '')
        elif raw_qtype == 'fillintheblank':
            answers = q_data.get('answers') or []
            answer_str = '; '.join(str(a) for a in answers)
        elif raw_qtype == 'matching':
            pairs = q_data.get('pairs') or []
            answer_str = ', '.join(f"{p[0]}→{p[1]}" for p in pairs if len(p) == 2)
        elif raw_qtype == 'calculation':
            ans = q_data.get('answer')
            unit = q_data.get('unit') or ''
            tol = q_data.get('tolerance')
            parts = [str(ans)]
            if unit:
                parts.append(unit)
            if tol:
                parts.append(f'±{tol}')
            answer_str = ' '.join(parts)
        elif raw_qtype == 'code':
            answer_str = str(q_data.get('answer') or '(see code)')
        else:
            answer_str = str(q_data.get('answer') or '')

        table_data.append([str(i), raw_qtype.capitalize(), answer_str])

    col_widths = [0.5 * inch, 1.25 * inch, 5.0 * inch]
    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d0d0d0')),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.grey),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f8f8')]),
    ]))
    story.append(t)

    story.append(Spacer(1, 20))
    story.append(Paragraph(
        reportlab_safe_text("<b>END OF ANSWER KEY</b>"),
        ParagraphStyle('EndKey', parent=styles['Normal'],
                       fontSize=10, alignment=TA_CENTER, fontName='Helvetica-Bold'),
    ))

    try:
        doc.build(story)
    except Exception as e:
        print(f"Failed to build answer key PDF at {output_path}: {e}")
        raise
    print(f"Answer key PDF created at: {output_path}")


def load_questions_from_json(path):
    p = Path(path)
    with p.open('r', encoding='utf-8') as fh:
        data = json.load(fh)
    # Support multiple JSON layouts:
    # 1) { "sections": [ {"title": "...", "questions": [...]}, ... ] }
    # 2) { "categories": [ ... ] } (alias)  -- if categories is a list of names
    #    and there is a top-level `questions` array, group questions by category name
    # 3) { "questions": [...] } or top-level list of questions
    if isinstance(data, dict) and ('sections' in data or 'categories' in data):
        key = 'sections' if 'sections' in data else 'categories'
        sections_raw = data.get(key, [])

        # If categories is a flat list of names and there's a top-level questions
        # array, group those questions into the named categories.
        if isinstance(sections_raw, list) and all(isinstance(x, str) for x in sections_raw) and isinstance(data.get('questions'), list):
            flat_questions = data.get('questions', [])
            normalized_questions = []
            for it in flat_questions:
                if isinstance(it, str):
                    out = {'q': it}
                else:
                    out = dict(it)
                    out['q'] = it.get('prompt') or it.get('q') or it.get('question') or it.get('text') or ''
                normalized_questions.append(out)

            groups = OrderedDict((name, []) for name in sections_raw)
            for q in normalized_questions:
                cat = q.get('category') or 'Uncategorized'
                if cat in groups:
                    groups[cat].append(q)
                else:
                    # preserve order: create a new bucket for unexpected categories
                    groups.setdefault(cat, []).append(q)

            out_sections = []
            for title, qlist in groups.items():
                out_sections.append({'title': title, 'questions': qlist})
            return {'sections': out_sections}

        # Otherwise process sections as objects (each may include 'questions')
        out_sections = []
        for sec in sections_raw:
            if isinstance(sec, dict):
                title = sec.get('title') or sec.get('name') or sec.get('label') or ''
                qitems = sec.get('questions') or sec.get('items') or []
            else:
                title = str(sec)
                qitems = []

            normalized_qs = []
            for it in qitems:
                if isinstance(it, str):
                    out = {'q': it}
                else:
                    out = dict(it)
                    out['q'] = it.get('prompt') or it.get('q') or it.get('question') or it.get('text') or ''
                normalized_qs.append(out)
            out_sections.append({'title': title, 'questions': normalized_qs})
        return {'sections': out_sections}

    # Fallback: flat list of questions
    if isinstance(data, dict):
        qlist = data.get('questions') or data.get('items') or []
    elif isinstance(data, list):
        qlist = data
    else:
        qlist = []

    normalized = []
    for item in qlist:
        if isinstance(item, str):
            out = {'q': item}
        else:
            out = dict(item)
            out['q'] = item.get('prompt') or item.get('q') or item.get('question') or item.get('text') or ''
        normalized.append(out)
    return {'questions': normalized}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Create exam PDF with optional JSON question bank")
    parser.add_argument('-q', '--questions', help='Path to JSON question bank file', default=None)
    parser.add_argument('-o', '--output', help='Output PDF filename', default='cven4333_exam.pdf')
    parser.add_argument('-m', '--metadata', '--setup', help='Path to JSON exam metadata/setup file', default=None)
    parser.add_argument('--save-questions', help='Write the normalized question artifact used for this PDF', default=None)
    parser.add_argument('--save-setup', help='Write the effective metadata/setup artifact used for this PDF', default=None)
    parser.add_argument('--answer-key', metavar='FILE',
                        help='Also generate an answer-key PDF at this path', default=None)
    parser.add_argument('--choice-marker', choices=['letter', 'circle', 'square'], default=None,
                        help='Style for multiple-choice option markers (default: letter)')
    args = parser.parse_args()
    if args.questions:
        raw = load_questions_from_json(args.questions)
        # raw is a dict with either 'sections' or 'questions'
        if isinstance(raw, dict) and 'sections' in raw:
            questions_to_use = raw['sections']
        elif isinstance(raw, dict) and 'questions' in raw:
            questions_to_use = raw['questions']
        else:
            questions_to_use = raw
    else:
        # No JSON provided: preserve the original section breakdown for the
        # built-in `questions` list so output matches prior behavior.
        original_sections = [
            (0, 8, "Section 1: Hydrologic Cycle and Global Water Balance"),
            (8, 16, "Section 2: Precipitation"),
            (16, 24, "Section 3: Evapotranspiration and Infiltration"),
            (24, 36, "Section 4: Runoff and Unit Hydrograph Theory"),
            (36, 44, "Section 5: Flood Frequency Analysis"),
            (44, 52, "Section 6: Flood Routing"),
            (52, 57, "Section 7: Groundwater and Baseflow"),
            (57, 60, "Section 8: Watershed Characteristics and Applications"),
        ]
        formatted_sections = []
        for start, end, title in original_sections:
            qslice = questions[start:min(end, len(questions))]
            formatted_qs = []
            for item in qslice:
                if isinstance(item, dict):
                    qtext = item.get('q') or item.get('prompt') or ''
                    choices = item.get('choices') or []
                else:
                    qtext = str(item)
                    choices = []
                formatted_qs.append({'q': qtext, 'choices': choices})
            formatted_sections.append({'title': title, 'questions': formatted_qs})
        questions_to_use = formatted_sections

    exam_metadata = load_metadata_from_json(args.metadata) if args.metadata else None

    # Apply CLI choice-marker override
    if args.choice_marker:
        if exam_metadata is None:
            exam_metadata = {}
        exam_metadata['choice_marker'] = args.choice_marker

    if args.save_questions:
        save_json_artifact(args.save_questions, questions_artifact(questions_to_use))
        print(f"Exam question artifact written to: {args.save_questions}")
    if args.save_setup:
        save_json_artifact(args.save_setup, effective_metadata(exam_metadata))
        print(f"Exam setup artifact written to: {args.save_setup}")

    try:
        build_exam_pdf(questions_to_use, args.output, metadata=exam_metadata)
    except Exception as e:
        print(f"Error creating exam PDF: {e}")
        sys.exit(1)

    if args.answer_key:
        try:
            build_answer_key_pdf(questions_to_use, args.answer_key, metadata=exam_metadata)
        except Exception as e:
            print(f"Error creating answer key PDF: {e}")
            sys.exit(1)
