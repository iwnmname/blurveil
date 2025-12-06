import cv2
import numpy as np
import pytesseract
import re
from PyQt6.QtGui import QImage, QPixmap

TESS_CONFIG = r'--oem 3 --psm 11'

PATTERNS = {
    "Email": r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
    "IP": r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
    "Secret": r'(?i)secret|pass|key|token',
}

def qpixmap_to_cv_image(pixmap: QPixmap):
    qimage = pixmap.toImage().convertToFormat(QImage.Format.Format_RGBA8888)
    
    width = qimage.width()
    height = qimage.height()
    
    ptr = qimage.bits()
    ptr.setsize(height * width * 4)
    
    arr = np.frombuffer(ptr, np.uint8).reshape((height, width, 4))
    
    return cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)

def cv_image_to_qpixmap(cv_img):
    height, width, channel = cv_img.shape
    bytes_per_line = 3 * width
    cv_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
    qimage = QImage(cv_img.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(qimage)

def blur_sensitive_data(pixmap: QPixmap) -> QPixmap:
    image = qpixmap_to_cv_image(pixmap)
    
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT, config=TESS_CONFIG)
    
    n_boxes = len(data['text'])
    
    blur_regions = []

    for i in range(n_boxes):
        text = data['text'][i].strip()
        if not text:
            continue
            
        for label, pattern in PATTERNS.items():
            if re.search(pattern, text):
                print(f"Найдено [{label}]: {text}")
                (x, y, w, h) = (data['left'][i], data['top'][i], data['width'][i], data['height'][i])
                
                pad = 5
                blur_regions.append((max(0, x-pad), max(0, y-pad), w+pad*2, h+pad*2))
                break

    for (x, y, w, h) in blur_regions:
        roi = image[y:y+h, x:x+w]
        
        if roi.size > 0:
            blurred_roi = cv2.GaussianBlur(roi, (51, 51), 30)
            image[y:y+h, x:x+w] = blurred_roi

    return cv_image_to_qpixmap(image)