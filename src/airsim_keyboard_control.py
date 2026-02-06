import airsim
import time
import math
from pynput import keyboard
from datetime import datetime
import os


from data_management.get_path import GetPath, Json
from data_management.data_conversions import FromAirsim


# =========================
# INITIALISATION
# =========================

trigger_affichage = False
mode_enregistrement = False
fermer_fenetres = False
waypoints = []
pressed_keys = set()

speed = 4
yaw_rate_speed = 60

last_time_yolo = 0


#Detection.start()


# =========================
# CONNEXION AIRSIM
# =========================

client = airsim.MultirotorClient()
client.confirmConnection()
client.enableApiControl(True)
client.armDisarm(True)
client.takeoffAsync().join()

'''
# Activer la météo 
client.simEnableWeather(True)
client.simSetWeatherParameter(airsim.WeatherParameter.Rain, 0.8)
client.simSetWeatherParameter(airsim.WeatherParameter.Fog, 0.5)
'''


print("Contrôles :")
print("Z/S = Avant / Arrière")
print("Q/D = Gauche / Droite")
print("Espace = Monter")
print("Shift = Descendre")
print("A/E = Yaw gauche / droite")
print("P = Prendre une photo")
print("CTRL + C = Quitter")


# =========================
# CLAVIER (pynput)
# =========================

def on_press(key):
    global trigger_affichage, mode_enregistrement, fermer_fenetres

    try:
        char = key.char.lower()
        pressed_keys.add(char)

        if char == 'p':
            trigger_affichage = True

        if mode_enregistrement:
            if char == 'y':
                x, y, z = FromAirsim.to_unreal_position(client)
                waypoints.append({"x": x, "y": y, "z": z})
                print(f"Position enregistrée : {x:.2f}, {y:.2f}, {z:.2f}")
                fermer_fenetres = True
                mode_enregistrement = False

            elif char == 'n':
                print("Position ignorée.")
                fermer_fenetres = True
                mode_enregistrement = False

        if char == "g":
            x, y, z = FromAirsim.to_unreal_position(client)
            waypoints.append({"x": x, "y": y, "z": z, "inspection": True})
            print(f"Position enregistrée avec inspection : {x:.2f}, {y:.2f}, {z:.2f}")


        if char == "h":
            x, y, z = FromAirsim.to_unreal_position(client)
            waypoints.append({"x": x, "y": y, "z": z, "inspection": False})
            print(f"Position enregistrée sans inspection : {x:.2f}, {y:.2f}, {z:.2f}")

    except AttributeError:
        pressed_keys.add(key)


def on_release(key):
    try:
        pressed_keys.discard(key.char)
    except AttributeError:
        pressed_keys.discard(key)


listener = keyboard.Listener(on_press=on_press, on_release=on_release, daemon=True)
listener.start()


# =========================
# BOUCLE PRINCIPALE
# =========================


try:
    while True:

        # --- Affichage / capture ---
        if trigger_affichage:
            img_cam, img_plan = map.generer_images(client)
            map.afficher_images(img_cam, img_plan)
            print("\nVoulez-vous enregistrer la position ? (y/n)")
            mode_enregistrement = True
            trigger_affichage = False

        if fermer_fenetres:
            map.fermer_fenetres()
            fermer_fenetres = False

        # --- Commandes ---
        v_forward = 0
        v_right = 0
        v_z = 0
        yaw_rate = 0

        if 'z' in pressed_keys:
            v_forward = speed
        if 's' in pressed_keys:
            v_forward = -speed
        if 'q' in pressed_keys:
            v_right = -speed
        if 'd' in pressed_keys:
            v_right = speed

        if keyboard.Key.space in pressed_keys:
            v_z = -speed
        if keyboard.Key.shift in pressed_keys:
            v_z = speed

        if 'a' in pressed_keys:
            yaw_rate = -yaw_rate_speed
        if 'e' in pressed_keys:
            yaw_rate = yaw_rate_speed

        # --- Conversion repère ---
        state = client.getMultirotorState()
        yaw = airsim.to_eularian_angles(
            state.kinematics_estimated.orientation
        )[2]

        vx = v_forward * math.cos(yaw) - v_right * math.sin(yaw)
        vy = v_forward * math.sin(yaw) + v_right * math.cos(yaw)

        client.moveByVelocityAsync(
            vx, vy, v_z, 0.1,
            yaw_mode=airsim.YawMode(is_rate=True, yaw_or_rate=yaw_rate)
        )

        time.sleep(0.03)

# =========================
# ARRÊT
# =========================

except KeyboardInterrupt:
    print("\nArrêt demandé (Ctrl + C)")

finally:
    print("Nettoyage en cours...")

    try:
        listener.stop()
    except Exception:
        pass

    try:
        client.moveByVelocityAsync(0, 0, 0, 0.1)
        client.hoverAsync()
    except Exception:
        pass

    try:
        client.armDisarm(False)
        client.enableApiControl(False)
    except Exception:
        pass


    if len(waypoints) != 0:

        file_name = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        folder = os.path.join(GetPath.waypoints, file_name)

        # Crée le dossier si nécessaire
        os.makedirs(folder, exist_ok=True)

        file_path = os.path.join(folder, file_name + ".json")

        Json.write(file_path, waypoints)

        print("Positions enregistrées dans :", file_path)



    print("Fin du programme.")