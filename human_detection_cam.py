import cv2
from ultralytics import YOLO
import time

# -------- LOAD MODEL --------
model = YOLO("yolov8n.pt")

# -------- CAMERA --------
cap = cv2.VideoCapture(0)

# -------- GLOBAL HUMAN COUNT --------
human_count = 0


# -------- DETECT HUMAN FUNCTION --------
def detect_human():
    global human_count

    ret, frame = cap.read()
    if not ret:
        human_count = 0
        return False

    results = model(frame)

    count = 0

    for r in results:
        for box in r.boxes:
            cls = int(box.cls[0])
            if cls == 0:  # person
                count += 1

    human_count = count

    return count > 0


# -------- GET HUMAN COUNT --------
def get_human_count():
    return human_count


# -------- OPTIONAL: DISPLAY WINDOW (for debugging) --------
def show_camera():
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        results = model(frame)

        count = 0

        for r in results:
            for box in r.boxes:
                cls = int(box.cls[0])

                if cls == 0:  # person
                    count += 1
                    x1, y1, x2, y2 = map(int, box.xyxy[0])

                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(frame, "Human", (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        cv2.putText(frame, f"Humans: {count}", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        cv2.imshow("Camera Feed", frame)

        if cv2.waitKey(1) & 0xFF == 27:  # ESC to exit
            break

        time.sleep(0.1)

    cap.release()
    cv2.destroyAllWindows()