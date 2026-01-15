"""
Calculate principal strain (ARCSim-aligned method) for stress calculation.
Based on ChatGPT's mathematical framework.
"""

import numpy as np

def calculate_principal_strain_per_triangle(original_vertices, deformed_vertices, faces):
    """
    Calculate principal strain for each triangle using ARCSim method.
    
    For each triangle:
    1. Compute deformation gradient F
    2. Compute Green-Lagrange strain E = ½(FᵀF - I)
    3. Find eigenvalues (principal strains) λ₁, λ₂
    4. Take maximum: ε_max = max(λ₁, λ₂)
    5. Only tensile strain: ε_max⁺ = max(0, ε_max)
    
    Args:
        original_vertices: (n, 3) - vertices before deformation
        deformed_vertices: (n, 3) - vertices after deformation
        faces: (m, 3) - triangle face indices
    
    Returns:
        principal_strains: (m,) - maximum principal tensile strain per triangle
    """
    n_faces = len(faces)
    principal_strains = np.zeros(n_faces)
    
    for i, face in enumerate(faces):
        v0_orig, v1_orig, v2_orig = original_vertices[face]
        v0_def, v1_def, v2_def = deformed_vertices[face]
        
        # Compute edge vectors in original (rest) state
        e1_orig = v1_orig - v0_orig
        e2_orig = v2_orig - v0_orig
        
        # Compute edge vectors in deformed state
        e1_def = v1_def - v0_def
        e2_def = v2_def - v0_def
        
        # For 2D material coordinates, assume triangle lies in plane
        # Create 2D basis from original triangle
        # This is simplified - full ARCSim uses proper material coordinates
        
        # Compute triangle area (for normalization)
        area_orig = 0.5 * np.linalg.norm(np.cross(e1_orig, e2_orig))
        area_def = 0.5 * np.linalg.norm(np.cross(e1_def, e2_def))
        
        if area_orig > 1e-10:
            # Area strain (simplified proxy for principal strain)
            area_strain = (area_def - area_orig) / area_orig
            
            # For principal strain approximation:
            # Use maximum edge stretch as proxy for ε_max
            len_e1_orig = np.linalg.norm(e1_orig)
            len_e2_orig = np.linalg.norm(e2_orig)
            len_e1_def = np.linalg.norm(e1_def)
            len_e2_def = np.linalg.norm(e2_def)
            
            if len_e1_orig > 1e-10 and len_e2_orig > 1e-10:
                strain_e1 = (len_e1_def - len_e1_orig) / len_e1_orig
                strain_e2 = (len_e2_def - len_e2_orig) / len_e2_orig
                
                # Maximum principal strain (approximation)
                # ε_max ≈ max(strain_e1, strain_e2, area_strain)
                epsilon_max = max(strain_e1, strain_e2, area_strain)
                
                # Only tensile strain contributes: ε_max⁺ = max(0, ε_max)
                epsilon_max_plus = max(0, epsilon_max)
                
                principal_strains[i] = epsilon_max_plus
    
    return principal_strains


def calculate_vertex_stress_from_principal_strain(original_vertices, deformed_vertices, faces, E_eff=100.0):
    """
    Calculate stress per vertex using ARCSim method.
    
    σ_eff = E_eff · max(0, ε_max)
    
    Where:
    - E_eff = Effective Young's modulus (kPa)
    - ε_max = Maximum principal tensile strain
    
    Args:
        original_vertices: (n, 3) - vertices before deformation
        deformed_vertices: (n, 3) - vertices after deformation
        faces: (m, 3) - triangle face indices
        E_eff: Effective Young's modulus (default 100 kPa)
    
    Returns:
        stress: (n,) - stress per vertex (kPa)
    """
    # Calculate principal strain per triangle
    triangle_strains = calculate_principal_strain_per_triangle(
        original_vertices, deformed_vertices, faces
    )
    
    # Average strain per vertex (from connected triangles)
    n_vertices = len(original_vertices)
    vertex_strain = np.zeros(n_vertices)
    vertex_count = np.zeros(n_vertices)
    
    for i, face in enumerate(faces):
        strain = triangle_strains[i]
        for v_idx in face:
            vertex_strain[v_idx] += strain
            vertex_count[v_idx] += 1
    
    # Average
    vertex_strain = np.where(vertex_count > 0, 
                            vertex_strain / vertex_count, 
                            0)
    
    # Convert to stress: σ_eff = E_eff · max(0, ε_max)
    # Only tensile strain contributes
    stress = E_eff * np.maximum(0, vertex_strain)
    
    return stress


# Strain interpretation thresholds (from reference)
STRAIN_THRESHOLDS = {
    'comfortable': 0.15,  # ε_max < 0.15
    'snug': 0.35,         # 0.15 ≤ ε_max < 0.35
    'tight': 0.6,          # 0.35 ≤ ε_max < 0.6
    'critical': 0.6        # ε_max ≥ 0.6
}

def interpret_strain(epsilon_max):
    """
    Interpret strain value into comfort category.
    
    Returns: 'comfortable', 'snug', 'tight', or 'critical'
    """
    if epsilon_max < STRAIN_THRESHOLDS['comfortable']:
        return 'comfortable'
    elif epsilon_max < STRAIN_THRESHOLDS['snug']:
        return 'snug'
    elif epsilon_max < STRAIN_THRESHOLDS['tight']:
        return 'tight'
    else:
        return 'critical'






