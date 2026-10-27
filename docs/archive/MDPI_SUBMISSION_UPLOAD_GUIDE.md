# MDPI Submission Upload Guide

## What to Upload for LaTeX Submission

### Option 1: Upload Complete Project (RECOMMENDED)

**Create a ZIP file containing:**

```
Your_Submission.zip
├── mdpi_version.tex          ← Main LaTeX file
├── Definitions/              ← MDPI template folder
│   ├── mdpi.cls
│   ├── mdpi.bst
│   ├── journalnames.tex
│   └── (other MDPI files)
├── class_distribution.png    ← All 7 figure files
├── gan_architecture.png
├── training_curves.png
├── baseline_confusion_matrix.png
├── gan_confusion_matrix.png
├── performance_comparison.png
└── app_screenshots.png
```

**Steps:**
1. In Overleaf, click **"Menu"** (top left)
2. Select **"Download"** → **"Source"**
3. This downloads a ZIP with all files
4. Upload this ZIP to MDPI submission system

---

### Option 2: Upload Individual Files

If the system allows multiple file uploads:

**Upload separately:**
1. **Main manuscript**: `mdpi_version.tex`
2. **Figure files**: Upload all 7 PNG files individually
3. **Definitions folder**: Upload as a ZIP or folder

---

## What NOT to Upload

❌ **Do NOT include:**
- Supplementary materials (upload separately if needed)
- Large data files
- Model weights (.h5 files)
- Python scripts
- README files
- Any files not needed for compilation

---

## Step-by-Step Upload Process

### Step 1: Prepare Your Files

**In Overleaf:**
1. Make sure your project compiles successfully
2. Click **"Menu"** → **"Download"** → **"Source"**
3. This creates a ZIP file with:
   - Your .tex file
   - All figure files
   - Definitions folder (if present)
   - Any other necessary files

### Step 2: Verify ZIP Contents

**Check that your ZIP contains:**
- ✅ `mdpi_version.tex` (or `main.tex` if you renamed it)
- ✅ All 7 PNG figure files
- ✅ `Definitions/` folder with `mdpi.cls` and other files
- ❌ No supplementary materials 
- ❌ No large data files

### Step 3: Upload to MDPI

**In MDPI submission system:**
1. Go to **"Manuscript Files"** section
2. Click **"Upload"** or **"Choose File"**
3. Select your ZIP file
4. Wait for upload to complete
5. The system will automatically extract and process files

---

## Important Notes

### File Size Limits
- MDPI typically allows up to **50 MB** for manuscript files
- Your ZIP should be much smaller (usually 5-20 MB)
- If too large, compress images or remove unnecessary files

### File Format
- **Main file**: Must be `.tex` (LaTeX source)
- **Figures**: PNG, PDF, or JPG (PNG recommended)
- **Compression**: ZIP format

### What MDPI System Does
- Automatically extracts files from ZIP
- Identifies main .tex file
- Extracts author information
- Processes figures and tables
- May attempt to compile (but this is optional)

---

## Troubleshooting

### Issue: "File too large"
**Solution**: 
- Compress PNG files (reduce resolution if > 300 DPI is not needed)
- Remove any unnecessary files
- Use PDF for figures if smaller

### Issue: "Cannot find main file"
**Solution**:
- Ensure `mdpi_version.tex` is in the root of ZIP
- Or rename to `main.tex` before creating ZIP

### Issue: "Missing Definitions folder"
**Solution**:
- Make sure `Definitions/` folder is included in ZIP
- Contains `mdpi.cls` and other required files

### Issue: "Figures not found"
**Solution**:
- Ensure all 7 PNG files are in the ZIP root (same level as .tex file)
- Check filenames match exactly (case-sensitive)

---

## Recommended Approach

**Best Practice:**
1. **Use Overleaf's "Download Source"** feature
   - This automatically includes all necessary files
   - Maintains proper file structure
   - Includes Definitions folder if present

2. **Verify before uploading:**
   - Extract ZIP locally
   - Check all files are present
   - Verify file sizes are reasonable

3. **Upload the ZIP:**
   - Single ZIP file is easiest
   - MDPI system handles extraction
   - Reduces upload errors

---

## After Upload

Once uploaded:
1. **Check extraction**: Verify system extracted files correctly
2. **Review metadata**: Check author information was extracted
3. **Verify figures**: Ensure all figures are recognized
4. **Continue submission**: Proceed to next steps in submission form

---

## Quick Checklist

Before uploading ZIP:
- [ ] Project compiles in Overleaf without errors
- [ ] All 7 figure files are included
- [ ] Definitions folder is included (if needed)
- [ ] No supplementary materials in ZIP
- [ ] File size is reasonable (< 50 MB)
- [ ] Main .tex file is named correctly (mdpi_version.tex or main.tex)

---

**You're ready to upload!** 🚀

