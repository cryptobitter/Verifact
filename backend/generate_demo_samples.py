import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

def create_radius_fracture(width=600, height=800):
    img = np.full((height, width), 25, dtype=np.uint8)
    noise = np.random.normal(0, 3, (height, width)).astype(np.int16)
    
    # Soft tissue contour
    cv2.ellipse(img, (width // 2, height // 2 + 50), (190, 380), 0, 0, 360, 50, -1)
    
    # Ulna (medial bone)
    ulna_pts = np.array([
        [180, 50], [210, 50],
        [205, 500], [215, 750], [175, 750],
        [170, 500]
    ], np.int32)
    cv2.fillPoly(img, [ulna_pts], 160)
    cv2.polylines(img, [ulna_pts], True, 225, 4)
    
    # Radius (lateral bone)
    radius_pts = np.array([
        [270, 50], [330, 50],
        [325, 480], [370, 680], [400, 750], [270, 750],
        [285, 480]
    ], np.int32)
    cv2.fillPoly(img, [radius_pts], 175)
    cv2.polylines(img, [radius_pts], True, 235, 5)
    
    # Trabecular texture
    trab = (np.random.normal(0, 15, (height, width))).astype(np.int16)
    img = np.clip(img.astype(np.int16) + trab, 0, 255).astype(np.uint8)
    
    # Distal Radius fracture line (transverse / slightly oblique cortical disruption at y=690)
    fx_pts = [(265, 688), (295, 692), (325, 689), (360, 693), (385, 686)]
    for i in range(len(fx_pts)-1):
        cv2.line(img, fx_pts[i], fx_pts[i+1], 20, 4)
    # Cortical step off displacement
    cv2.circle(img, (380, 687), 8, 245, -1)
    cv2.line(img, (378, 680), (384, 698), 15, 3)

    # Blur slightly for radiograph appearance
    img = cv2.GaussianBlur(img, (5, 5), 1.2)
    # Add radiopaque marker
    cv2.putText(img, "R AP FOREARM", (40, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, 240, 2)
    cv2.putText(img, "ER TRAUMA", (40, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.5, 180, 1)
    return img

def create_normal_femur(width=600, height=800):
    img = np.full((height, width), 22, dtype=np.uint8)
    # Soft tissue contour
    cv2.ellipse(img, (width // 2, height // 2), (230, 440), 0, 0, 360, 55, -1)
    
    # Femur Shaft & Greater Trochanter
    femur_pts = np.array([
        [230, 50], [370, 50],
        [350, 400], [340, 780],
        [260, 780], [250, 400]
    ], np.int32)
    cv2.fillPoly(img, [femur_pts], 180)
    cv2.polylines(img, [femur_pts], True, 245, 7) # Thick intact cortical bone
    
    # Trabecular texture
    trab = (np.random.normal(0, 12, (height, width))).astype(np.int16)
    img = np.clip(img.astype(np.int16) + trab, 0, 255).astype(np.uint8)
    img = cv2.GaussianBlur(img, (5, 5), 1.0)
    
    cv2.putText(img, "L FEMUR AP", (40, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, 240, 2)
    cv2.putText(img, "CONTROL INTACT", (40, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.5, 180, 1)
    return img

def create_clavicle_displaced(width=800, height=600):
    img = np.full((height, width), 20, dtype=np.uint8)
    # Apical chest / neck soft tissue
    cv2.ellipse(img, (width // 2, height // 2 + 80), (380, 260), 0, 0, 360, 45, -1)
    
    # Medial clavicle fragment
    medial_pts = np.array([
        [120, 280], [390, 270], [385, 305], [120, 315]
    ], np.int32)
    cv2.fillPoly(img, [medial_pts], 190)
    cv2.polylines(img, [medial_pts], True, 240, 5)
    
    # Lateral clavicle fragment (displaced inferiorly/laterally)
    lateral_pts = np.array([
        [410, 315], [690, 305], [695, 340], [415, 350]
    ], np.int32)
    cv2.fillPoly(img, [lateral_pts], 190)
    cv2.polylines(img, [lateral_pts], True, 240, 5)
    
    # Fracture gap / displacement zone
    cv2.line(img, (385, 270), (415, 350), 10, 4)
    
    # Rib contours in background
    for y in [380, 460, 540]:
        cv2.ellipse(img, (400, y), (360, 70), 5, 180, 360, 90, 12)
        
    trab = (np.random.normal(0, 10, (height, width))).astype(np.int16)
    img = np.clip(img.astype(np.int16) + trab, 0, 255).astype(np.uint8)
    img = cv2.GaussianBlur(img, (5, 5), 1.0)
    
    cv2.putText(img, "R CLAVICLE AP", (40, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, 240, 2)
    cv2.putText(img, "MID-SHAFT TRAUMA", (40, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.5, 180, 1)
    return img

def create_scaphoid_hairline(width=600, height=700):
    img = np.full((height, width), 24, dtype=np.uint8)
    cv2.ellipse(img, (width // 2, height // 2), (200, 300), 0, 0, 360, 48, -1)
    
    # Carpal cluster & Scaphoid bone
    cv2.ellipse(img, (310, 360), (45, 65), -25, 0, 360, 175, -1)
    cv2.ellipse(img, (310, 360), (45, 65), -25, 0, 360, 235, 4)
    
    # Adjacent Radius distal articular surface
    cv2.ellipse(img, (300, 510), (110, 80), 0, 180, 360, 170, -1)
    cv2.ellipse(img, (300, 510), (110, 80), 0, 180, 360, 230, 4)
    
    # Subtle hairline fracture line through scaphoid waist
    cv2.line(img, (290, 355), (328, 368), 25, 2)
    
    trab = (np.random.normal(0, 12, (height, width))).astype(np.int16)
    img = np.clip(img.astype(np.int16) + trab, 0, 255).astype(np.uint8)
    img = cv2.GaussianBlur(img, (3, 3), 0.8)
    
    cv2.putText(img, "L WRIST SCAPHOID VIEW", (40, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.65, 240, 2)
    cv2.putText(img, "HAIRLINE SUSPECTED", (40, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.5, 180, 1)
    return img

def main():
    target_dir = os.path.join(os.path.dirname(__file__), "app", "static", "samples")
    os.makedirs(target_dir, exist_ok=True)
    
    samples = {
        "distal_radius_fracture.png": create_radius_fracture(),
        "normal_femur_control.png": create_normal_femur(),
        "clavicle_displaced_fracture.png": create_clavicle_displaced(),
        "scaphoid_hairline_fracture.png": create_scaphoid_hairline()
    }
    
    for filename, img in samples.items():
        filepath = os.path.join(target_dir, filename)
        cv2.imwrite(filepath, img)
        print(f"Generated {filepath} ({img.shape})")

if __name__ == "__main__":
    main()
