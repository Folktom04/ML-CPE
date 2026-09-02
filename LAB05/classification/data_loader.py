 

import os
from PIL import Image

# ชื่อคลาส (index ตรงกับ label ที่ใช้เทรนโมเดล)
CLASS_NAMES = ["Cat", "Dog"]


def load_dataset(data_dir="../PetImages"):
    
    image_paths = []
    labels = []

    for class_idx, class_name in enumerate(CLASS_NAMES):
        class_dir = os.path.join(data_dir, class_name)
        if not os.path.isdir(class_dir):
            raise FileNotFoundError(f"ไม่พบโฟลเดอร์: {class_dir}")

        files = sorted(
            os.listdir(class_dir),
            key=lambda x: (len(x), x),  # เรียงตามเลขไฟล์ 0,1,2,... ให้ถูกต้อง
        )
        for fname in files:
            if not fname.lower().endswith((".jpg", ".jpeg", ".png")):
                continue
            image_paths.append(os.path.join(class_dir, fname))
            labels.append(class_idx)

    return image_paths, labels, CLASS_NAMES


def verify_image(path):
     
    try:
        with Image.open(path) as im:
            im.verify()
        return True
    except Exception:
        return False


if __name__ == "__main__":
    paths, labels, classes = load_dataset()
    print(f"พบรูปภาพทั้งหมด {len(paths)} รูป")
    for idx, name in enumerate(classes):
        count = labels.count(idx)
        print(f"  - {name}: {count} รูป")
