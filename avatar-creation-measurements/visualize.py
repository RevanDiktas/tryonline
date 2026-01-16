# ============================================================
# COMPATIBILITY FIXES FOR PYTHON 3.11+ AND NUMPY 2.0+
# Must be applied BEFORE any imports that use chumpy/smplx
# ============================================================
import inspect
if not hasattr(inspect, 'getargspec'):
    inspect.getargspec = inspect.getfullargspec

import numpy as np
if not hasattr(np, 'bool'):
    np.bool = np.bool_
if not hasattr(np, 'int'):
    np.int = np.int_
if not hasattr(np, 'float'):
    np.float = np.float64
if not hasattr(np, 'complex'):
    np.complex = np.complex128
if not hasattr(np, 'object'):
    np.object = np.object_
if not hasattr(np, 'str'):
    np.str = np.str_
if not hasattr(np, 'unicode'):
    np.unicode = np.str_
# ============================================================

"""
Visualizer Stub for SMPL-Anthropometry Measurements.

This is a minimal stub that provides the Visualizer class interface
without requiring Open3D or other visualization dependencies.

For full visualization, use the original visualize.py from:
https://github.com/DavidBoja/SMPL-Anthropometry
"""

from typing import List, Dict, Optional
import warnings


class Visualizer:
    """
    Stub Visualizer class for SMPL-Anthropometry.
    
    This stub allows the measurement code to work without visualization
    dependencies like Open3D. All visualization methods are no-ops.
    """
    
    def __init__(
        self,
        verts: np.ndarray = None,
        faces: np.ndarray = None,
        joints: np.ndarray = None,
        landmarks: Dict = None,
        measurements: Dict = None,
        measurement_types: Dict = None,
        length_definitions: Dict = None,
        circumf_definitions: Dict = None,
        joint2ind: Dict = None,
        circumf_2_bodypart: Dict = None,
        face_segmentation: Dict = None,
        visualize_body: bool = True,
        visualize_landmarks: bool = True,
        visualize_joints: bool = True,
        visualize_measurements: bool = True,
        title: str = "Visualization"
    ):
        """
        Initialize the stub visualizer.
        
        All parameters are stored but visualization is not performed.
        """
        self.verts = verts
        self.faces = faces
        self.joints = joints
        self.landmarks = landmarks or {}
        self.measurements = measurements or {}
        self.measurement_types = measurement_types or {}
        self.length_definitions = length_definitions or {}
        self.circumf_definitions = circumf_definitions or {}
        self.joint2ind = joint2ind or {}
        self.circumf_2_bodypart = circumf_2_bodypart or {}
        self.face_segmentation = face_segmentation or {}
        self.visualize_body = visualize_body
        self.visualize_landmarks = visualize_landmarks
        self.visualize_joints = visualize_joints
        self.visualize_measurements = visualize_measurements
        self.title = title
        
    def visualize(
        self,
        measurement_names: List[str] = None,
        landmark_names: List[str] = None,
        title: str = None
    ):
        """
        Stub visualization method.
        
        Prints a warning that visualization is disabled and returns.
        """
        warnings.warn(
            "Visualization is disabled in this stub version. "
            "Install Open3D and use the full visualize.py for 3D visualization.",
            UserWarning
        )
        
        if measurement_names:
            print(f"[Visualizer Stub] Would visualize {len(measurement_names)} measurements:")
            for name in measurement_names[:5]:
                value = self.measurements.get(name, "N/A")
                print(f"  - {name}: {value}")
            if len(measurement_names) > 5:
                print(f"  ... and {len(measurement_names) - 5} more")
                
    def add_mesh(self, mesh):
        """Stub: Add mesh to visualization."""
        pass
        
    def add_points(self, points, colors=None):
        """Stub: Add points to visualization."""
        pass
        
    def add_lines(self, lines, colors=None):
        """Stub: Add lines to visualization."""
        pass
        
    def show(self):
        """Stub: Show visualization window."""
        warnings.warn(
            "Visualization is disabled. Use the full visualize.py for 3D visualization.",
            UserWarning
        )
