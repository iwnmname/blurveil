import cv2
from PIL import Image
import pytesseract

print(f"OpenCV: {cv2.__version__}")
print(f"Tesseract: {pytesseract.get_tesseract_version()}")

def main():
    print("Hello from blurveil!")
    print("Все зависимости работают!")

if __name__ == "__main__":
    main()