# 4D-Humans Setup Guide

## ✅ Completed Steps

1. ✓ Created conda environment: `4D-humans` (Python 3.10)
2. ✓ Installed PyTorch and dependencies
3. ✓ Installed 4D-Humans package
4. ✓ Downloaded HMR2 checkpoint
5. ✓ Fixed NumPy compatibility issues

## 📋 Next Steps

### 1. Download SMPL Body Model (REQUIRED)

The SMPL model requires manual download:

1. **Visit**: https://smpl.is.tue.mpg.de/
2. **Register** for a free account
3. **Download**: "SMPL for Python" (version 1.0.0)
4. **Extract** and find: `basicModel_neutral_lbs_10_207_0_v1.0.0.pkl`
5. **Place** the file in: `/Volumes/Expansion/avatar-creation/4D-Humans-clean/data/`

### 2. Run Test Demo

Once you have the SMPL model:

```bash
conda activate 4D-humans
cd /Volumes/Expansion/avatar-creation/4D-Humans-clean
bash test_setup.sh
```

## 🚀 Usage Examples

### Basic Image Demo

```bash
python demo.py \
    --img_folder example_data/images \
    --out_folder demo_out \
    --batch_size=1 \
    --side_view \
    --save_mesh
```

### Custom Images

```bash
python demo.py \
    --img_folder /path/to/your/images \
    --out_folder output \
    --batch_size=1 \
    --full_frame
```

### Video Tracking (requires PHALP)

First install PHALP:
```bash
pip install git+https://github.com/brjathu/PHALP.git
```

Then run:
```bash
python track.py video.source="example_data/videos/gymnasts.mp4"
```

## 📁 Project Structure

```
/Volumes/Expansion/avatar-creation/4D-Humans-clean/
├── data/
│   ├── checkpoints/
│   │   └── hmr2.ckpt           # ✓ Downloaded
│   └── basicModel_neutral_lbs_10_207_0_v1.0.0.pkl  # ⚠️ Need to download
├── example_data/
│   ├── images/                 # Test images
│   └── videos/                 # Test videos
├── demo.py                     # Main demo script
├── track.py                    # Video tracking script
└── gradio_app.py              # Interactive web interface
```

## 🔧 Troubleshooting

### Issue: NumPy compatibility error
```bash
pip install "numpy<2.0"
```

### Issue: OpenGL/EGL errors on macOS
This is normal - the code will fall back to CPU rendering.

### Issue: Out of memory
Reduce batch size:
```bash
python demo.py --batch_size=1 ...
```

## 📚 Additional Resources

- GitHub: https://github.com/shubham-goel/4D-Humans
- Paper: https://shubham-goel.github.io/4dhumans/
- SMPL: https://smpl.is.tue.mpg.de/

## 🎯 Current Status

- **Environment**: Ready ✓
- **Dependencies**: Installed ✓
- **HMR2 Model**: Downloaded ✓
- **SMPL Model**: **⚠️ PENDING - Manual download required**

Once SMPL model is downloaded, run `bash test_setup.sh` to verify everything works!

