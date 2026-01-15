"""
YOLOv8-based human detector to replace detectron2
Works on macOS without compilation issues
"""
import torch
import numpy as np


class YOLOPredictor:
    """
    Replacement for DefaultPredictor_Lazy using YOLOv8
    Detects people and returns bounding boxes in the same format as detectron2
    """
    
    def __init__(self, confidence=0.5):
        """
        Initialize YOLO model
        Args:
            confidence: Minimum confidence threshold for detections
        """
        from ultralytics import YOLO
        # Load YOLOv8 model (will auto-download on first run)
        print("Loading YOLOv8 model...")
        self.model = YOLO('yolov8n.pt')  # 'n' for nano (fastest)
        self.confidence = confidence
        print("✓ YOLOv8 model loaded")
        
    def __call__(self, original_image):
        """
        Args:
            original_image (np.ndarray): an image of shape (H, W, C) (in BGR order).
        
        Returns:
            predictions (dict): Dictionary with 'instances' containing:
                - pred_boxes: Bounding boxes
                - scores: Confidence scores  
                - pred_classes: Class IDs (0 for person)
        """
        # Run YOLOv8 inference
        results = self.model(original_image, verbose=False)[0]
        
        # Filter for person class (class 0 in COCO dataset)
        boxes = []
        scores = []
        classes = []
        
        for box in results.boxes:
            if int(box.cls[0]) == 0:  # Person class
                boxes.append(box.xyxy[0].cpu().numpy())
                scores.append(float(box.conf[0]))
                classes.append(0)
        
        # Convert to torch tensors to match detectron2 format
        if len(boxes) > 0:
            boxes_tensor = torch.tensor(np.array(boxes))
            scores_tensor = torch.tensor(scores)
            classes_tensor = torch.tensor(classes)
        else:
            boxes_tensor = torch.empty((0, 4))
            scores_tensor = torch.empty((0,))
            classes_tensor = torch.empty((0,))
        
        # Create instances object that mimics detectron2's Instances
        class Instances:
            def __init__(self, boxes, scores, classes):
                self.pred_boxes = type('Boxes', (), {'tensor': boxes})()
                self.scores = scores
                self.pred_classes = classes
        
        instances = Instances(boxes_tensor, scores_tensor, classes_tensor)
        
        return {'instances': instances}


