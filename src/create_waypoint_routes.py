import cv2
import tkinter as tk
from tkinter import ttk
import os
from datetime import datetime


#this paragraph contains instructions to add the parent directory in the python path.
import sys
extra_path=os.path.join(os.path.dirname(__file__), "..")
try:
    sys.path.index(extra_path)
except:  # noqa: E722
    sys.path.append(extra_path)

from data.get_path import GetPath, Json  # noqa: E402
from data.data_conversions import FromPlan, FromUnreal  # noqa: E402


# --- settings ---
plan_path = GetPath.plan
plan_data = Json.read(GetPath.plan_data)
plan_width, plan_height = plan_data["width"], plan_data["height"]

drone_initial_UE_coordinates = Json.read(GetPath.drone_initial_UE_coordinates)
UE_Z_INITIAL_DRONE = drone_initial_UE_coordinates["z"]

PLAN_X_INITIAL_DRONE, PLAN_Y_INITIAL_DRONE, _= FromUnreal.coordinates_to_plan_position(drone_initial_UE_coordinates["x"], drone_initial_UE_coordinates["y"], 0)

waypoints = []

slider_value = None


def altitude_cursor(nom):
    """Ouvre une fenêtre Tkinter avec un slider et affiche la valeur en direct."""
    global slider_value

    root = tk.Tk()
    root.title(nom)
    root.geometry("300x140")

    # Variable Tkinter pour suivre la valeur
    val = tk.DoubleVar(value=4.5)

    # Label qui affichera la valeur en temps réel
    label = ttk.Label(root, text=f"Altitude : {val.get():.2f}")
    label.pack(pady=5)

    step = 0.5

    # Fonction appelée à chaque mouvement du slider
    def update_label(event=None):
        valeur_arrondie = round(val.get() / step) * step
        val.set(valeur_arrondie)
        label.config(text=f"Altitude : {val.get():.2f}")

    # Slider
    scale = ttk.Scale(
        root,
        from_=0,
        to=15,
        orient="horizontal",
        variable=val,
        command=update_label  # mise à jour en direct
    )
    scale.pack(pady=10)

    # Bouton de validation
    def validate():
        global slider_value
        slider_value = val.get()
        root.destroy()

    def on_close():
        global slider_value
        slider_value = 4.5
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)

    ttk.Button(root, text="Valider", command=validate).pack(pady=5)

    root.mainloop()
    return slider_value



# when adding a point :
def on_mouse(event, x_plan, y_plan, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        cv2.circle(img_resized, (x_plan, y_plan), 5, (0, 0, 255), -1)

        altitude_value_in_m = altitude_cursor("Waypoint - Inspection")
        altitude = UE_Z_INITIAL_DRONE + altitude_value_in_m * 100

        x_unreal, y_unreal = FromPlan.to_unreal_position(x_plan, y_plan)
        print(f"\nPosition enregistrée avec inspection : x={x_unreal}, y={y_unreal}, z={altitude}")
        waypoints.append({"x": x_unreal, "y": y_unreal, "z": altitude, "inspection": True})

    if event == cv2.EVENT_RBUTTONDOWN:
        cv2.circle(img_resized, (x_plan, y_plan), 5, (255, 0, 0), -1)

        altitude_value_in_m = altitude_cursor("Waypoint")
        altitude = UE_Z_INITIAL_DRONE + altitude_value_in_m * 100

        x_unreal, y_unreal = FromPlan.to_unreal_position(x_plan, y_plan)
        print(f"\nPosition enregistrée sans inspection : x={x_unreal}, y={y_unreal}, z={altitude}")
        waypoints.append({"x": x_unreal, "y": y_unreal, "z": altitude, "inspection": False})


''' this routine is usezd to define points on the map for the patrol mission. Pick the points on the map and associate an altitude in m from ground.
at the end , a new file is created in the directory data/waypoints. config can be chaged in get_path python file.'''
# --- chargement de l'image ---
img = cv2.imread(plan_path)
if img is None:
    raise ValueError("Impossible de charger l'image.")

# redimensionner l'image
img_resized = cv2.resize(img, (plan_width, plan_height))


# Point coordonnées initiales drone
x0 = int(PLAN_X_INITIAL_DRONE)
y0 = int(PLAN_Y_INITIAL_DRONE)

cv2.circle(img_resized, (x0, y0), 5, (0, 255, 0), -1)

cv2.line(img_resized, (x0 - 8, y0), (x0 + 8, y0), (0, 255, 0), 1)
cv2.line(img_resized, (x0, y0 - 8), (x0, y0 + 8), (0, 255, 0), 1)

cv2.putText(
    img_resized,
    "Drone start",
    (x0 + 10, y0 - 10),
    cv2.FONT_HERSHEY_SIMPLEX,
    0.4,
    (0, 255, 0),
    1,
    cv2.LINE_AA
)

# ===============================
# Encadré d'aide (haut droite)
# ===============================

help_text = [
    "Clique gauche : point de passage avec inspection",
    "Clique droit : point de passage"
]

padding = 10
line_height = 18
font_scale = 0.45
thickness = 1

# Calcul taille du rectangle
text_width = 0
for line in help_text:
    (w, h), _ = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
    text_width = max(text_width, w)

box_width = text_width + 2 * padding
box_height = len(help_text) * line_height + 2 * padding

# Position haut droite
x1 = plan_width - box_width - 10
y1 = 10
x2 = plan_width - 10
y2 = y1 + box_height

# Rectangle semi-transparent
overlay = img_resized.copy()
cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 0, 0), -1)
alpha = 0.6
img_resized = cv2.addWeighted(overlay, alpha, img_resized, 1 - alpha, 0)

# Texte
y_text = y1 + padding + line_height - 5
for line in help_text:
    cv2.putText(
        img_resized,
        line,
        (x1 + padding, y_text),
        cv2.FONT_HERSHEY_SIMPLEX,
        font_scale,
        (255, 255, 255),
        thickness,
        cv2.LINE_AA
    )
    y_text += line_height



# --- création de la fenêtre ---
cv2.namedWindow("Plan", cv2.WINDOW_AUTOSIZE)
cv2.resizeWindow("Plan", plan_width, plan_height)

# associer la fonction de callback
cv2.setMouseCallback("Plan", on_mouse)

# --- boucle d'affichage ---
while True:
    cv2.imshow("Plan", img_resized)

    # ESC pour quitter
    if cv2.waitKey(1) & 0xFF == 27:
        break

    # Fermeture via la croix
    if cv2.getWindowProperty("Plan", cv2.WND_PROP_VISIBLE) < 1:
        break


if len(waypoints) != 0:
    file_name = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    folder = os.path.join(GetPath.waypoints, file_name)

    os.makedirs(folder, exist_ok=True)

    file_path = os.path.join(folder, file_name + ".json")
    Json.write(file_path, waypoints)

    print("\nPositions enregistrées dans :", file_path, "\n")

cv2.destroyAllWindows()


cv2.destroyAllWindows()
