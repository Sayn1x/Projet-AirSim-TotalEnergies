import cv2
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import json
import os

from data.get_path import GetPath, Json

# -------------------------
# Chargement du plan initial
# -------------------------

plan_path = GetPath.plan
arrow_path = GetPath.arrow

plan_data = Json.read(GetPath.plan_data)
plan_width, plan_height = plan_data["width"], plan_data["height"]

def cv2_to_tk(img):
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return ImageTk.PhotoImage(Image.fromarray(img))

# -------------------------
# Tkinter : fenêtre principale
# -------------------------

root = tk.Tk()
root.title("Plan de la raffinerie")

label_plan = tk.Label(root)
label_plan.pack(padx=10, pady=10)

# Charger le plan
img_plan = cv2.imread(plan_path)
img_plan = cv2.resize(img_plan, (plan_width, plan_height))
photo_plan = cv2_to_tk(img_plan)
label_plan.config(image=photo_plan)
label_plan.image = photo_plan

# -------------------------
# Variables globales
# -------------------------

photos_data = []
current_index = None
base_path = ""
photo_window = None
photo_label = None
img_plan_with_cars = img_plan.copy()

# -------------------------
# Fonctions utilitaires
# -------------------------

def overlay_png(background, overlay, x, y):
    h, w = overlay.shape[:2]
    x -= overlay.shape[1] // 2
    y -= overlay.shape[0] // 2
    roi = background[y:y+h, x:x+w]
    overlay_rgb = overlay[:, :, :3]
    overlay_alpha = overlay[:, :, 3:] / 255.0
    roi[:] = overlay_rgb * overlay_alpha + roi * (1 - overlay_alpha)

def rotate_image(img, angle):
    h, w = img.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, -angle, 1.0)
    return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_TRANSPARENT)

# -------------------------
# Mise à jour du plan
# -------------------------

def update_plan_with_arrow(index):
    img_copy = img_plan_with_cars.copy()

    photo = photos_data[index]
    x = int(photo["x"])
    y = int(photo["y"])
    yaw = float(photo["yaw"])

    img_arrow = cv2.imread(arrow_path, cv2.IMREAD_UNCHANGED)
    img_arrow = cv2.resize(img_arrow, (30, 30))
    img_arrow = rotate_image(img_arrow, yaw)

    overlay_png(img_copy, img_arrow, x, plan_height - y)

    photo_plan_new = cv2_to_tk(img_copy)
    label_plan.config(image=photo_plan_new)
    label_plan.image = photo_plan_new

# -------------------------
# Affichage d'une photo
# -------------------------

def show_photo(index):
    global current_index
    current_index = index

    info = photos_data[index]
    filename = info["Filename"]

    img = cv2.imread(os.path.join(base_path, filename))
    img = cv2.resize(img, (480, 270))
    img_tk = cv2_to_tk(img)

    update_plan_with_arrow(index)

    photo_label.config(image=img_tk)
    photo_label.image = img_tk
    photo_window.title(filename)

# -------------------------
# Navigation
# -------------------------

def next_photo():
    if current_index < len(photos_data) - 1:
        show_photo(current_index + 1)

def prev_photo():
    if current_index > 0:
        show_photo(current_index - 1)

# -----------------
# Ouvrir une image 
# -----------------

def ouvrir_fichier():
    global photos_data, base_path, photo_window, photo_label

    chemin = filedialog.askopenfilename(
        title="Choisir une image",
        filetypes=[("Images", "*.png *.jpg *.jpeg *.tiff *.bmp")]
    )
    if not chemin:
        return

    base_path, photo_file = os.path.split(chemin)

    # Charger le JSON associé
    data_photo_path = os.path.join(base_path, "data_photos.json")
    with open(data_photo_path) as f:
        photos_data = json.load(f)

    # Trouver l'index de la photo ouverte
    for i, p in enumerate(photos_data):
        if p["Filename"] == photo_file:
            start_index = i
            break

    # Créer la fenêtre photo
    photo_window = tk.Toplevel(root)
    photo_window.bind("<Right>", lambda e: next_photo())
    photo_window.bind("<Left>", lambda e: prev_photo())
    photo_window.focus_set()


    photo_window.title(photo_file)

    photo_label = tk.Label(photo_window)
    photo_label.pack(padx=10, pady=10)

    frame_btn = tk.Frame(photo_window)
    frame_btn.pack()

    tk.Button(frame_btn, text="<< Précédente", command=prev_photo).pack(side="left", padx=5)
    tk.Button(frame_btn, text="Suivante >>", command=next_photo).pack(side="left", padx=5)

    show_photo(start_index)


def ouvrir_voitures():
    global img_plan_with_cars

    chemin = filedialog.askopenfilename(
        title="Choisir un fichier JSON de voitures",
        filetypes=[("JSON", "*.json")]
    )
    if not chemin:
        return

    with open(chemin) as f:
        voitures = json.load(f)

    # Repartir du plan original
    img_plan_with_cars = img_plan.copy()

    # Dessiner les voitures
    for v in voitures:
        x = int(v["x"])
        y = int(v["y"])
        y_canvas = y

        # Point vert
        cv2.circle(img_plan_with_cars, (x, y_canvas), 6, (0, 255, 0), -1)

        # Cercle autour
        cv2.circle(img_plan_with_cars, (x, y_canvas), 40, (0, 255, 0), 2)

    # Afficher le plan mis à jour
    photo_plan_new = cv2_to_tk(img_plan_with_cars)
    label_plan.config(image=photo_plan_new)
    label_plan.image = photo_plan_new

# -------------------------
# Menu
# -------------------------

menu_bar = tk.Menu(root)
root.config(menu=menu_bar)

menu_fichier = tk.Menu(menu_bar, tearoff=0)
menu_bar.add_cascade(label="Fichier", menu=menu_fichier)

menu_fichier.add_command(label="Open photos", command=ouvrir_fichier)
menu_fichier.add_command(label="Cars locations (.json)", command=ouvrir_voitures)
menu_fichier.add_command(label="Quitter", command=root.quit)

root.mainloop()