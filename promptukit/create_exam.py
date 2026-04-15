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

# --- Styles ---
styles = getSampleStyleSheet()

title_style = ParagraphStyle('ExamTitle', parent=styles['Title'],
    fontSize=16, spaceAfter=4, alignment=TA_CENTER)
subtitle_style = ParagraphStyle('ExamSubtitle', parent=styles['Normal'],
    fontSize=11, spaceAfter=2, alignment=TA_CENTER)
instructions_style = ParagraphStyle('Instructions', parent=styles['Normal'],
    fontSize=9, spaceAfter=6, leftIndent=18, rightIndent=18, alignment=TA_JUSTIFY)
question_style = ParagraphStyle('Question', parent=styles['Normal'],
    fontSize=10, spaceBefore=8, spaceAfter=2, fontName='Helvetica-Bold')
choice_style = ParagraphStyle('Choice', parent=styles['Normal'],
    fontSize=10, spaceBefore=1, spaceAfter=1, leftIndent=24)
section_style = ParagraphStyle('Section', parent=styles['Heading2'],
    fontSize=12, spaceBefore=14, spaceAfter=6, fontName='Helvetica-Bold',
    textColor=colors.HexColor('#1a1a1a'))

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

# --- Build PDF ---
def build_exam_pdf(sections_or_questions, output_path):
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

    story = []

    # Header
    story.append(Paragraph("CVEN 4333: Engineering Hydrology", title_style))
    story.append(Paragraph("University of Colorado Boulder &mdash; Prof. Joseph Kasprzyk", subtitle_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph("Multiple Choice Examination &mdash; 60 Questions", subtitle_style))
    story.append(Spacer(1, 10))

    # Name / ID box
    header_data = [
        ["Name: ________________________________________", "Date: ___________________"],
        ["Student ID: ___________________________________", "Version:  A  /  B  /  C  /  D  /  E"],
    ]
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
    instructions_text = (
        "<b>Instructions:</b> Record your answers on the Gradescope Bubble Sheet provided. "
        "Fill in the bubble completely using a dark pencil. Erase fully if you change an answer. "
        "Each question has exactly one correct answer (A through E). Each correct answer is worth "
        "1 point (60 points total). There is no penalty for guessing. "
        "You may write on this exam booklet, but only the bubble sheet will be graded. "
        "Calculators are permitted. No notes, textbooks, or electronic devices other than calculators."
    )
    story.append(Paragraph(instructions_text, instructions_style))
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
    for sec in processed_sections:
        sec_title = sec.get('title') or ''
        if sec_title:
            story.append(Paragraph(sec_title, section_style))
        for q_data in sec.get('questions', []):
            if isinstance(q_data, dict):
                q_text = q_data.get('q') or q_data.get('prompt') or q_data.get('question') or q_data.get('text') or ''
                choices_iter = q_data.get('choices') or []
            else:
                q_text = str(q_data)
                choices_iter = []

            if re.match(r'^\s*\d+\.', str(q_text).strip()) is None:
                q_text = f"{question_counter}. {q_text}"
            question_counter += 1

            block = [Paragraph(q_text, question_style)]
            for j, c in enumerate(choices_iter):
                chs = str(c).strip()
                if re.match(r'^[A-Za-z][\)\.\s]+', chs):
                    block.append(Paragraph(chs, choice_style))
                else:
                    block.append(Paragraph(f"{chr(ord('A') + j)}) {chs}", choice_style))
            # KeepTogether prevents a question from breaking across pages
            # ReportLab's KeepTogether may mutate the sequence; pass a tuple
            # to satisfy static type checkers (lists are invariant).
            story.append(KeepTogether(tuple(block)))

    # Footer
    story.append(Spacer(1, 20))
    story.append(Paragraph(
        "<b>END OF EXAM</b> &mdash; Please verify that you have recorded all 60 answers on your Gradescope Bubble Sheet.",
        ParagraphStyle('EndNote', parent=styles['Normal'],
                       fontSize=10, alignment=TA_CENTER, fontName='Helvetica-Bold')
    ))

    try:
        doc.build(story)
    except Exception as e:
        print(f"Failed to build PDF at {output_path}: {e}")
        raise
    print(f"Exam PDF created at: {output_path}")


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
                    prompt = it
                    choices = []
                    category = None
                else:
                    prompt = it.get('prompt') or it.get('q') or it.get('question') or it.get('text') or ''
                    choices = it.get('choices') or it.get('answers') or []
                    category = it.get('category') or None
                normalized_questions.append({'q': prompt, 'choices': choices, 'category': category})

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
                    prompt = it
                    choices = []
                    category = None
                else:
                    prompt = it.get('prompt') or it.get('q') or it.get('question') or it.get('text') or ''
                    choices = it.get('choices') or it.get('answers') or []
                    category = it.get('category') or None
                normalized_qs.append({'q': prompt, 'choices': choices, 'category': category})
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
            prompt = item
            choices = []
            category = None
        else:
            prompt = item.get('prompt') or item.get('q') or item.get('question') or item.get('text') or ''
            choices = item.get('choices') or item.get('answers') or []
            category = item.get('category') or None
        normalized.append({'q': prompt, 'choices': choices, 'category': category})
    return {'questions': normalized}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Create exam PDF with optional JSON question bank")
    parser.add_argument('-q', '--questions', help='Path to JSON question bank file', default=None)
    parser.add_argument('-o', '--output', help='Output PDF filename', default='cven4333_exam.pdf')
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

    try:
        build_exam_pdf(questions_to_use, args.output)
    except Exception as e:
        print(f"Error creating exam PDF: {e}")
        sys.exit(1)
