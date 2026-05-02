import streamlit as st


st.markdown(
    """
    <style>
    .stApp {
        background-color: #0f1117;
    }

    h1, h2, h3, h4, h5, h6,
    p, li, label {
        color: white !important;
    }

    .stMarkdown, .stMarkdown p, .stMarkdown div {
        color: white !important;
    }

    .stButton > button,
    .stDownloadButton > button,
    .stFileUploader button {
        background-color: #a855f7 !important;
        color: white !important;
        border-radius: 8px;
        border: none;
        font-weight: 600;
    }

    .stButton > button:hover,
    .stDownloadButton > button:hover,
    .stFileUploader button:hover {
        background-color: #9333ea !important;
        color: white !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)





st.title("PB Dance Show Order Generator")

st.markdown("""
### Instructions

Please upload a JSON file in the following format:

Each dance must include:
- title (string)
- list of dancers' names (list of strings)
- style (string)
- shared costume items (list of strings, please use "None" if the dance does not use a shared item)
- isHighlight (true/false) -> For dances that could be ideal for openers/closers
- isFinale (true/false, this is ONLY for the senior dance or exec dance)


""")



example_json = """[
  {
    "name": "Dance 1",
    "dancers": ["A", "B", "C"],
    "style": "Contemporary",
    "costumes": ["Red Tops"],
    "isHighlight": false,
    "isFinale": false
  },
  {
    "name": "Finale",
    "dancers": ["A", "D", "E"],
    "style": "Jazz",
    "costumes": ["None"],
    "isHighlight": true,
    "isFinale": true
  }
]"""





st.subheader("Example JSON")

st.code(example_json, language="json")


st.download_button(
    "Download Example JSON",
    example_json,
    file_name="example.json"
)



import json
import random
import copy
import time

# -----------------------------
# Helpers
# -----------------------------

def count_shared(list1, list2):
    return len(set(list1) & set(list2))


def shared_costumes(c1, c2):
    set1 = {c for c in c1 if c != "None"}
    set2 = {c for c in c2 if c != "None"}
    return len(set1 & set2)


def split_into_acts(schedule):
    mid = len(schedule) // 2
    return schedule[:mid], schedule[mid:]


def valid_pair(prev, nxt):
    if prev is None:
        return True

    if count_shared(prev["dancers"], nxt["dancers"]) > 0:
        return False

    if shared_costumes(prev["costumes"], nxt["costumes"]) > 0:
        return False

    return True


def is_valid_schedule(schedule):
    act1, act2 = split_into_acts(schedule)

    for act in [act1, act2]:
        for i in range(len(act) - 1):
            if not valid_pair(act[i], act[i + 1]):
                return False

    return True


# -----------------------------
# Quick change detection
# -----------------------------

def find_quick_changes(schedule):
    act1, act2 = split_into_acts(schedule)
    quick_flags = {}

    def process_act(act, offset):
        dancer_positions = {}

        for i, dance in enumerate(act):
            for dancer in dance["dancers"]:
                dancer_positions.setdefault(dancer, []).append(i)

        for dancer, positions in dancer_positions.items():
            for i in range(len(positions) - 1):
                if positions[i + 1] - positions[i] == 2:
                    quick_flags.setdefault(positions[i] + offset, set()).add(dancer)
                    quick_flags.setdefault(positions[i + 1] + offset, set()).add(dancer)

    process_act(act1, 0)
    process_act(act2, len(act1))

    return quick_flags


def count_quick_changes(schedule):
    return sum(len(v) for v in find_quick_changes(schedule).values()) // 2


# -----------------------------
# Scoring
# -----------------------------

def score_schedule(schedule):
    act1, act2 = split_into_acts(schedule)
    score = 0

    def score_act(act):
        s = 0

        STYLE_WEIGHT = 10
        QUICK_CHANGE_WEIGHT = 70
        COSTUME_DISTANCE_WEIGHT = 45

        # Style flow
        for i in range(len(act) - 1):
            if act[i]["style"] == act[i + 1]["style"]:
                s += STYLE_WEIGHT

        # Costume distance penalty
        costume_positions = {}

        for i, dance in enumerate(act):
            for costume in dance["costumes"]:
                if costume != "None":
                    costume_positions.setdefault(costume, []).append(i)

        for costume, positions in costume_positions.items():
            for i in range(len(positions) - 1):
                gap = positions[i + 1] - positions[i]
                if gap > 0:
                    s += int(COSTUME_DISTANCE_WEIGHT / gap)

        # Quick-change penalty
        dancer_positions = {}

        for i, dance in enumerate(act):
            for dancer in dance["dancers"]:
                dancer_positions.setdefault(dancer, []).append(i)

        for dancer, positions in dancer_positions.items():
            for i in range(len(positions) - 1):
                if positions[i + 1] - positions[i] == 2:
                    s += QUICK_CHANGE_WEIGHT

        return s

    score += score_act(act1)
    score += score_act(act2)

    # Highlight rules
    def score_highlights(act, second=False):
        s = 0

        if not act[0]["isHighlight"]:
            s += 80

        if not second and not act[-1]["isHighlight"]:
            s += 80

        if second and act[-1]["isHighlight"]:
            s -= 20

        return s

    score += score_highlights(act1, False)
    score += score_highlights(act2, True)

    return score


# -----------------------------
# Candidate generation
# -----------------------------

def local_choice_score(path, dance, index, act_start):
    score = 0

    prev = path[-1] if path and index != act_start else None

    if prev and dance["style"] == prev["style"]:
        score += 10

    # Penalize 1-dance quick changes
    if index - 2 >= act_start:
        two_back = path[-2]
        if count_shared(two_back["dancers"], dance["dancers"]) > 0:
            score += 70 * count_shared(two_back["dancers"], dance["dancers"])

    # Prefer farther costume spacing
    for past_index in range(act_start, len(path)):
        past = path[past_index]
        overlap = shared_costumes(past["costumes"], dance["costumes"])
        if overlap > 0:
            gap = index - past_index
            score += int(45 / gap) * overlap

    # Prefer highlights in key spots
    if dance.get("isHighlight", False):
        score -= 20

    return score


def build_greedy_candidate(dances):
    finale_list = [d for d in dances if d.get("isFinale", False)]
    others = [d for d in dances if not d.get("isFinale", False)]

    if len(finale_list) != 1:
        raise ValueError("Exactly one finale required")

    finale = finale_list[0]
    total_len = len(dances)
    mid = total_len // 2

    path = []
    remaining = others.copy()

    for index in range(total_len - 1):
        act_start = 0 if index < mid else mid
        prev = path[-1] if path and index != act_start else None

        valid_options = [d for d in remaining if valid_pair(prev, d)]

        if not valid_options:
            return None

        # If this is the dance before finale, make sure it can lead into finale
        if index == total_len - 2:
            valid_options = [d for d in valid_options if valid_pair(d, finale)]
            if not valid_options:
                return None

        scored = [
            (local_choice_score(path, d, index, act_start) + random.randint(0, 20), d)
            for d in valid_options
        ]

        scored.sort(key=lambda x: x[0])

        # Pick from top few instead of always best, to create variety
        top_k = scored[:min(4, len(scored))]
        chosen = random.choice(top_k)[1]

        path.append(chosen)
        remaining.remove(chosen)

    schedule = path + [finale]

    if is_valid_schedule(schedule):
        return schedule

    return None


# -----------------------------
# Local improvement
# -----------------------------

def improve_schedule(schedule, max_swaps=500):
    best = copy.deepcopy(schedule)
    best_score = score_schedule(best)

    n = len(best)

    # Do not move finale
    movable_indices = list(range(n - 1))

    for _ in range(max_swaps):
        candidate = copy.deepcopy(best)

        i, j = random.sample(movable_indices, 2)
        candidate[i], candidate[j] = candidate[j], candidate[i]

        if not is_valid_schedule(candidate):
            continue

        s = score_schedule(candidate)

        if s < best_score:
            best = candidate
            best_score = s

    return best, best_score


# -----------------------------
# Generate top 3 schedules
# -----------------------------

def generate_top_schedules(dances, num_solutions=3, time_budget=12):
    start = time.time()
    solutions = []
    seen = set()

    def signature(schedule):
        return tuple(d["name"] for d in schedule)

    while time.time() - start < time_budget:
        candidate = build_greedy_candidate(dances)

        if candidate is None:
            continue

        improved, score = improve_schedule(candidate, max_swaps=300)
        sig = signature(improved)

        if sig not in seen:
            seen.add(sig)
            solutions.append((improved, score, True))

    solutions.sort(key=lambda x: x[1])

    if len(solutions) >= num_solutions:
        return solutions[:num_solutions]

    return solutions


# -----------------------------
# Debug
# -----------------------------

def debug_schedule(schedule):
    act1, act2 = split_into_acts(schedule)

    print("\n--- DEBUG CHECK ---\n")

    def check(act, name):
        print(name)

        for i in range(len(act) - 1):
            shared_dancers = set(act[i]["dancers"]) & set(act[i + 1]["dancers"])
            shared_costume_items = (
                {c for c in act[i]["costumes"] if c != "None"} &
                {c for c in act[i + 1]["costumes"] if c != "None"}
            )

            if shared_dancers:
                print(f"⚠️ Dancer conflict: {act[i]['name']} -> {act[i+1]['name']}: {shared_dancers}")

            if shared_costume_items:
                print(f"⚠️ Costume conflict: {act[i]['name']} -> {act[i+1]['name']}: {shared_costume_items}")

        print()

    check(act1, "Act 1")
    check(act2, "Act 2")


# -----------------------------
# Print
# -----------------------------

def print_schedule(schedule):
    act1, act2 = split_into_acts(schedule)
    quick_flags = find_quick_changes(schedule)

    def format_dancers(dancers, index):
        flagged = quick_flags.get(index, set())
        return ", ".join([f"<span style='color:red; font-weight:bold;'>{d}*</span>" if d in flagged else d for d in dancers])

    def format_costumes(costumes):
        if costumes == ["None"]:
            return "None"
        return ", ".join(costumes)

    print("\n===== ACT 1 =====\n")
    for i, dance in enumerate(act1):
        print(f"{i + 1}. {dance['name']} ({dance['style']})")
        print(f"   Dancers: {format_dancers(dance['dancers'], i)}")
        print(f"   Costumes: {format_costumes(dance['costumes'])}\n")

    print("\n--- INTERMISSION ---\n")

    offset = len(act1)

    print("\n===== ACT 2 =====\n")
    for i, dance in enumerate(act2):
        print(f"{i + 1}. {dance['name']} ({dance['style']})")
        print(f"   Dancers: {format_dancers(dance['dancers'], i + offset)}")
        print(f"   Costumes: {format_costumes(dance['costumes'])}\n")

    print("\n* = quick change (1 dance gap)\n")


# -----------------------------
# Runner
# -----------------------------

def run_scheduler(json_data):
    dances = json.loads(json_data)

    solutions = generate_top_schedules(dances, num_solutions=3, time_budget=12)

    if not solutions:
        st.markdown("<b>No valid schedules found.</b>", unsafe_allow_html=True)
        return

    output = ""

    for idx, (schedule, score, perfect) in enumerate(solutions, 1):
        output += f"<h2>Option {idx}</h2>"

        act1, act2 = split_into_acts(schedule)
        quick_flags = find_quick_changes(schedule)

        def format_dancers(dancers, index):
            flagged = quick_flags.get(index, set())
            return ", ".join([
                f"<span style='color:red; font-weight:bold;'>{d}*</span>"
                if d in flagged else d
                for d in dancers
            ])

        # ACT 1
        output += "<h3>Act 1</h3>"
        for i, dance in enumerate(act1):
            output += f"<b>{i+1}. {dance['name']}</b><br>"
            output += f"Dancers: {format_dancers(dance['dancers'], i)}<br>"
            output += f"Costumes: {', '.join(dance['costumes'])}<br><br>"

        # INTERMISSION
        output += "<hr><b>INTERMISSION</b><hr>"

        # ACT 2
        offset = len(act1)
        output += "<h3>Act 2</h3>"
        for i, dance in enumerate(act2):
            output += f"<b>{i+1}. {dance['name']}</b><br>"
            output += f"Dancers: {format_dancers(dance['dancers'], i + offset)}<br>"
            output += f"Costumes: {', '.join(dance['costumes'])}<br><br>"

        # FOOTER INFO
        output += f"<p><b>Score:</b> {score}<br>"
        output += f"<b>Quick changes:</b> {count_quick_changes(schedule)}</p>"

        output += "<hr>"

    output += "<p><b>* = quick change (1 dance gap)</b></p>"

    st.markdown(output, unsafe_allow_html=True)



uploaded_file = st.file_uploader("Upload your JSON file", type=["json"])

if uploaded_file is not None:
    json_data = uploaded_file.read().decode("utf-8")

    st.subheader("Generated Show Orders")

    progress = st.progress(0)
    status = st.empty()

    status.text("Starting scheduler...")

    # fake progress animation (while your algorithm runs)
    for i in range(30):
        progress.progress(i + 1)
        time.sleep(0.03)

    status.text("Optimizing schedules...")

    run_scheduler(json_data)

    progress.empty()
    status.success("Done!")
