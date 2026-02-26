# HGSFP Survey Tool
A Python tool to analyze Likert-style survey data and generate PDF summaries.

**What’s in this repo**
- `survey_analyzer.py`: main script that reads survey JSON and generates PDFs.
- `dummy_survey.json`: sample input with the expected structure.
- `survey_analyzer_original.py`: original version kept for reference.

**Requirements**
- Python 3
- Python packages used by the script: `matplotlib`, `numpy`, `fpdf`, `pypdf`, `sentence-transformers`, `scikit-learn`

**Quick start**
1. Run the analyzer against the sample data:

```powershell
python .\survey_analyzer.py .\dummy_survey.json .\out
```

**Using your own survey data**
1. Prepare a JSON file that matches the structure described below.
2. Run:

```powershell
python .\survey_analyzer.py path\to\your_survey.json path\to\output_dir
```

**Input format (JSON)**
- Top-level keys: `ResultCount` (integer), `Data` (array of response objects)
- Each response object includes:
- `ml_title`, `al_title` (strings)
- Likert ratings (integers 1–5):
- `ml_interesting`, `ml_new`, `ml_expected`, `ml_exciting`, `ml_structure`, `ml_level`
- `al_interesting`, `al_new`, `al_expected`, `al_exciting`, `al_structure`, `al_level`
- `il_attended` (boolean)
- If `il_attended` is `true`, include: `il_interesting`, `il_new`, `il_expected`, `il_exciting`, `il_structure`, `il_level`
- Optional comments:
- `sugg_lectures` with `ml_comment`, `al_comment`, `il_comment` (strings or null)
- `sugg_organization` (string)
- `sugg_topics` (string)
- Other fields in `dummy_survey.json` (for example `HappendAt`, `InstanceId`) are ignored.

**Output**
- PDFs are written to the output directory:
- Per-lecture results for morning and afternoon lectures
- Industry lecture results (if any attended)
- Overall results across all lectures
- Comments and topic suggestions (raw and optionally clustered)
