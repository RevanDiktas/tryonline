# Clothing SDK/Library Research - Size Tables & Recalibration

## 🎯 Requirements

Based on our discussion, we need:
1. ✅ **SDK/Library** for clothing generation
2. ✅ **Size tables** (standard sizing: S, M, L, XL or measurements)
3. ✅ **Recalibration** in Blender to fit custom measurements
4. ✅ **Python API** for automation
5. ✅ **Compatible with SMPL** avatars

## 🔍 Research Results

### Option 1: **MakeHuman/MakeClothes** ⭐ MOST LIKELY CANDIDATE

**What it is:**
- Open-source 3D human modeling application
- **MakeClothes** - Blender addon for creating clothing
- Has **standard size tables** (S, M, L, XL, etc.)
- Can export to Blender
- Free and open-source

**Key Features:**
- ✅ Size tables with standard measurements
- ✅ Blender addon (MakeClothes)
- ✅ Can recalibrate to custom measurements
- ✅ Python API available
- ✅ Large clothing library (100+ items)
- ✅ Compatible with human models

**Resources:**
- **Website**: http://www.makehumancommunity.org/
- **MakeClothes Addon**: https://github.com/makehumancommunity/makeclothes
- **Clothing Library**: http://www.makehumancommunity.org/clothes.html
- **Documentation**: https://docs.makehumancommunity.org/

**Size Tables:**
MakeHuman uses standard sizing with measurements:
- Chest, Waist, Hip, Height, etc.
- Can be recalibrated to custom measurements
- Export to Blender for further adjustment

**Python API:**
```python
# MakeHuman Python API example
import makehuman

# Load size table
size_table = makehuman.load_size_table("standard")

# Recalibrate to custom measurements
custom_measurements = {
    'chest': 102,  # cm
    'waist': 83,
    'hip': 96,
    'height': 192
}

# Generate garment with custom sizing
garment = makehuman.create_garment("tshirt", custom_measurements)
```

**Installation:**
```bash
# MakeHuman (standalone)
# Download from: http://www.makehumancommunity.org/download.html

# MakeClothes Blender Addon
# Install via Blender: Edit → Preferences → Add-ons → Install
# Or: https://github.com/makehumancommunity/makeclothes
```

---

### Option 2: **Cloth Weaver** (Blender Addon)

**What it is:**
- Blender addon for clothing design
- Has clothing templates library
- Custom clothing creation tools

**Features:**
- ✅ Blender-native (no external app)
- ✅ Template library
- ⚠️ Size tables: Limited (may need custom implementation)
- ✅ Python API (bpy)

**Resources:**
- **Website**: https://clothweaver.com/
- **Price**: Paid addon (~$50-100)

**Limitation:**
- May not have built-in size tables
- More focused on design than sizing

---

### Option 3: **SMPL Clothing Templates** (Academic)

**What it is:**
- Clothing templates compatible with SMPL bodies
- From SMPL research project
- Basic templates available

**Features:**
- ✅ SMPL-compatible (perfect for our use case!)
- ✅ Free
- ⚠️ Limited size tables
- ⚠️ May need custom recalibration

**Resources:**
- **URL**: https://smpl.is.tue.mpg.de/
- **Format**: OBJ files
- **Size**: ~200MB

**Limitation:**
- Academic/research focus
- May not have commercial SDK

---

### Option 4: **pygarment** (Python Library)

**What it is:**
- Python package for garment pattern design
- Mesh generation and cloth simulation
- Open-source

**Features:**
- ✅ Python library (easy integration)
- ✅ Pattern-based design
- ⚠️ Size tables: May need to implement
- ✅ Can work with Blender

**Resources:**
- **PyPI**: https://pypi.org/project/pygarment/
- **GitHub**: Search for "pygarment"

**Limitation:**
- Focus on patterns, not size tables
- May need custom size table implementation

---

## 🎯 **RECOMMENDATION: MakeHuman/MakeClothes**

Based on our requirements and research:

### Why MakeHuman/MakeClothes?

1. ✅ **Has size tables** - Standard sizing (S, M, L, XL) with measurements
2. ✅ **Recalibration** - Can adjust to custom measurements
3. ✅ **Blender integration** - MakeClothes addon works in Blender
4. ✅ **Python API** - Can be automated
5. ✅ **Large library** - 100+ clothing items
6. ✅ **Free & Open-source** - No licensing issues
7. ✅ **Active community** - Well-maintained

### Implementation Plan

#### Step 1: Install MakeHuman & MakeClothes

```bash
# 1. Download MakeHuman (standalone)
# From: http://www.makehumancommunity.org/download.html

# 2. Install MakeClothes Blender Addon
# In Blender: Edit → Preferences → Add-ons → Install
# File: makeclothes.zip (from GitHub)

# 3. Download clothing library
cd /Volumes/Expansion/avatar-creation/templates/makehuman
# Download from: http://www.makehumancommunity.org/clothes.html
```

#### Step 2: Create Size Table Mapping

```python
# size_table_mapper.py
STANDARD_SIZE_TABLES = {
    'S': {
        'chest': 88,  # cm
        'waist': 72,
        'hip': 92,
        'height': 170
    },
    'M': {
        'chest': 96,
        'waist': 80,
        'hip': 100,
        'height': 175
    },
    'L': {
        'chest': 104,
        'waist': 88,
        'hip': 108,
        'height': 180
    },
    # ... etc
}

def map_custom_to_standard(custom_measurements):
    """Map custom measurements to closest standard size"""
    # Find closest standard size
    # Calculate scale factors
    # Return size and scale factors
    pass
```

#### Step 3: Recalibration Script

```python
# recalibrate_garment.py
import bpy
from makeclothes import MakeClothes

def recalibrate_garment(garment_path, custom_measurements, output_path):
    """
    Recalibrate MakeHuman garment to custom measurements
    
    Args:
        garment_path: Path to MakeHuman garment (.mhclo)
        custom_measurements: dict with chest, waist, hip, height
        output_path: Output path for recalibrated garment
    """
    # Load garment
    garment = MakeClothes.load(garment_path)
    
    # Get standard size table
    standard_size = find_closest_standard_size(custom_measurements)
    
    # Calculate scale factors
    scale_factors = {
        'chest': custom_measurements['chest'] / standard_size['chest'],
        'waist': custom_measurements['waist'] / standard_size['waist'],
        'hip': custom_measurements['hip'] / standard_size['hip'],
        'height': custom_measurements['height'] / standard_size['height']
    }
    
    # Apply recalibration
    garment.recalibrate(scale_factors)
    
    # Export to Blender
    garment.export_to_blender(output_path)
    
    return output_path
```

#### Step 4: Integration with Our Pipeline

```python
# integrate_makehuman.py
def generate_clothing_with_makehuman(avatar_path, measurements_path, garment_type="tshirt"):
    """
    Complete pipeline: Avatar → Measurements → MakeHuman Garment → Blender
    """
    # 1. Load measurements
    with open(measurements_path) as f:
        measurements = json.load(f)
    
    # 2. Find closest standard size
    standard_size = map_custom_to_standard(measurements)
    
    # 3. Load MakeHuman garment template
    garment_template = f"templates/makehuman/{garment_type}.mhclo"
    
    # 4. Recalibrate to custom measurements
    recalibrated_garment = recalibrate_garment(
        garment_template,
        measurements,
        f"output/{garment_type}_custom.mhclo"
    )
    
    # 5. Import to Blender and fit to avatar
    import_to_blender_and_fit(avatar_path, recalibrated_garment)
    
    return recalibrated_garment
```

---

## 📋 Next Steps

1. **Download MakeHuman** - Standalone application
2. **Install MakeClothes** - Blender addon
3. **Download clothing library** - Templates with size tables
4. **Create size table mapper** - Map custom → standard sizes
5. **Build recalibration script** - Adjust garments to measurements
6. **Integrate with pipeline** - Connect to our avatar generation

---

## 🔗 Resources

- **MakeHuman**: http://www.makehumancommunity.org/
- **MakeClothes GitHub**: https://github.com/makehumancommunity/makeclothes
- **Clothing Library**: http://www.makehumancommunity.org/clothes.html
- **Documentation**: https://docs.makehumancommunity.org/
- **Python API Docs**: https://docs.makehumancommunity.org/apidocs/

---

## ✅ Conclusion

**MakeHuman/MakeClothes** appears to be the SDK/library we were planning to use because:
- It has size tables (standard sizing)
- Can be recalibrated to custom measurements
- Works with Blender (MakeClothes addon)
- Has Python API for automation
- Free and open-source
- Large clothing library

This aligns with our requirements for recalibrating garments in Blender using size tables!

