from picamzero import Camera
import cv2
import os
from datetime import datetime, timedelta
import time
import math

# 🔹 Funktion til at hente tidspunktet for et billede (uden EXIF)
def get_time(img_path):
    """
    Returnerer tidspunktet for et billede baseret på filens ændringstid.
    """
    try:
        mod_time = os.path.getmtime(img_path)  # Få filens ændringstid
        return datetime.fromtimestamp(mod_time)  # Konverter til datetime-format
    except Exception as err:
        print(f"❌ Error obtaining modification time for {img_path}: {err}")
        return datetime.now()

# 🔹 Funktion til at beregne tidsforskellen mellem to billeder (i sekunder)
def get_time_difference(img1, img2):
    t1 = get_time(img1)
    t2 = get_time(img2)
    return (t2 - t1).total_seconds()

# 🔹 Funktion til at konvertere billeder til OpenCV-format
def convert_to_cv(img1, img2):
    return cv2.imread(img1), cv2.imread(img2)

# 🔹 Beregner keypoints og descriptors med ORB
def calculate_features(img1, img2):
    orb = cv2.ORB_create()
    kp1, des1 = orb.detectAndCompute(img1, None)
    kp2, des2 = orb.detectAndCompute(img2, None)
    return kp1, kp2, des1, des2

# 🔹 Matcher descriptors med BFMatcher
def calculate_matches(des1, des2):
    if des1 is None or des2 is None:
        return []
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    return bf.match(des1, des2)

# 🔹 Finder koordinater for matchende keypoints
def find_matching_coordinates(kp1, kp2, matches):
    coords1 = [kp1[m.queryIdx].pt for m in matches]
    coords2 = [kp2[m.trainIdx].pt for m in matches]
    return coords1, coords2

# 🔹 Beregner gennemsnitlig afstand mellem matchende koordinater
def calculate_mean_distance(coords1, coords2):
    if not coords1 or not coords2:
        return 0
    distances = [math.sqrt((c1[0] - c2[0])**2 + (c1[1] - c2[1])**2) for c1, c2 in zip(coords1, coords2)]
    return sum(distances) / len(distances) if distances else 0

# 🔹 Beregner hastigheden i km/s
def calculate_speed_in_kmps(mean_distance, GSD, time_diff):
    distance_km = mean_distance * GSD  # Pixels til kilometer
    return distance_km / time_diff if time_diff > 0 else 0

# 🔹 Hovedprogrammet
if __name__ == "__main__":
    cam = Camera()
    start_time = datetime.now()
    end_time = start_time + timedelta(minutes=10)

    previous_image = None
    all_speeds = []

    print("🚀 Starting ISS speed measurement...")

    while datetime.now() < end_time:
        image_name = f"photo_{datetime.now().strftime('%H%M%S')}.jpg"
        cam.take_photo(image_name)
        time.sleep(30)  # Vent 30 sekunder mellem billeder

        if previous_image:
            try:
                time_diff = get_time_difference(previous_image, image_name)
                if time_diff <= 0:
                    raise ValueError("Time difference is zero or negative.")
            except Exception as e:
                print(f"❌ Error calculating time difference: {e}")
                previous_image = image_name
                continue

            img1_cv, img2_cv = convert_to_cv(previous_image, image_name)
            if img1_cv is None or img2_cv is None:
                print("❌ Error loading images. Skipping this comparison.")
                previous_image = image_name
                continue

            kp1, kp2, des1, des2 = calculate_features(img1_cv, img2_cv)
            matches = calculate_matches(des1, des2)
            if not matches:
                print("⚠️ No matches found. Skipping.")
                previous_image = image_name
                continue

            coords1, coords2 = find_matching_coordinates(kp1, kp2, matches)
            mean_distance = calculate_mean_distance(coords1, coords2)

            GSD = 12468  # Ground Sampling Distance (km/pixel)
            speed = calculate_speed_in_kmps(mean_distance, GSD, time_diff)
            all_speeds.append(speed)

            print(f"✅ Calculated speed: {speed:.4f} km/s")

        previous_image = image_name  # Opdater til næste iteration

    # Beregn gennemsnitshastigheden
    final_speed = sum(all_speeds) / len(all_speeds) if all_speeds else 0

    # Gem resultatet i en fil
    with open("result.txt", "w") as file:
        file.write(f"{final_speed:.5g}")

    print("🎯 Measurement completed! Final speed saved to result.txt")
