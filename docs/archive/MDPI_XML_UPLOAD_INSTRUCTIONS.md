# MDPI XML Upload Instructions

## Problem
MDPI's submission system couldn't automatically extract metadata from your LaTeX file and is asking for an XML file with the front matter.

## Solution

### Step 1: Upload the XML File

1. **I've created `mdpi_metadata.xml`** with all your front matter information
2. **Upload this XML file** to the MDPI submission system in the "Manuscript Files" section
3. The system will use this to populate the submission form automaticallyx

### Step 2: Also Upload Your LaTeX Files

**After uploading the XML, you still need to upload:**
- Your main LaTeX file (`mdpi_version.tex`)
- All 7 figure files (PNG)
- Definitions folder (if needed)

**OR** upload the complete ZIP from Overleaf (as before)

---

## What's in the XML File

The XML file contains:
- ✅ **Title**: DCGAN-Based Dark Skin Image Augmentation...
- ✅ **Author**: Ogwumike Ugochukwu Belusochim Phillips
- ✅ **Affiliation**: Illinois Institute of Technology
- ✅ **Email**: bogwumike@hawk.illinoistech.edu
- ✅ **ORCID**: 0009-0006-0048-5767
- ✅ **Abstract**: Complete abstract text
- ✅ **Keywords**: All 10 keywords

---

## Upload Process

### Option A: Upload XML First (Recommended)

1. **Upload `mdpi_metadata.xml`** first
   - This helps the system populate the form
   - Go to "Manuscript Files" section
   - Click "Upload"
   - Select `mdpi_metadata.xml`

2. **Then upload your LaTeX files**
   - Upload ZIP from Overleaf OR
   - Upload individual files (.tex + figures)

### Option B: Upload Everything Together

1. **Create a new ZIP** containing:
   - `mdpi_metadata.xml`
   - `mdpi_version.tex`
   - All 7 PNG figure files
   - Definitions folder (if needed)

2. **Upload the complete ZIP**

---

## Alternative: Manual Entry

If XML upload doesn't work, you can manually enter the information in the submission form:

**Title:**
```
DCGAN-Based Dark Skin Image Augmentation for Improving Dermatology Classifier Fairness: An End-to-End Clinical Decision Support System
```

**Author:**
```
Ogwumike Ugochukwu Belusochim Phillips
```

**Affiliation:**
```
Illinois Institute of Technology, Chicago, IL, USA
```

**Email:**
```
bogwumike@hawk.illinoistech.edu
```

**ORCID:**
```
0009-0006-0048-5767
```

**Abstract:** (Copy from line 46 of your .tex file)

**Keywords:**
```
medical imaging; generative adversarial networks; fairness in AI; dermatology; skin lesion classification; dataset bias; clinical decision support systems; data augmentation; EfficientNet; demographic equity
```

---

## Troubleshooting

### Issue: "XML file not recognized"
**Solution**: 
- Make sure file is named `mdpi_metadata.xml`
- Check file encoding is UTF-8
- Try uploading as part of ZIP file

### Issue: "Still can't extract metadata"
**Solution**:
- Manually enter information in submission form
- XML is just to help - you can skip it if needed
- Main thing is your LaTeX file compiles correctly

### Issue: "System still asking for XML"
**Solution**:
- Upload the XML file I created
- Or manually fill out the submission form
- The XML is optional - it just helps auto-populate fields

---

## What MDPI Needs

**Essential:**
- ✅ Your LaTeX source file (`mdpi_version.tex`)
- ✅ All figure files (7 PNG files)
- ✅ Properly formatted manuscript

**Helpful (but not required):**
- XML file (helps auto-populate form)
- Definitions folder (if not already in their system)

---

## Next Steps

1. **Upload `mdpi_metadata.xml`** to MDPI system
2. **Upload your LaTeX files** (ZIP or individual files)
3. **Verify** the system extracted information correctly
4. **Continue** with submission form

The XML file I created should resolve the error and help the system populate your submission form automatically! 🚀

