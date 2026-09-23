 

import numpy as np
from PIL import Image
from skimage.feature import hog
from skimage import color

IMG_SIZE = (64, 64)
HOG_PARAMS = dict(
    orientations=9,
    pixels_per_cell=(8, 8),
    cells_per_block=(2, 2),
    block_norm="L2-Hys",
)


def load_and_resize(path, size=IMG_SIZE):
    """เปิดรูปภาพ, แปลงเป็น RGB, และ resize ให้ได้ขนาดคงที่"""
    img = Image.open(path).convert("RGB").resize(size)
    return np.array(img)


def extract_hog_features(img_array):
    """
    สกัด HOG feature จากภาพ (numpy array, RGB)
    คืนค่าเป็น 1D feature vector
    """
    gray = color.rgb2gray(img_array)
    features = hog(gray, **HOG_PARAMS)
    return features


def image_to_features(path):
    """รวมขั้นตอน resize + สกัด feature จาก path ของรูปภาพเดียว"""
    img_array = load_and_resize(path)
    return extract_hog_features(img_array)


def build_feature_matrix(image_paths, verbose=True):
    """
    วนลูปสกัด feature จากรูปภาพทั้งหมด
    คืนค่าเป็น numpy array รูปร่าง (n_samples, n_features)
    """
    feature_list = []
    n = len(image_paths)
    for i, path in enumerate(image_paths):
        feature_list.append(image_to_features(path))
        if verbose and (i + 1) % 1000 == 0:
            print(f"  สกัด feature แล้ว {i + 1}/{n} รูป")
    return np.array(feature_list, dtype=np.float32)


if __name__ == "__main__":
    # ทดสอบสกัด feature จากภาพตัวอย่าง 1 ภาพ
    import sys
    from data_loader import load_dataset

    paths, labels, classes = load_dataset()
    sample_features = image_to_features(paths[0])
    print(f"ตัวอย่างภาพ: {paths[0]}")
    print(f"ขนาด feature vector: {sample_features.shape}")
