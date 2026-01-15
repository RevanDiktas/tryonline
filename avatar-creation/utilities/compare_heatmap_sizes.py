#!/usr/bin/env python3
"""
Quick script to compare heatmap distances across sizes.
Uses existing distance files if available, or generates new ones.
"""

import sys
from pathlib import Path
import numpy as np

PROJECT_ROOT = Path(__file__).parent
HEATMAP_DIR = PROJECT_ROOT / 'output' / 'heatmaps'

def load_distance_stats(filepath):
    """Load distance statistics from text file."""
    stats = {}
    distances = []
    
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    # Parse statistics
    for line in lines:
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip().lower()
            value = value.strip()
            if key in ['min', 'max', 'mean', 'median', 'std']:
                stats[key] = float(value)
    
    # Parse per-vertex distances
    in_distances = False
    for line in lines:
        if 'Per-vertex distances' in line:
            in_distances = True
            continue
        if in_distances and ':' in line:
            try:
                _, dist_str = line.split(':', 1)
                distances.append(float(dist_str.strip()))
            except:
                pass
    
    return stats, np.array(distances)


def compare_sizes():
    """Compare XS, M, and XL heatmap distances."""
    print("=" * 70)
    print("HEATMAP SIZE COMPARISON: XS vs M vs XL")
    print("=" * 70)
    
    sizes = ['xs', 'm', 'xl']
    size_data = {}
    
    # Load data for each size
    for size in sizes:
        dist_file = HEATMAP_DIR / f'playboy_tshirt_{size}_perfect_distances.txt'
        if dist_file.exists():
            stats, distances = load_distance_stats(dist_file)
            size_data[size] = {'stats': stats, 'distances': distances}
            print(f"\n✓ Loaded {size.upper()} data: {len(distances)} vertices")
        else:
            print(f"\n⚠️  {size.upper()} distance file not found: {dist_file}")
            print(f"   Run: python generate_heatmap.py --garment output/playboy_tshirt_all_sizes/playboy_tshirt_{size}_perfect.ply --body output/playboy_tshirt_all_sizes/body_apose_{size}.ply --output output/heatmaps")
            size_data[size] = None
    
    # Compare statistics
    print("\n" + "=" * 70)
    print("DISTANCE STATISTICS COMPARISON (mm)")
    print("=" * 70)
    print(f"{'Metric':<12} {'XS':<15} {'M':<15} {'XL':<15} {'Difference (XL-XS)':<20}")
    print("-" * 70)
    
    if all(size_data.get(s) is not None for s in sizes):
        for metric in ['min', 'max', 'mean', 'median', 'std']:
            xs_val = size_data['xs']['stats'].get(metric, 0)
            m_val = size_data['m']['stats'].get(metric, 0)
            xl_val = size_data['xl']['stats'].get(metric, 0)
            diff = xl_val - xs_val
            
            print(f"{metric.capitalize():<12} {xs_val:>10.2f} mm   {m_val:>10.2f} mm   {xl_val:>10.2f} mm   {diff:>+10.2f} mm")
    
    # Color distribution comparison
    print("\n" + "=" * 70)
    print("COLOR DISTRIBUTION (Fit Categories)")
    print("=" * 70)
    
    if all(size_data.get(s) is not None for s in sizes):
        categories = {
            'Very Tight (0-2mm)': (0, 2),
            'Tight (2-5mm)': (2, 5),
            'Snug (5-10mm)': (5, 10),
            'Comfortable (10-15mm)': (10, 15),
            'Loose (15-25mm)': (15, 25),
            'Very Loose (25+mm)': (25, 1000)
        }
        
        print(f"{'Category':<25} {'XS':<12} {'M':<12} {'XL':<12}")
        print("-" * 70)
        
        for cat_name, (min_dist, max_dist) in categories.items():
            xs_count = np.sum((size_data['xs']['distances'] >= min_dist) & 
                             (size_data['xs']['distances'] < max_dist))
            m_count = np.sum((size_data['m']['distances'] >= min_dist) & 
                            (size_data['m']['distances'] < max_dist))
            xl_count = np.sum((size_data['xl']['distances'] >= min_dist) & 
                             (size_data['xl']['distances'] < max_dist))
            
            xs_pct = xs_count / len(size_data['xs']['distances']) * 100
            m_pct = m_count / len(size_data['m']['distances']) * 100
            xl_pct = xl_count / len(size_data['xl']['distances']) * 100
            
            print(f"{cat_name:<25} {xs_pct:>6.1f}% ({xs_count:>5})  {m_pct:>6.1f}% ({m_count:>5})  {xl_pct:>6.1f}% ({xl_count:>5})")
    
    # Key insights
    print("\n" + "=" * 70)
    print("KEY INSIGHTS")
    print("=" * 70)
    
    if all(size_data.get(s) is not None for s in sizes):
        xs_mean = size_data['xs']['stats']['mean']
        m_mean = size_data['m']['stats']['mean']
        xl_mean = size_data['xl']['stats']['mean']
        
        print(f"\n1. Average Fit Gap:")
        print(f"   XS: {xs_mean:.2f}mm (tighter)")
        print(f"   M:  {m_mean:.2f}mm (baseline)")
        print(f"   XL: {xl_mean:.2f}mm (looser)")
        print(f"   Difference: XL is {xl_mean - xs_mean:.2f}mm looser than XS")
        
        xs_min = size_data['xs']['stats']['min']
        xl_min = size_data['xl']['stats']['min']
        print(f"\n2. Tightest Points:")
        print(f"   XS minimum: {xs_min:.2f}mm")
        print(f"   XL minimum: {xl_min:.2f}mm")
        if xs_min < xl_min:
            print(f"   ✓ XS is tighter (smaller minimum distance)")
        else:
            print(f"   ⚠️  Unexpected: XS should be tighter")
        
        xs_max = size_data['xs']['stats']['max']
        xl_max = size_data['xl']['stats']['max']
        print(f"\n3. Loosest Points:")
        print(f"   XS maximum: {xs_max:.2f}mm")
        print(f"   XL maximum: {xl_max:.2f}mm")
        if xl_max > xs_max:
            print(f"   ✓ XL is looser (larger maximum distance)")
        else:
            print(f"   ⚠️  Unexpected: XL should be looser")
        
        # Count tight vertices
        xs_tight = np.sum(size_data['xs']['distances'] < 10)
        m_tight = np.sum(size_data['m']['distances'] < 10)
        xl_tight = np.sum(size_data['xl']['distances'] < 10)
        
        print(f"\n4. Tight Areas (<10mm):")
        print(f"   XS: {xs_tight} vertices ({xs_tight/len(size_data['xs']['distances'])*100:.1f}%)")
        print(f"   M:  {m_tight} vertices ({m_tight/len(size_data['m']['distances'])*100:.1f}%)")
        print(f"   XL: {xl_tight} vertices ({xl_tight/len(size_data['xl']['distances'])*100:.1f}%)")
        
        if xs_tight > xl_tight:
            print(f"   ✓ XS has more tight areas (expected)")
        else:
            print(f"   ⚠️  Unexpected: XS should have more tight areas")
    
    print("\n" + "=" * 70)
    print("COMPARISON COMPLETE")
    print("=" * 70)


if __name__ == '__main__':
    compare_sizes()






