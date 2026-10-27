# Setting Up MDPI Paper in Overleaf

## Method 1: Start Fresh with MDPI Template (RECOMMENDED)

This is the easiest way to ensure all MDPI files are properly set up:

### Step 1: Create New Project from MDPI Template
1. In Overleaf, click **"New Project"** → **"View All"** or **"Templates"**
2. Search for: **"MDPI"** or **"template for preparing your research article submission to MDPI journals"**
3. Click **"Open as Template"** to create a new project from the template
4. This will automatically include the `Definitions/` folder with `mdpi.cls`

### Step 2: Replace Template Content
1. Open `main.tex` in the new template project
2. Copy ALL content from your `mdpi_version.tex` file
3. Paste it into `main.tex` (replace everything)
4. Upload all your figure files to Overleaf:
   - `class_distribution.png`
   - `gan_architecture.png`
   - `training_curves.png`
   - `baseline_confusion_matrix.png`
   - `gan_confusion_matrix.png`
   - `performance_comparison.png`
   - `app_screenshots.png`

### Step 3: Compile
1. Click **"Recompile"** button
2. Your paper should compile successfully!

---

## Method 2: Add MDPI Files to Existing Project

If you want to keep working in your current Overleaf project:

### Step 1: Download MDPI Template
1. Go to: https://www.mdpi.com/authors/latex
2. Download the LaTeX template ZIP file
3. Extract it locally

### Step 2: Upload Definitions Folder to Overleaf
1. In your Overleaf project, click the **"New Folder"** button (above the file list)
2. Name it: `Definitions`
3. Click on the new `Definitions` folder
4. Click **"Upload"** button
5. Upload these files from the extracted template:
   - `mdpi.cls`
   - `mdpi.bst`
   - Any other files in the `Definitions/` folder

### Step 3: Verify File Structure
Your Overleaf project should now show:
```
Definitions/
  ├── mdpi.cls
  └── mdpi.bst
mdpi_version.tex (or main.tex)
[your figure files]
```

### Step 4: Compile
1. Make sure `mdpi_version.tex` is set as the main document
2. Click **"Recompile"**

---

## Quick Fix: Rename Your File

If Overleaf is looking for `main.tex`, you can rename your file:

1. In Overleaf file list, click the three dots (⋮) next to `mdpi_version.tex`
2. Select **"Rename"**
3. Rename to: `main.tex`
4. Overleaf should automatically recognize it as the main file

---

## Troubleshooting in Overleaf

### Issue: "File `Definitions/mdpi.cls` not found"
**Solution**: Make sure the `Definitions/` folder exists in your Overleaf project root, and `mdpi.cls` is inside it.

### Issue: Figures not showing
**Solution**: 
- Upload all `.png` files to the project root (same level as `main.tex`)
- Make sure filenames match exactly (case-sensitive)

### Issue: Compilation errors after pasting content
**Solution**:
- Check for any special characters that might have been corrupted during copy-paste
- Make sure all `\begin{document}` and `\end{document}` tags are present
- Check that all `\begin{thebibliography}` is closed with `\end{thebibliography}`

### Issue: References not formatting correctly
**Solution**: 
- Since you have inline references (`\begin{thebibliography}`), you don't need BibTeX
- Make sure the bibliography environment is properly closed
- The MDPI template should format references automatically

---

## Recommended: Use Method 1

**Method 1 is strongly recommended** because:
- ✅ All MDPI files are guaranteed to be present
- ✅ No file path issues
- ✅ Template is already configured correctly
- ✅ Less chance of errors

You can always copy your content into the template project!

