"""English / Kinyarwanda for the interface: the menu, page and panel titles, card labels,
buttons, filters, table headers and status pills. Longer notes and explanations stay in English.

The language is chosen in the account menu (top right) and kept for the session. English text
passes through unchanged, so the English interface is exactly as written in the screens.

The Kinyarwanda here is a draft awaiting review by a native speaker, like the other Kinyarwanda
labels in the app. Text that is not listed stays in English.
"""

from collections.abc import Callable, Iterable

import streamlit as st

EN, RW = "en", "rw"

KINYARWANDA: dict[str, str] = {
    # menu and pages
    "Plan and diagnose": "Gutegura no gusesengura",
    "Track": "Gukurikirana",
    "Reference": "Ibisobanuro",
    "Learn": "Kwiga",
    "Diagnose and track": "Gusesengura no gukurikirana",
    "Manage": "Gucunga",
    "Overview": "Incamake",
    "District priorities": "Ibyihutirwa mu karere",
    "Sector diagnosis": "Isesengura ry'umurenge",
    "Action plans & progress": "Gahunda z'ibikorwa n'aho bigeze",
    "Caregiver learning": "Amahugurwa y'abarezi",
    "District brief": "Raporo y'akarere",
    "Admin": "Ubuyobozi bwa sisitemu",
    "Data & methods": "Amakuru n'uburyo bukoreshwa",
    # sidebar and account menu
    "Demo role": "Uruhare rw'igerageza",
    "Fictional users, no personal data. A deployment would sign people in.": (
        "Abakoresha b'impimbano, nta makuru bwite. Sisitemu nyayo yasaba abantu kwinjira."
    ),
    "Role": "Uruhare",
    "Planner's district (demo)": "Akarere k'ushinzwe igenamigambi (igerageza)",
    "ECD planning · Rwanda": "Igenamigambi rya ECD · Rwanda",
    "All districts": "Uturere twose",
    "demo account": "konti y'igerageza",
    "Fictional user. Switch role under Demo role in the sidebar.": (
        "Ukoresha w'impimbano. Hindura uruhare muri «Uruhare rw'igerageza» ku ruhande."
    ),
    "Dark mode": "Uburyo bw'umwijima",
    "Light mode": "Uburyo bw'urumuri",
    # page headers
    "Find where new pre-primary places are needed first, and how sure we can be of the order.": (
        "Menya aho imyanya mishya y'amashuri y'incuke ikenewe mbere, n'urwego twizera urutonde."
    ),
    "Understand what is holding early childhood development back.": (
        "Sobanukirwa n'ibidindiza imikurire y'abana bato."
    ),
    "Track decisions, delivery and progress toward {target} by {year}.": (
        "Kurikirana ibyemezo, ishyirwa mu bikorwa n'aho bigeze ugana kuri {target} bitarenze "
        "{year}."
    ),
    "One page for the district council. Use your browser's print, or download the PDF or CSV.": (
        "Urupapuro rumwe rw'inama njyanama y'akarere. Koresha «print» ya mushakisha, cyangwa "
        "ukuremo PDF cyangwa CSV."
    ),
    "Where every number comes from, and how far to trust it.": (
        "Aho buri mubare uturuka, n'urwego wawizera."
    ),
    "Users and roles, data files. Plan decisions are not editable here.": (
        "Abakoresha n'inshingano zabo, amadosiye y'amakuru. Ibyemezo bya gahunda "
        "ntibihindurirwa hano."
    ),
    "{centre} · monthly check-in and your courses": "{centre} · raporo y'ukwezi n'amasomo yawe",
    "{sector} sector · confirm suggested courses, follow up training and centre check-ins.": (
        "Umurenge wa {sector} · emeza amasomo yatanzwe nk'inama, kurikirana amahugurwa "
        "n'amaraporo y'ibigo."
    ),
    # panel titles and subtitles
    "Where the gap is": "Aho icyuho kiri",
    "{year} target outlook": "Icyerekezo cy'intego ya {year}",
    "Pre-primary enrolment, Rwanda": "Abiyandikisha mu mashuri y'incuke, Rwanda",
    "Districts needing attention first": "Uturere dukeneye kwitabwaho mbere",
    "Planner actions": "Ibikorwa by'ushinzwe igenamigambi",
    "Pending decisions in your district's plan": "Ibyemezo bitegerejwe muri gahunda y'akarere kawe",
    "How ranking works": "Uko urutonde rukorwa",
    "Each component is a percentile among the district's sectors.": (
        "Buri gice ni umwanya w'ijanisha (percentile) mu mirenge y'akarere."
    ),
    "Sector ranking and needs": "Urutonde rw'imirenge n'ibikenewe",
    "{name} map": "Ikarita ya {name}",
    "Priority score (higher = act first)": "Amanota y'ibyihutirwa (menshi = gukora mbere)",
    "Why this order": "Impamvu y'uru rutonde",
    "Top three sectors, component by component": "Imirenge itatu ya mbere, igice ku kindi",
    "Key factors affecting ECD in {name}": "Impamvu z'ingenzi zigira ingaruka kuri ECD i {name}",
    "National percentile, 1 = worst · line marks the worst quarter": (
        "Umwanya w'ijanisha mu gihugu, 1 = habi cyane · umurongo werekana kimwe cya kane kibi"
    ),
    "Planner decision": "Icyemezo cy'ushinzwe igenamigambi",
    "The rules suggest; a person decides.": "Amategeko atanga inama; umuntu ni we ufata icyemezo.",
    "Observed vs expected attendance": "Ubwitabire bwagaragaye n'ubwari bwitezwe",
    "What the model sees": "Ibyo icyitegererezo kibona",
    "Top drivers · associated with, not caused by": (
        "Impamvu nyamukuru · bifitanye isano, si byo bibitera"
    ),
    "Evidence and recommended response": "Ibimenyetso n'igisubizo gisabwa",
    "Enrolment trend and what-if": "Uko kwiyandikisha guhinduka, n'igerageza ry'«ese bibaye»",
    "Recent decisions & updates": "Ibyemezo n'impinduka biheruka",
    "From the append-only audit log": "Biva mu gitabo cy'igenzura kitahindurwa",
    "Action plan": "Gahunda y'ibikorwa",
    "Recommendations become plan items; the district planner decides each one.": (
        "Inama zihinduka ingingo za gahunda; ushinzwe igenamigambi mu karere afata icyemezo "
        "kuri buri imwe."
    ),
    "Training tracker": "Ikurikirana ry'amahugurwa",
    "Required LEARN courses by sector · aggregates only": (
        "Amasomo ya LEARN ateganyijwe ku murenge · imibare rusange gusa"
    ),
    "{name} district · pre-primary brief": "Akarere ka {name} · raporo y'amashuri y'incuke",
    "Export": "Gukuramo",
    "Simulated values are left out unless you include them, then labelled.": (
        "Imibare y'igerageza ntishyirwamo keretse uyishyizemo, maze ikerekanwa."
    ),
    "Your courses and progress": "Amasomo yawe n'aho ugeze",
    "Course": "Isomo",
    "Lessons, quiz and certificate": "Amasomo, ikizamini n'icyemezo",
    "Suggested courses to confirm": "Amasomo yatanzwe nk'inama yo kwemeza",
    "Nothing becomes required automatically.": "Nta kintu kiba itegeko mu buryo bwikora.",
    "Required training by centre": "Amahugurwa ateganyijwe ku kigo",
    "Completion, not scores": "Kurangiza, si amanota",
    "Overdue, to follow up": "Ibyarenze igihe, byo gukurikiranwa",
    "Required courses past their due date": "Amasomo ateganyijwe yarengeje igihe",
    "Latest check-ins": "Raporo ziheruka",
    "One row per centre · counts only": "Umurongo umwe ku kigo · imibare gusa",
    "Users": "Abakoresha",
    "Fictional demo accounts and their roles": "Konti z'igerageza z'impimbano n'inshingano zazo",
    "Data files": "Amadosiye y'amakuru",
    # cards
    "Children aged 3–5 (2026)": "Abana bafite imyaka 3–5 (2026)",
    "Children aged 3–5": "Abana bafite imyaka 3–5",
    "Attending pre-primary": "Bitabira amashuri y'incuke",
    "Places needed for {target}": "Imyanya ikenewe kugira ngo hagerwe kuri {target}",
    "Children > 1 km from a school": "Abana bari kure y'ishuri > km 1",
    "Sectors": "Imirenge",
    "Stable top-3 sectors": "Imirenge ihamye mu 3 ya mbere",
    "Places in top 3": "Imyanya mu mirenge 3 ya mbere",
    "All places needed": "Imyanya yose ikenewe",
    "Target": "Intego",
    "Projected {year}": "Biteganyijwe muri {year}",
    "Places a year still needed": "Imyanya igikenewe buri mwaka",
    "Plan items": "Ingingo za gahunda",
    "Required training completed": "Amahugurwa ateganyijwe yarangiye",
    "This month's check-in": "Raporo y'uku kwezi",
    "Attendance, last check-in": "Ubwitabire, raporo iheruka",
    "Required courses done": "Amasomo ateganyijwe yarangiye",
    "Suggested courses": "Amasomo yatanzwe nk'inama",
    "Waiting for your confirmation": "Bitegereje ko ubyemeza",
    "Centres to follow up": "Ibigo byo gukurikirana",
    "Overdue courses": "Amasomo yarengeje igihe",
    "Datasets with real files": "Amakuru afite amadosiye nyayo",
    "Sectors with real boundaries": "Imirenge ifite imbibi nyazo",
    "Peer model": "Icyitegererezo cyo kugereranya",
    "Statuses in use": "Imiterere ikoreshwa",
    "NST2 target": "Intego ya NST2",
    "Pre-primary enrolment": "Abiyandikisha mu mashuri y'incuke",
    "NST2 target: {target} pre-primary enrolment by {year}": (
        "Intego ya NST2: {target} by'abiyandikisha mu mashuri y'incuke bitarenze {year}"
    ),
    "Current ({year})": "Ubu ({year})",
    "{year} milestone": "Intambwe ya {year}",
    "{year} target": "Intego ya {year}",
    "Your {year} target (NST2: {target})": "Intego yawe ya {year} (NST2: {target})",
    "Access": "Kugera ku ishuri",
    "Home environment": "Imibereho yo mu rugo",
    "Places and distance to a school": "Imyanya n'intera igera ku ishuri",
    "Teacher ratios, qualifications, LEARN training": (
        "Umubare w'abana kuri mwarimu, impamyabumenyi, amahugurwa ya LEARN"
    ),
    "Stunting, children under 5": "Igwingira, abana bari munsi y'imyaka 5",
    "Water, sanitation, mothers' education": "Amazi, isuku n'isukura, amashuri y'ababyeyi",
    "Household poverty rate": "Igipimo cy'ubukene mu ngo",
    # table headers
    "Rank": "Umwanya",
    "Sector": "Umurenge",
    "District": "Akarere",
    "Province": "Intara",
    "Not attending": "Batitabira",
    "Children not attending": "Abana batitabira",
    "Places": "Imyanya",
    "Places needed": "Imyanya ikenewe",
    "Rooms": "Ibyumba",
    "> 1 km": "> km 1",
    "Main bottleneck": "Imbogamizi nyamukuru",
    "Bottleneck": "Imbogamizi",
    "Bottlenecks": "Imbogamizi",
    "Top-3 stable": "Ihamye mu 3 ya mbere",
    "{year} status": "Uko bihagaze {year}",
    "Caregivers": "Abarezi",
    "Decision": "Icyemezo",
    "Delivery": "Ishyirwa mu bikorwa",
    "Required assigned": "Ateganyijwe yahawe",
    "Waiting for officer": "Bitegereje umukozi",
    "Centre": "Ikigo",
    "Due": "Itariki ntarengwa",
    "Month": "Ukwezi",
    "Attendance": "Ubwitabire",
    "Challenge": "Ikibazo",
    "Needs follow-up": "Bikeneye gukurikiranwa",
    "Factor": "Impamvu",
    "Evidence": "Ibimenyetso",
    "Level": "Urwego",
    "Suggested action": "Igikorwa gisabwa",
    "Source": "Inkomoko",
    "Status": "Imiterere",
    "Indicator": "Igipimo",
    "Value": "Agaciro",
    "Children 3–5": "Abana 3–5",
    "Attending": "Bitabira",
    "Dataset": "Amakuru",
    "Folder": "Ububiko",
    "Expected files": "Amadosiye ategerejwe",
    "Publisher": "Uwayatangaje",
    "Period": "Igihe",
    "Licence": "Uruhushya",
    "Used by": "Akoreshwa na",
    "In this build": "Muri iyi verisiyo",
    # status pills
    "Supply": "Imyanya",
    "Demand": "Ubwitabire",
    "Capacity": "Ubushobozi",
    "Wellbeing": "Imibereho myiza",
    "At target": "Byageze ku ntego",
    "Unclear": "Ntibisobanutse",
    "On track": "Biri mu nzira nziza",
    "At risk": "Biri mu kaga",
    "Off track": "Ntibiri mu nzira",
    "Stable": "Bihamye",
    "Depends on weights": "Biterwa n'uburemere",
    "Rarely top 3": "Gake mu 3 ba mbere",
    "Pending": "Bitegereje",
    "Not decided": "Ntibirafatirwa icyemezo",
    "Approved": "Byemejwe",
    "Edited": "Byahinduwe",
    "Rejected": "Byanzwe",
    "Planned": "Biteganyijwe",
    "Funded": "Byabonewe amafaranga",
    "Done": "Byarangiye",
    "Required": "Ateganyijwe",
    "Suggested": "Yatanzwe nk'inama",
    "Completed": "Byarangiye",
    "Overdue": "Byarenze igihe",
    "High": "Hejuru",
    "Medium": "Hagati",
    "Low": "Hasi",
    "No water": "Nta mazi",
    # filters, buttons and other controls
    "Target attendance (%)": "Intego y'ubwitabire (%)",
    "Reference year": "Umwaka fatizo",
    "All provinces": "Intara zose",
    "Attendance rate": "Igipimo cy'ubwitabire",
    "Show all districts": "Erekana uturere twose",
    "Open action plans": "Fungura gahunda z'ibikorwa",
    "Priority preset": "Uburyo bw'ibyihutirwa",
    "Reach most children": "Kugera ku bana benshi",
    "Equity first": "Uburinganire mbere",
    "Balanced": "Biringaniye",
    "Custom": "Byihariye",
    "Share not attending": "Igipimo cy'abatitabira",
    "Below similar sectors": "Munsi y'imirenge isa nawo",
    "Poverty": "Ubukene",
    "Add sectors to your action plan": "Ongeramo imirenge muri gahunda yawe y'ibikorwa",
    "Choose sectors": "Hitamo imirenge",
    "Add to plan": "Ongera muri gahunda",
    "Go to action plans": "Jya kuri gahunda z'ibikorwa",
    "Diagnosis target": "Intego y'isesengura",
    "Add to action plan": "Ongera muri gahunda y'ibikorwa",
    "Review in action plans": "Reba muri gahunda z'ibikorwa",
    "All indicators behind the factors": "Ibipimo byose biri inyuma y'izi mpamvu",
    "Sectors to add rooms in": "Imirenge yo kongeramo ibyumba",
    "Rooms a year (from {year})": "Ibyumba buri mwaka (guhera {year})",
    "Top sectors": "Imirenge ya mbere",
    "Plan name": "Izina rya gahunda",
    "Create plan": "Kora gahunda",
    "Plan version": "Verisiyo ya gahunda",
    "Start a new version": "Tangira verisiyo nshya",
    "Create new version": "Kora verisiyo nshya",
    "Add {n} to this plan": "Ongeramo {n} muri iyi gahunda",
    "approve": "Kwemeza",
    "edit": "Guhindura",
    "reject": "Kwanga",
    "Places (for an edit)": "Imyanya (iyo uhinduye)",
    "Reason (required to edit or reject)": "Impamvu (isabwa iyo uhinduye cyangwa wanze)",
    "Record decision": "Bika icyemezo",
    "Delivery status": "Aho ishyirwa mu bikorwa rigeze",
    "planned": "Biteganyijwe",
    "funded": "Byabonewe amafaranga",
    "done": "Byarangiye",
    "Update status": "Hindura aho bigeze",
    "Full audit log for this plan": "Igitabo cyose cy'igenzura cy'iyi gahunda",
    "Include simulated values (labelled SIMULATED)": (
        "Shyiramo imibare y'igerageza (yanditseho SIMULATED)"
    ),
    "Download CSV": "Kuramo CSV",
    "Download PDF": "Kuramo PDF",
    "Your centre's check-ins": "Raporo z'ikigo cyawe",
    "Open a course": "Fungura isomo",
    "Mark as done": "Emeza ko warangije",
    "Submit answers": "Ohereza ibisubizo",
    "Download certificate (PDF)": "Kuramo icyemezo (PDF)",
    "Due date": "Itariki ntarengwa",
    "Note (required to set aside)": "Icyitonderwa (gisabwa iyo ubishyize ku ruhande)",
    "Confirm as required": "Emeza ko ari itegeko",
    "Set aside": "Shyira ku ruhande",
    "User": "Ukoresha",
    "Save": "Bika",
    "Rebuild analysis tables": "Ongera wubake imbonerahamwe z'isesengura",
    # short empty states
    "Every item has a decision.": "Buri ngingo yafatiweho icyemezo.",
    "No plan yet for your district. Start one from the ranking.": (
        "Nta gahunda iraboneka mu karere kawe. Yitangire uhereye ku rutonde."
    ),
    "Plans are made by district planners. Pick a district in Action plans to read one.": (
        "Gahunda zikorwa n'abashinzwe igenamigambi mu turere. Hitamo akarere muri Gahunda "
        "z'ibikorwa kugira ngo uyisome."
    ),
    "Nothing waiting for confirmation.": "Nta kitegereje kwemezwa.",
    "No check-ins yet.": "Nta raporo iraboneka.",
    "No courses yet.": "Nta masomo araboneka.",
    "No plan has been created for this district yet.": "Nta gahunda irakorwa kuri aka karere.",
    "No LEARN data for this district: the pilot runs in Muhanga.": (
        "Nta makuru ya LEARN kuri aka karere: igerageza rikorerwa i Muhanga."
    ),
    "No drivers: the district average is the benchmark.": (
        "Nta mpamvu zigaragazwa: impuzandengo y'akarere ni yo igereranywa."
    ),
    "Nothing recorded yet.": "Nta kirandikwa.",
    "No items for your sector in this plan.": "Nta ngingo z'umurenge wawe muri iyi gahunda.",
}

# Roles by id: "Admin" is also a page title, so roles are kept apart.
ROLES_RW = {
    "district_planner": "Ushinzwe igenamigambi mu karere",
    "national_analyst": "Umusesenguzi ku rwego rw'igihugu",
    "sector_officer": "Umukozi w'umurenge",
    "caregiver": "Umurezi / mwarimu",
    "admin": "Umuyobozi wa sisitemu",
}
DRAFT_NOTE = (
    "Ikinyarwanda ni inyandiko y'agateganyo, izasuzumwa n'umuntu uvuga Ikinyarwanda "
    "kavukire. Inyandiko ndende ziguma mu Cyongereza."
)


def lang() -> str:
    return st.session_state.get("lang", EN)


def t(text: str, **values: object) -> str:
    """`text` in the chosen language; with `values`, a template filled in after translation.
    In English, or for text not listed, the English text."""
    out = KINYARWANDA.get(text, text) if lang() == RW else text
    return out.format(**values) if values else out


def role(role_id: str, english: str) -> str:
    return ROLES_RW.get(role_id, english) if lang() == RW else english


def shown(options: Iterable[str], names: dict[str, str] | None = None) -> Callable[[str], str]:
    """A format_func showing each option in the language now. The labels are worked out here,
    during the page run, because Streamlit (and its test harness) may call format_func later.
    `names` gives labels for options that need more than a lookup."""
    labels = {o: t(o) for o in options} | (names or {})
    return lambda option: labels.get(option, option)


def select(where, label: str, options: list[str], key: str, index: int = 0, **kwargs) -> str:
    """A selectbox whose shown options follow the language. Streamlit keeps the shown text of a
    keyed box when only the language changes, so the box has a key per language; the choice is
    kept in st.session_state[key], as before, so it survives the change and other code reads it
    there."""
    chosen = st.session_state.get(key)
    value = where.selectbox(
        label,
        options,
        index=options.index(chosen) if chosen in options else index,
        key=f"{key}-{lang()}",
        format_func=shown(options),
        **kwargs,
    )
    st.session_state[key] = value
    return value
