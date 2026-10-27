# Draw.io Quick Reference - DCGAN Architecture

## 🚀 **5-Minute Quick Start**

### **Step 1: Open Draw.io**
- Go to: https://app.diagrams.net/
- Click "Create New Diagram"
- Choose "Blank Diagram"

### **Step 2: Set Canvas Size**
- File → Page Setup
- Width: 1600px, Height: 900px
- Background: White

### **Step 3: Create Generator (Left Side)**

**Layer Order (Top to Bottom):**

1. **Title Box:**
   - Shape: Rectangle
   - Text: "Generator"
   - Style: Bold, 16pt, centered

2. **Input:**
   - Shape: Rounded Rectangle
   - Text: "z ~ N(0,1)\n100-dim"
   - Color: Light Blue (#E3F2FD)

3. **Dense:**
   - Text: "Dense\n8×8×256"
   - Color: Light Green (#C8E6C9)

4. **BatchNorm:**
   - Text: "BatchNorm\nLeakyReLU"
   - Color: Light Yellow (#FFF9C4)

5. **Reshape:**
   - Text: "Reshape\n(8, 8, 256)"
   - Color: Light Orange (#FFE0B2)

6. **Conv2DTranspose 1:**
   - Text: "Conv2DTranspose\n128, 5×5, s=2\n(16, 16, 128)"
   - Color: Light Red (#FFCDD2)

7. **BatchNorm:**
   - Text: "BatchNorm\nLeakyReLU"
   - Color: Light Yellow (#FFF9C4)

8. **Conv2DTranspose 2:**
   - Text: "Conv2DTranspose\n64, 5×5, s=2\n(32, 32, 64)"
   - Color: Light Red (#FFCDD2)

9. **BatchNorm:**
   - Text: "BatchNorm\nLeakyReLU"
   - Color: Light Yellow (#FFF9C4)

10. **Conv2DTranspose 3:**
    - Text: "Conv2DTranspose\n3, 5×5, s=2, tanh\n(64, 64, 3)"
    - Color: Light Pink (#F8BBD0)

11. **Output:**
    - Text: "64×64×3\nRGB Image"
    - Color: Light Purple (#E1BEE7)

### **Step 4: Create Discriminator (Right Side)**

**Layer Order (Top to Bottom):**

1. **Title:** "Discriminator"

2. **Input:**
   - Text: "64×64×3\nRGB Image"
   - Color: Light Purple (#E1BEE7)

3. **Conv2D 1:**
   - Text: "Conv2D\n64, 5×5, s=2"
   - Color: Light Red (#FFCDD2)

4. **Activation:**
   - Text: "LeakyReLU\nDropout(0.3)"
   - Color: Light Yellow (#FFF9C4)

5. **Conv2D 2:**
   - Text: "Conv2D\n128, 5×5, s=2"
   - Color: Light Red (#FFCDD2)

6. **Activation:**
   - Text: "LeakyReLU\nDropout(0.3)"
   - Color: Light Yellow (#FFF9C4)

7. **Flatten:**
   - Text: "Flatten"
   - Color: Light Blue (#BBDEFB)

8. **Dense:**
   - Text: "Dense(1)\nLogits"
   - Color: Light Green (#C8E6C9)

9. **Output:**
   - Text: "Real/Fake\nClassification"
   - Color: Light Pink (#F8BBD0)

### **Step 5: Add Arrows**

- Use "Arrow" tool from left panel
- Connect each layer to the next (top to bottom)
- Style: Straight, 2px width, black

### **Step 6: Add Training Info**

- Add text box at bottom:
  - "Training: 40 dark-skin images, 400 epochs, Adam optimizer"

### **Step 7: Export**

- File → Export as → PNG
- **IMPORTANT:** Set DPI to 300
- Save as: `gan_architecture.png`
- Place in your paper directory

---

## 🎨 **Color Codes (Copy-Paste)**

- Light Blue: `#E3F2FD`
- Light Green: `#C8E6C9`
- Light Yellow: `#FFF9C4`
- Light Orange: `#FFE0B2`
- Light Red: `#FFCDD2`
- Light Pink: `#F8BBD0`
- Light Purple: `#E1BEE7`

---

## ✅ **Quick Checklist**

- [ ] Generator on left, Discriminator on right
- [ ] All layers labeled correctly
- [ ] Arrows show data flow (top to bottom)
- [ ] Colors are consistent
- [ ] Text is readable
- [ ] Exported at 300 DPI
- [ ] Saved as `gan_architecture.png`

**Done!** 🎉


