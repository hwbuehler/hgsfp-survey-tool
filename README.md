# HGSFP Survey Tool

A Python tool to analyze Likert-style survey data and generate comprehensive PDF reports with graphs, statistics, and clustered comments.

## Overview

This tool automates the analysis of HGSFP Graduate Days survey responses. It:
- Processes survey data in JSON format
- Generates Likert scale visualizations with distribution analysis
- Calculates statistical summaries (mean ± standard deviation)
- Clusters open-ended comments using sentence transformers
- Creates professional PDF reports

## Quick Start

### For End Users (No coding required!)

See [BUILD_DISTRIBUTION.md](BUILD_DISTRIBUTION.md) for instructions on:
- **Building a standalone executable** — Create a single `.exe` file to distribute to coworkers
- **Running the GUI application** — No Python installation needed

### For Developers

#### Prerequisites
- Python 3.9+
- Virtual environment with dependencies installed

#### Run via Command Line

```powershell
# Activate virtual environment
.\Scripts\Activate.ps1

# Run analysis
python .\survey_analyzer.py path\to\survey.json path\to\output_dir
```

#### Run via GUI

```powershell
python .\gui.py
```

## Project Structure

- `gui.py` — GUI application (customtkinter-based)
- `survey_analyzer.py` — Core analysis engine
- `survey_analyzer_original.py` — Original implementation (reference)
- `dummy_survey.json` — Sample input file with expected structure
- `fonts/` — DejaVu fonts for PDF rendering
- `models/all-MiniLM-L6-v2/` — Sentence transformer model for comment clustering

## Input Format (JSON)

Your survey JSON file must have this structure:

```json
{
  "ResultCount": 42,
  "Data": [
    {
      "ml_title": "Lecture Title or DnA",
      "al_title": "Afternoon Lecture or DnA",
      "il_title": "Industry Lecture or DnA",
      "ml_interesting": 4,
      "ml_new": 3,
      "ml_expected": 5,
      "ml_exciting": 4,
      "ml_structure": 5,
      "ml_level": 4,
      "al_interesting": 4,
      "al_new": 3,
      "al_expected": 5,
      "al_exciting": 4,
      "al_structure": 5,
      "al_level": 4,
      "il_interesting": 5,
      "il_new": 4,
      "il_expected": 5,
      "il_exciting": 5,
      "il_structure": 4,
      "il_level": 4,
      "sugg_lectures": {
        "ml_comment": "Great content!",
        "al_comment": null,
        "il_comment": "Very informative."
      },
      "sugg_organization": "Better break times would be helpful",
      "sugg_topics": "More on machine learning applications"
    }
  ]
}
```

### Key Notes:
- **Lecture titles**: Use `"DnA"` (Did not Attend) for sessions the respondent didn't attend
- **Ratings**: Integers from 1–5 for all Likert scale questions
- **Comments**: Can be strings or `null`; use `"DnA"` in title fields instead of a separate attendance boolean
- **Extra fields**: Additional fields in your JSON are ignored (e.g., `HappenedAt`, `InstanceId`)

## Output

PDFs are generated in your specified output directory:
- `results_overall.pdf` — Overall survey summary across all lectures
- `results_morning_lectures.pdf` — Aggregated morning lecture analysis
- `results_afternoon_lectures.pdf` — Aggregated afternoon lecture analysis
- `results_<lecture_name>.pdf` — Individual lecture results (one per lecture)
- Comments and topic suggestions (raw + clustered by similarity)

Each PDF includes:
- Stacked bar charts showing Likert distribution (%)
- Mean and standard deviation for each question
- Comments and suggestions organized by topic cluster

## Dependencies

- **matplotlib** — Chart generation
- **numpy** — Numerical computations
- **fpdf** — PDF creation
- **pypdf** — PDF manipulation
- **sentence-transformers** — Comment clustering
- **scikit-learn** — Clustering algorithms
- **customtkinter** — Modern GUI framework (optional, for GUI only)
- **CTkMessagebox** — Dialog boxes for GUI

## Building an Executable

To distribute this tool to coworkers without requiring Python installation:

**See [BUILD_DISTRIBUTION.md](BUILD_DISTRIBUTION.md)** for complete instructions on:
- Building a single executable with PyInstaller
- Creating a distribution package
- Troubleshooting deployment issues

Quick start:
```powershell
.\build_executable.ps1
```

The `.exe` file will be created at `dist/HGSFP-Survey-Tool.exe`

## License

See [LICENSE](LICENSE) file.

## Contact

Created by Hagen-Wolfgang Buehler  
Email: ad277@uni-heidelberg.de  
Repository: https://github.com/hwbuehler/hgsfp-survey-tool
