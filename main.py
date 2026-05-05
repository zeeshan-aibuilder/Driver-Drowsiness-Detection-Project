import cv2
import numpy as np
import os
import time
import webbrowser
import pyautogui
from pygame import mixer
from collections import deque

# 🚨 THE REAL PRO FIX: Compatible with Python 3.13 (MediaPipe 0.10.30)
import mediapipe as mp

mp_face_mesh = mp.solutions.face_mesh
FACEMESH_TESSELATION = mp.solutions.face_mesh_connections.FACEMESH_TESSELATION

# --- CONFIGURATION ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSET_PATH = os.path.join(CURRENT_DIR, "assets", "sound.mp3")

CAMERA_ID = 0
WINDOW_NAME = "ZI Group - Bio-Metric Sentinel"

# --- PROJECT DETAILS ---
PROJECT_NAME = "DRIVER SAFETY SYSTEM"
TEAM_NAME = "DEVELOPED BY: ZI GROUP"
MEMBERS = ["M Zeeshan", "Ibrahim Asif"]
IBRAHIM_NUMBER = "923224991814"

# --- TIMING CONSTANTS ---
EYE_AR_THRESH = 0.25
TIME_TO_WAIT_BEFORE_ALARM = 5
WHATSAPP_DELAY = 10

# --- COLORS (BGR) ---
NEON_GREEN = (100, 255, 50)
NEON_RED = (50, 50, 255)
NEON_CYAN = (255, 200, 0)
NEON_PURPLE = (255, 0, 200)
NEON_WARN = (0, 165, 255)
HUD_BG_COLOR = (20, 15, 20)
GRID_COLOR = (50, 35, 50)

# --- MEDIAPIPE INDICES ---
LEFT_EYE_IDXS = [362, 385, 387, 263, 373, 380]
RIGHT_EYE_IDXS = [33, 160, 158, 133, 153, 144]
GRAPH_HISTORY_SIZE = 100

# --- CORE FUNCTIONS ---


def trigger_whatsapp_alert() -> None:
    """Triggers an emergency WhatsApp message to the specified contact using Desktop App."""
    print("\n[!!!] OPENING WHATSAPP DESKTOP APP [!!!]")
    message = (
        "🚨 *EMERGENCY ALERT* 🚨%0A"
        "Your friend *M Zeeshan* is unresponsive while driving!%0A"
        "Please call him IMMEDIATELY.%0A%0A"
        "📍 *Live Location Link:*%0A"
        "https://www.google.com/maps/search/?api=1&query=Lahore,Pakistan"
    )
    whatsapp_url = f"whatsapp://send?phone={IBRAHIM_NUMBER}&text={message}"
    webbrowser.open(whatsapp_url)
    time.sleep(5)
    pyautogui.press("enter")


class AudioManager:
    """Handles asynchronous audio playback for the alarm system."""

    def __init__(self, path: str):
        self.path = path
        self.loaded = False
        try:
            mixer.init()
            if os.path.exists(path):
                mixer.music.load(path)
                self.loaded = True
            else:
                print(f"[ERROR] Audio file missing: {path}")
        except Exception as e:
            print(f"[AUDIO ERROR]: {e}")

    def play(self) -> None:
        if self.loaded and not mixer.music.get_busy():
            mixer.music.play(-1)

    def stop(self) -> None:
        if self.loaded and mixer.music.get_busy():
            mixer.music.stop()


class CyberpunkRenderer:
    """Handles all visual HUD elements, graphs, and text rendering."""

    def __init__(self):
        self.graph_data = deque([0.35] * GRAPH_HISTORY_SIZE, maxlen=GRAPH_HISTORY_SIZE)

    def update_graph_data(self, ear_value: float) -> None:
        display_val = max(0.15, min(0.40, ear_value))
        self.graph_data.append(display_val)

    def glow_effect(self, img: np.ndarray, intensity: float = 0.3) -> np.ndarray:
        blur = cv2.GaussianBlur(img, (19, 19), 0)
        return cv2.addWeighted(img, 1, blur, intensity, 0)

    def draw_text(
        self,
        img: np.ndarray,
        text: str,
        pos: tuple,
        scale: float = 0.5,
        color: tuple = NEON_GREEN,
        thick: int = 1,
        align: str = "left",
    ) -> None:
        font = cv2.FONT_HERSHEY_DUPLEX
        size, _ = cv2.getTextSize(text, font, scale, thick)
        x, y = pos
        if align == "right":
            x -= size[0]
        elif align == "center":
            x -= size[0] // 2

        cv2.putText(img, text, (x + 1, y + 1), font, scale, (0, 0, 0), thick + 2)
        cv2.putText(img, text, (x, y), font, scale, color, thick, cv2.LINE_AA)

    def render_project_info(self, frame: np.ndarray) -> None:
        h, w = frame.shape[:2]
        self.draw_text(frame, PROJECT_NAME, (30, 70), 0.8, NEON_CYAN, 1)
        self.draw_text(frame, TEAM_NAME, (30, 95), 0.5, NEON_PURPLE, 1)

        start_y = h - 120
        self.draw_text(
            frame, "TEAM MEMBERS:", (w - 30, start_y), 0.5, NEON_CYAN, 1, "right"
        )
        for i, member in enumerate(MEMBERS):
            y = start_y + 25 + (i * 20)
            self.draw_text(
                frame, f"> {member}", (w - 30, y), 0.4, NEON_GREEN, 1, "right"
            )

    def render_live_graph(
        self, frame: np.ndarray, x_offset: int, y_offset: int
    ) -> None:
        w_panel, h_panel = 550, 320
        fh, fw = frame.shape[:2]
        if x_offset + w_panel > fw:
            x_offset = fw - w_panel - 10

        roi = frame[y_offset : y_offset + h_panel, x_offset : x_offset + w_panel]

        pts = np.array(
            [
                [0, 30],
                [30, 0],
                [200, 0],
                [230, 30],
                [w_panel, 30],
                [w_panel, h_panel],
                [50, h_panel],
                [0, h_panel - 50],
            ],
            np.int32,
        )

        bg_roi = roi.copy()
        cv2.fillPoly(bg_roi, [pts], HUD_BG_COLOR)
        cv2.addWeighted(bg_roi, 0.9, roi, 0.1, 0, roi)
        cv2.polylines(roi, [pts], True, NEON_CYAN, 2, cv2.LINE_AA)

        self.draw_text(roi, "REAL-TIME ALERTNESS", (70, 40), 0.6, NEON_CYAN, 1)
        self.draw_text(roi, "MONITORING SYSTEM", (70, 65), 0.4, NEON_CYAN, 1)

        g_x, g_y, g_w, g_h = 60, 90, w_panel - 80, h_panel - 120
        for i in range(5):
            y = g_y + int(i * (g_h / 4))
            cv2.line(roi, (g_x, y), (g_x + g_w, y), GRID_COLOR, 1)
        for i in range(6):
            x = g_x + int(i * (g_w / 5))
            cv2.line(roi, (x, g_y), (x, g_y + g_h), GRID_COLOR, 1)

        range_span = 0.40 - 0.15

        def val_to_y(val):
            return g_y + g_h - int(((val - 0.15) / range_span) * g_h)

        thresh_y = val_to_y(EYE_AR_THRESH)

        cv2.line(roi, (g_x, thresh_y), (g_x + g_w, thresh_y), NEON_RED, 2)
        self.draw_text(roi, "DROWSY ZONE", (g_x + 10, g_y + g_h - 5), 0.4, NEON_RED, 1)

        points = []
        for i, val in enumerate(self.graph_data):
            x = g_x + int((i / (GRAPH_HISTORY_SIZE - 1)) * g_w)
            y = val_to_y(val)
            y = max(g_y, min(g_y + g_h, y))
            points.append((x, y))

        for i in range(1, len(points)):
            color = NEON_GREEN if self.graph_data[i] > EYE_AR_THRESH else NEON_RED
            cv2.line(roi, points[i - 1], points[i], color, 2, cv2.LINE_AA)

        curr_pt = points[-1]
        curr_ear = self.graph_data[-1]

        cv2.circle(roi, curr_pt, 5, NEON_CYAN, -1)

        status = "AWAKE" if curr_ear > EYE_AR_THRESH else "DROWSY"
        status_col = NEON_GREEN if curr_ear > EYE_AR_THRESH else NEON_RED

        self.draw_text(
            roi,
            f"STATUS: {status}",
            (curr_pt[0] - 100, curr_pt[1] - 25),
            0.5,
            status_col,
            1,
            "right",
        )
        self.draw_text(
            roi,
            f"EAR: {curr_ear:.2f}",
            (curr_pt[0] - 100, curr_pt[1] - 5),
            0.5,
            NEON_CYAN,
            1,
            "right",
        )

        frame[y_offset : y_offset + h_panel, x_offset : x_offset + w_panel] = roi


class FacialSystem:
    """Core AI engine for facial landmark detection and EAR calculation."""

    def __init__(self):
        # 🚨 THE PRO FIX: Using the explicit imports here!
        self.face_mesh = mp_face_mesh.FaceMesh(max_num_faces=1, refine_landmarks=True)
        self.ear_buffer = deque(maxlen=5)

        self.eyes_closed_start_time = None
        self.alarm_start_time = None
        self.alert_sent = False

    def get_ear(self, lms, w: int, h: int) -> float:
        def dist_pts(i1, i2):
            p1 = np.array([lms[i1].x * w, lms[i1].y * h])
            p2 = np.array([lms[i2].x * w, lms[i2].y * h])
            return np.linalg.norm(p1 - p2)

        left_ear = (dist_pts(385, 380) + dist_pts(387, 373)) / (
            2.0 * dist_pts(362, 263)
        )
        right_ear = (dist_pts(160, 144) + dist_pts(158, 153)) / (
            2.0 * dist_pts(33, 133)
        )
        return (left_ear + right_ear) / 2.0

    def process(
        self, frame: np.ndarray, renderer: CyberpunkRenderer, audio: AudioManager
    ) -> None:
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb)
        current_ear = 0.35

        if results.multi_face_landmarks:
            for lms in results.multi_face_landmarks:
                landmarks = lms.landmark

                # 🚨 THE PRO FIX: Explicit reference to FACEMESH_TESSELATION
                for conn in FACEMESH_TESSELATION:
                    p1 = (int(landmarks[conn[0]].x * w), int(landmarks[conn[0]].y * h))
                    p2 = (int(landmarks[conn[1]].x * w), int(landmarks[conn[1]].y * h))
                    cv2.line(frame, p1, p2, (0, 60, 0), 1)

                raw_ear = self.get_ear(landmarks, w, h)
                self.ear_buffer.append(raw_ear)
                current_ear = sum(self.ear_buffer) / len(self.ear_buffer)

                def draw_eye(indices, color):
                    pts = np.array(
                        [
                            (int(landmarks[i].x * w), int(landmarks[i].y * h))
                            for i in indices
                        ]
                    )
                    cv2.polylines(frame, [pts], True, color, 2)

                if current_ear < EYE_AR_THRESH:
                    eye_color = NEON_RED
                    if self.eyes_closed_start_time is None:
                        self.eyes_closed_start_time = time.time()

                    duration = time.time() - self.eyes_closed_start_time

                    if duration <= TIME_TO_WAIT_BEFORE_ALARM:
                        renderer.draw_text(
                            frame,
                            f"EYES CLOSED: {duration:.1f}s",
                            (w // 2, h // 2 + 50),
                            0.8,
                            NEON_WARN,
                            2,
                            "center",
                        )
                    else:
                        audio.play()
                        renderer.draw_text(
                            frame,
                            "!!! DROWSINESS ALERT !!!",
                            (w // 2, h // 2),
                            1.2,
                            NEON_RED,
                            3,
                            "center",
                        )

                        if int(time.time() * 5) % 2 == 0:
                            cv2.rectangle(frame, (0, 0), (w, h), NEON_RED, 20)

                        if self.alarm_start_time is None:
                            self.alarm_start_time = time.time()

                        elapsed_alarm = time.time() - self.alarm_start_time
                        wa_countdown = WHATSAPP_DELAY - int(elapsed_alarm)

                        if wa_countdown > 0:
                            renderer.draw_text(
                                frame,
                                f"MSG TO IBRAHIM IN: {wa_countdown}s",
                                (w // 2, h - 100),
                                0.8,
                                NEON_WARN,
                                2,
                                "center",
                            )
                        else:
                            if not self.alert_sent:
                                trigger_whatsapp_alert()
                                self.alert_sent = True
                            renderer.draw_text(
                                frame,
                                "MSG SENT TO IBRAHIM",
                                (w // 2, h - 100),
                                0.8,
                                NEON_GREEN,
                                2,
                                "center",
                            )
                else:
                    eye_color = NEON_GREEN
                    self.eyes_closed_start_time = None
                    self.alarm_start_time = None
                    self.alert_sent = False
                    audio.stop()

                draw_eye(LEFT_EYE_IDXS, eye_color)
                draw_eye(RIGHT_EYE_IDXS, eye_color)
        else:
            audio.stop()
            self.eyes_closed_start_time = None

        renderer.update_graph_data(current_ear)


def main():
    print("[INFO] Initializing Camera System...")
    cap = cv2.VideoCapture(CAMERA_ID)

    # 🚨 THE PRO FIX: Safe Camera Verification
    if not cap.isOpened():
        print("[FATAL ERROR] Camera not found or occupied! Please check your webcam.")
        return

    cap.set(3, 1280)
    cap.set(4, 720)

    audio = AudioManager(ASSET_PATH)
    renderer = CyberpunkRenderer()
    system = FacialSystem()

    print(f"[INFO] {PROJECT_NAME} Started Successfully. Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[ERROR] Dropped frame or camera disconnected.")
            break

        frame = cv2.flip(frame, 1)

        renderer.draw_text(frame, "SYSTEM ONLINE", (30, 30), 0.5, NEON_GREEN)
        system.process(frame, renderer, audio)
        renderer.render_project_info(frame)

        fh, fw = frame.shape[:2]
        renderer.render_live_graph(frame, x_offset=fw - 580, y_offset=30)

        final_frame = renderer.glow_effect(frame)
        cv2.imshow(WINDOW_NAME, final_frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            print("[INFO] Shutting down system securely...")
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
