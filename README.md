# Dance Show Order Generator

As the president of a 70-member collegiate dance company, I manage our biannual showcase scheduling manually. Since there are many unique constraints to navigate around, creating the show order by hand is a process that used to take days. I built this tool because I wanted to find a way to streamline this process for myself (and future executives of the company!) and try to solve the problem operationally. One of the most important constraints is to try to minimize the amount of 1-dance quick changes throughout the show order.

My manually-built schedule from the previous semester had 10 one-dance quick changes and took me a week to create. This tool generates optimized show orders with 3–7 quick changes and does it in under 15 seconds.

This tool utilizes two types of constraints:
1. Hard constraints --- these are rules that cannot ever be violated (no dancers can appear in back-to-back dances, no shared costume items can be used in back-to-back dances)
2. Soft constraints --- these are preferences that should be optimized (style variety, high-energy pieces at act openings/closings, minimizing quick costume changes)

## How it works:
1. Greedy Hueristic --- candidate show orders are built using a randomized top-k heuristic (each placement is scored locally against the style variety, costume spacing, and quick-change risks)
2. Local search improvement --- performs random swap hill-climbing over movable positions (the finale must stay at the end), only accepts changes that reduce the penalty score

Multiple show order candidates are generated within a time budget and ranked by score. The top 3 valid, distinct orderings are returned to the user, with quick-change dancers highlighted in red. Includes a loading animation during generation (this is decorative for UX, does not reflect true progress time).

## Scoring Penalties:
- Style penalty: +10 for each consecutive dances with the same style
- Quick change penalty: +70 per dancer with only a 1-dance gap
- Shared costume penalty: +45 / gap for shared costume items
- Highlight placement: +80 if opener/closer is not a highlight
- Finale placement: pinned to end of Act 2 (this is a hard constraint)

I determined the weights operationally by considering how difficult the negative actions would be to deal with. For example, the show is more entertaining when the genres of dances are shuffled, but it is way more important for the well-being of company dancers to attempt to minimize the amount of dancers with only one dance to change costumes and rest.

I knew that my audience would be future executives of my dance company, so I wanted to make the complex algorithm accessible for non-technical users. As such, the web interface provides instructions about the expected JSON format and the ability to download a sample JSON file.

## Usage: 
- Upload a JSON file with your dances
- Required fields per dance: name, dancers (list), style, costumes (list), isHighlight (true/false, bool, to be indicated by opinion ahead of time), isFinale (true/false, bool, this is only for the senior or exec dance, depending on the semester)
- streamlit run app.py

## Results:
This tool was validated against real roster data from a recent showcase (I anonymized names). The best manually-built schedule I made had 10 one-dance quick changes. Generated schedules consistently produced 3–7,
with no hard constraint violations.

This tool returns 3 distinct valid show orders so executives can choose based on factors outside of the algorithm, such as audience experience or dancer time conflicts.

## What I would do to improve this system:
- Add configurable weight sliders so executives can adjust the weights depending on their own preferences/experiences
- Potentially change to a simulated annealing system because the hill-climber can get stuck in local minima
- Create a PDF export function



### Built with: Python, Streamlit
### Created as a class project to address to a real, personal operational problem
