# Body Measurement Extraction Workflow

## ✅ Improved Approach: Height-Calibrated Measurements

**Key Principle:** Always ask the user for their **actual height** first, then use that to calibrate all measurements.

### Why Height Calibration?

- Every person is different - mesh height varies
- Using actual height ensures accurate scaling
- All measurements (chest, waist, hips, etc.) become accurate after scaling
- Works for any body type and size

## 📋 Workflow

### Step 1: Generate 3D Mesh
```bash
python demo_yolo.py --input photo.jpg --output_folder output/
```
This creates:
- `person0.obj` - 3D mesh
- `person0_params.npz` - SMPL parameters

### Step 2: Create Relaxed Pose (for garment work)
```bash
python final_relaxed_rig.py --params person0_params.npz --height <USER_HEIGHT> --output GARMENT_RIG.obj
```
**Important:** Use the user's actual height here!

### Step 3: Extract Measurements
```bash
python extract_measurements_improved.py --mesh GARMENT_RIG.obj --height <USER_HEIGHT> --output measurements.json
```

## 🎯 Scripts

### `extract_measurements_improved.py` ⭐ **USE THIS ONE**
- **Method:** Geometric landmark detection
- **How it works:**
  1. Finds anatomical landmarks by analyzing mesh geometry
  2. Searches for narrowest point (waist)
  3. Searches for widest points (chest, hips)
  4. Calculates circumferences using actual mesh cross-sections
- **Pros:**
  - Works with any .obj mesh
  - No SMPL model loading needed
  - Uses convex hull for accurate perimeter calculation
  - Finds landmarks automatically

### `extract_accurate_measurements.py` (older version)
- Uses fixed height ratios (75% for chest, 60% for waist, etc.)
- Less accurate for different body types
- Still works but not as precise

## 📊 What Measurements Are Extracted?

### Circumferences:
- **Chest** - Widest point in upper torso
- **Waist** - Narrowest point between chest and hips
- **Hips** - Widest point in lower torso
- **Neck** - Narrowest point in upper body
- **Thigh** - Midpoint between hip and knee

### Widths:
- **Shoulder width** - Distance between shoulder points
- **Arm span** - Total width from left to right

### Lengths:
- **Inseam** - Hip to floor
- **Torso length** - Shoulder to hip
- **Arm length** - Approximate shoulder to wrist

## 💡 Usage Example

```bash
# 1. User provides height: 192cm
# 2. Generate mesh
python demo_yolo.py --input user_photo.jpg --output_folder user_mesh/

# 3. Create garment rig
python final_relaxed_rig.py \
  --params user_mesh/user_photo_person0_params.npz \
  --height 192 \
  --output user_garment_rig.obj

# 4. Extract measurements
python extract_measurements_improved.py \
  --mesh user_garment_rig.obj \
  --height 192 \
  --output user_measurements.json
```

## 🔧 How It Works

1. **Load mesh** - Reads the .obj file
2. **Scale to height** - Scales mesh to match user's actual height
3. **Find landmarks** - Analyzes geometry to find:
   - Narrowest point (waist)
   - Widest points (chest, hips)
   - Shoulder level
   - Neck level
4. **Calculate circumferences** - Slices mesh at landmark levels and calculates actual perimeter
5. **Extract widths/lengths** - Measures distances between key points

## ⚠️ Important Notes

- **Always ask for height first!** This is critical for accuracy
- Works best with relaxed pose mesh (arms at sides)
- Measurements are in centimeters
- Some measurements (like arm length) are approximate
- For garment work, use `FINAL_RELAXED_RIG.obj` as input

## 🚀 Next Steps

- Train/improve landmark detection for better accuracy
- Add more measurement types (bicep, calf, etc.)
- Validate against real measurements for calibration

---

**Last updated:** Today's session
**Status:** ✅ Working - uses height calibration for accurate measurements

