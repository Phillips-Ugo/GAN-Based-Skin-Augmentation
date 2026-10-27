"""
DCGAN Architecture Figure Generator
Creates a professional architecture diagram for the paper
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

# Set up figure with two subplots (Generator and Discriminator)
fig = plt.figure(figsize=(16, 10))
fig.suptitle('DCGAN Architecture for Synthetic Dark-Skin Image Generation', 
             fontsize=18, fontweight='bold', y=0.97)

# Create two axes side by side
ax1 = plt.subplot(1, 2, 1)  # Generator (left)
ax2 = plt.subplot(1, 2, 2)  # Discriminator (right)

# ==================== GENERATOR (LEFT) ====================
ax1.set_xlim(0, 10)
ax1.set_ylim(-1.5, 12)
ax1.axis('off')
ax1.set_title('Generator', fontsize=16, fontweight='bold', pad=20)

# Generator layers with (label, x, y, color)
gen_layers = [
    ('z ~ N(0,1)\n100-dim', 5, 11, '#E3F2FD'),  # Light blue
    ('Dense\n8×8×256', 5, 9.5, '#C8E6C9'),  # Light green
    ('BatchNorm\nLeakyReLU', 5, 8, '#FFF9C4'),  # Light yellow
    ('Reshape\n(8, 8, 256)', 5, 6.5, '#FFE0B2'),  # Light orange
    ('Conv2DTranspose\n128, 5×5, s=2\n(16, 16, 128)', 5, 5, '#FFCDD2'),  # Light red
    ('BatchNorm\nLeakyReLU', 5, 3.5, '#FFF9C4'),  # Light yellow
    ('Conv2DTranspose\n64, 5×5, s=2\n(32, 32, 64)', 5, 2, '#FFCDD2'),  # Light red
    ('BatchNorm\nLeakyReLU', 5, 0.5, '#FFF9C4'),  # Light yellow
    ('Conv2DTranspose\n3, 5×5, s=2, tanh\n(64, 64, 3)', 5, -1, '#F8BBD0'),  # Light pink
]

for i, (label, x, y, color) in enumerate(gen_layers):
    # Create rounded rectangle box
    box = FancyBboxPatch((x-2, y-0.5), 4, 1, 
                         boxstyle="round,pad=0.15", 
                         facecolor=color, 
                         edgecolor='#333333', 
                         linewidth=2)
    ax1.add_patch(box)
    
    # Add text
    ax1.text(x, y, label, ha='center', va='center', 
            fontsize=10, fontweight='bold', color='#000000')
    
    # Add arrow pointing down (except for last layer)
    if i < len(gen_layers) - 1:
        arrow = FancyArrowPatch((x, y-0.5), (x, y-1.1), 
                               arrowstyle='->', mutation_scale=25, 
                               color='#333333', linewidth=2.5, zorder=1)
        ax1.add_patch(arrow)

# ==================== DISCRIMINATOR (RIGHT) ====================
ax2.set_xlim(0, 10)
ax2.set_ylim(-1.5, 12)
ax2.axis('off')
ax2.set_title('Discriminator', fontsize=16, fontweight='bold', pad=20)

# Discriminator layers
disc_layers = [
    ('64×64×3\nRGB Image', 5, 11, '#E1BEE7'),  # Light purple
    ('Conv2D\n64, 5×5, s=2', 5, 9.5, '#FFCDD2'),  # Light red
    ('LeakyReLU\nDropout(0.3)', 5, 8, '#FFF9C4'),  # Light yellow
    ('Conv2D\n128, 5×5, s=2', 5, 6.5, '#FFCDD2'),  # Light red
    ('LeakyReLU\nDropout(0.3)', 5, 5, '#FFF9C4'),  # Light yellow
    ('Flatten', 5, 3.5, '#BBDEFB'),  # Light blue
    ('Dense(1)\nLogits', 5, 2, '#C8E6C9'),  # Light green
    ('Real/Fake\nClassification', 5, 0.5, '#F8BBD0'),  # Light pink
]

for i, (label, x, y, color) in enumerate(disc_layers):
    # Create rounded rectangle box
    box = FancyBboxPatch((x-2, y-0.5), 4, 1, 
                         boxstyle="round,pad=0.15", 
                         facecolor=color, 
                         edgecolor='#333333', 
                         linewidth=2)
    ax2.add_patch(box)
    
    # Add text
    ax2.text(x, y, label, ha='center', va='center', 
            fontsize=10, fontweight='bold', color='#000000')
    
    # Add arrow pointing down (except for last layer)
    if i < len(disc_layers) - 1:
        arrow = FancyArrowPatch((x, y-0.5), (x, y-1.1), 
                               arrowstyle='->', mutation_scale=25, 
                               color='#333333', linewidth=2.5, zorder=1)
        ax2.add_patch(arrow)

# ==================== ADD TRAINING INFO ====================
info_text = ('Training Configuration:\n'
             '• 40 dark-skin training images\n'
             '• 400 epochs, Batch size: 32\n'
             '• Adam optimizer (lr=1e-4)\n'
             '• Binary cross-entropy loss\n'
             '• Output: 3,500 synthetic images (500 per class)')

fig.text(0.5, 0.02, info_text, ha='center', fontsize=11, 
         bbox=dict(boxstyle='round,pad=10', facecolor='#FFFDE7', 
                  edgecolor='#333333', linewidth=2, alpha=0.9),
         family='monospace')

# Adjust layout
plt.tight_layout(rect=[0, 0.05, 1, 0.95])

# Save in high resolution
plt.savefig('gan_architecture.png', dpi=300, bbox_inches='tight', 
           facecolor='white', edgecolor='none', pad_inches=0.2)
plt.savefig('gan_architecture.pdf', bbox_inches='tight', 
           facecolor='white', edgecolor='none', pad_inches=0.2)

print("SUCCESS: Figure saved successfully!")
print("   - gan_architecture.png (300 DPI)")
print("   - gan_architecture.pdf (vector format)")
print("\nPlace gan_architecture.png in your paper directory")

# Optionally display
# plt.show()

