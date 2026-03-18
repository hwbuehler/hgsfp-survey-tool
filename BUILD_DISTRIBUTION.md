# HGSFP Survey Tool - Build & Distribution Guide

## Building the Executable

### Prerequisites
- Python 3.9 or higher
- Virtual environment activated (with all dependencies installed)
- PyInstaller (will be installed automatically by the build script)

### Build Steps

#### Option 1: Using PowerShell (Recommended)
```powershell
.\build_executable.ps1
```

#### Option 2: Using Command Prompt
```cmd
.\build_executable.bat
```

#### Option 3: Manual Build
If you prefer to run PyInstaller directly:
```powershell
# Activate virtual environment
.\Scripts\Activate.ps1

# Install PyInstaller if not already installed
pip install pyinstaller

# Build the executable
pyinstaller gui.spec
```

### Build Output
The executable will be created at:
```
dist/HGSFP-Survey-Tool.exe
```

**Build time:** 5-10 minutes (first build may take longer due to model file size)

## Distribution to Coworkers

### System Requirements
- Windows 7 or later (64-bit)
- ~500 MB free disk space
- No Python installation required

### Distribution Steps

1. **Locate the executable:**
   ```
   dist/HGSFP-Survey-Tool.exe
   ```

2. **Create a distribution package:**
   - Copy `dist/HGSFP-Survey-Tool.exe` to your coworkers
   - Include a `README.txt` with instructions (see below)
   - Optionally include a sample `survey.json` file

3. **Share with coworkers:**
   - Email the executable directly
   - Share via file sharing service (OneDrive, Google Drive, etc.)
   - Place on network drive

### User Instructions for Coworkers

Provide them with these instructions:

```
HGSFP Survey Tool - User Guide
==============================

1. Download HGSFP-Survey-Tool.exe

2. Prepare your survey data:
   - Ensure you have a valid JSON file with survey data
   - See accompanying survey.json example for format

3. Run the tool:
   - Double-click HGSFP-Survey-Tool.exe
   - A window will open with the tool interface

4. Using the tool:
   - Click "Select input file" and choose your survey JSON file
   - Click "Select output path" and choose where to save PDFs
   - Click "Perform analysis!"
   - Wait for the analysis to complete (can take 5-15 minutes)
   - PDFs will be saved to your chosen output folder

5. Output files:
   - results_overall.pdf: Overall survey summary
   - results_morning_lectures.pdf: Morning sessions analysis
   - results_afternoon_lectures.pdf: Afternoon sessions analysis
   - results_industry_lecture.pdf: Industry lecture analysis
   - Results for individual lectures
   - Comments and topic suggestions

Note: The first run may be slower as it loads the language model (~500MB).
```

## Troubleshooting

### Build Issues

**Error: "PyInstaller not found"**
- Solution: Run the build script (it will install PyInstaller automatically)

**Error: "Models directory not found"**
- Solution: Ensure the `models/` directory exists in the project root with `all-MiniLM-L6-v2/`

**Error: "Fonts directory not found"**
- Solution: Ensure the `fonts/` directory exists with DejaVuSans font files

**Build takes too long or out of memory**
- Reason: The sentence-transformers model is ~500MB
- Solution: Ensure you have sufficient disk space and RAM; close other applications

### Runtime Issues (for coworkers)

**"The executable won't start"**
- Solution: Check Windows Defender/antivirus - may need to allow the executable
- Solution: Ensure Windows system is fully updated
- Solution: Try running as Administrator

**"Analysis fails with module import error"**
- Solution: Ensure the executable is not on a network drive with restricted access

**"Analysis is very slow"**
- Expected: First run loads the large language model (~500MB)
- Expected: Subsequent runs will be faster (if model is cached)
- Normal: Analysis can take 5-15 minutes depending on data size

## Optimization Options

### Reduce Executable Size
The current executable is ~600MB due to the sentence-transformers model. This is normal and necessary for comment clustering.

If smaller size is needed, you could:
1. Remove comment clustering feature
2. Use a lighter language model
3. Modify `survey_analyzer.py` as needed

### Code Signing (Optional)
For enterprise distribution, consider signing the executable:
```powershell
signtool sign /f certificate.pfx /p password /t http://timestamp.server.com HGSFP-Survey-Tool.exe
```

## Cleanup

After building, you can remove build artifacts to save space:
```powershell
Remove-Item -Recurse build/ -ErrorAction SilentlyContinue
Remove-Item -Recurse __pycache__/ -ErrorAction SilentlyContinue
```

The only file needed for distribution is: `dist/HGSFP-Survey-Tool.exe`

---

For questions or issues, contact: ad277@uni-heidelberg.de
