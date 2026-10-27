# MDPI Template Setup Instructions

## Problem
The LaTeX compiler cannot find `Definitions/mdpi.cls` which is required to compile your MDPI paper.

## Solution: Download MDPI Template Files

### Step 1: Download the MDPI LaTeX Template

1. Go to MDPI's LaTeX template page: **https://www.mdpi.com/authors/latex**
2. Click "Download LaTeX Template" button
3. This will download a ZIP file containing:
   - `Definitions/` folder with `mdpi.cls` and other required files
   - Example template files

### Step 2: Extract and Place Files

1. Extract the downloaded ZIP file
2. **Copy the entire `Definitions/` folder** to your project directoDefinitionsry:
   ```
   AI-Powered-Skin-Disease-Diagnosis-with-GAN-Based-Dark-Skin-Image-Augmentation/
   ├── Definitions/
   │   ├── mdpi.cls
   │   ├── mdpi.bst
   │   └── (other MDPI files)
   ├── mdpi_version.tex
   ├── references.bib
   └── (your other files)
   ```

### Step 3: Verify File Structure

Your project should have:
```
Definitions/
  ├── mdpi.cls          ← Required class file
  ├── mdpi.bst          ← BibTeX style file (if using BibTeX)
  └── logo-mdpi.png     ← Optional logo file
```

### Step 4: Compile

**For local compilation:**
```bash
pdflatex mdpi_version.tex
pdflatex mdpi_version.tex
```

**For online compilers (Overleaf, etc.):**
1. Upload your entire project folder including the `Definitions/` folder
2. Make sure `mdpi_version.tex` is set as the main file
3. Compile

## Alternative: If Using Overleaf

If you're using Overleaf:

1. Create a new project from the MDPI template on Overleaf
2. Go to: https://www.overleaf.com/latex/templates/template-for-preparing-your-research-article-submission-to-mdpi-journals/rvfhdgfzhpmx
3. Upload your `mdpi_version.tex` content to replace the template content
4. The `Definitions/` folder will already be present

## Troubleshooting

### Error: "File `Definitions/mdpi.cls' not found"
- **Cause**: The `Definitions/` folder is missing or in the wrong location
- **Fix**: Download the template and ensure `Definitions/mdpi.cls` exists in your project root

### Error: "File `main.tex` not found" 
- **Cause**: Your compiler is looking for `main.tex` instead of `mdpi_version.tex`
- **Fix**: 
  - Rename `mdpi_version.tex` to `main.tex`, OR
  - Configure your compiler to use `mdpi_version.tex` as the main file

### Online Compiler Issues
If using an online LaTeX compiler:
- Make sure you upload ALL files including the `Definitions/` folder
- Some online compilers require you to zip the entire project and upload it
- Check that file paths are preserved correctly

## Important Notes

⚠️ **You MUST use the official MDPI template files** - MDPI requires papers to be compiled with their official class file for proper formatting and submission requirements.

The `Definitions/mdpi.cls` file is proprietary and cannot be shared directly - you must download it from MDPI's official website.

