import airsim
from pathlib import Path
import threading
import math
import time
import numpy as np
from PIL import Image
import io
from datetime import datetime
import os
import json
import cv2

from data_management.drone_basic_functions import Drone
from data_management.data_conversions import FromAirsim, FromUnreal
from data_management.get_path import GetPath, Json
from yolo.yolo_airsim import Detection


# =========================================
''' quand le parcours est prêt on peut uitiliser ce script pour l'appliquer et lancer la patrouille. lancer d'abord le run dans unreal puis lancer celuici'''

print("Chargement des donnees de parcours")
waypoints_base_path = GetPath.waypoints

while True:
    file_name = input("\tNom du fichier : ")
    file_name = file_name.removesuffix(".json")

    default_path = Path(waypoints_base_path) / file_name

    file_path = default_path / (file_name + ".json")

    if file_path.is_file():
        print("Lancement du programme...")
        break
    else:
        print("Le fichier n'existe pas.")

waypoints_data = Json.read(file_path)


# =========================================


client = Drone.initialization()
Drone.takeoff(client)


# =========================================


threading.Thread(target = Detection.yolo_loop, daemon = True).start()


# =========================================
# VARIABLES
# =========================================

# move
velocity = 4

# yolo
car_conf_history = []
truck_conf_history = []
last_seen_car_time = 0
last_seen_truck_time = 0
DELAY_MAX = 4
N_MIN_YOLO_COUNTER = 4
positions_detected_objects = []
detections = []

i = 0
timer_car_stop = 0
timer_truck_stop = 0
car_stop = False
truck_stop = False

car_detection_delay = 0
truck_detection_delay = 0

car_validated = False
truck_validated = False

stop_time = 0

car_depth_map_flag = False
truck_depth_map_flag = False

# take_a_photo
last_photo_distance = 0
last_photo_position = [0,0,0]
photo_file_number = 0
photos_folder_date = datetime.now().strftime("%Y-%m-%d_%H-%M")
photo_positions_data = []



# =========================================
# FONCTIONS
# =========================================


def distance_to_the_object(box) :
    drone_position = Drone.get_position(client)
    print("Analyse... (YOLO + Depth Map)")
    depth_image = Drone.Sensor.Camera.get_depth_map(client)
    print("Fin de l'analyse")

    x1, y1, x2, y2 = box.xyxy[0]
    cx = int(((x1 + x2) / 2) / 3)
    cy = int(((y1 + y2) / 2) / 3)

    patch = depth_image[cy-2:cy+3, cx-2:cx+3]

    distance = np.median(patch)

    distance_x = distance * math.cos(Drone.get_yaw_drone(client))
    distance_y = distance * math.sin(Drone.get_yaw_drone(client))

    x_object_airsim = drone_position.x_val + distance_x
    y_object_airsim = drone_position.y_val + distance_y

    x_object_unreal, y_object_unreal, _ = FromAirsim.Coordinates.to_unreal_position(client, x_object_airsim, y_object_airsim, 0)

    return distance, x_object_unreal, y_object_unreal


def distance_to_the_object_v2(depth_map, box) :

    drone_position = Drone.get_position(client)

    x1, y1, x2, y2 = box.xyxy[0]
    cx = int(((x1 + x2) / 2) / 3)
    cy = int(((y1 + y2) / 2) / 3)

    patch = depth_map[cy-2:cy+3, cx-2:cx+3]

    distance = np.median(patch)

    distance_x = distance * math.cos(Drone.get_yaw_drone(client))
    distance_y = distance * math.sin(Drone.get_yaw_drone(client))

    x_object_airsim = drone_position.x_val + distance_x
    y_object_airsim = drone_position.y_val + distance_y

    x_object_unreal, y_object_unreal, _ = FromAirsim.Coordinates.to_unreal_position(client, x_object_airsim, y_object_airsim, 0)

    return distance, x_object_unreal, y_object_unreal



def show_yolo_detection(image, box, label, conf):
    """
    image : np.ndarray (RGB)
    box   : YOLO box
    """

    img = image.copy()

    x1, y1, x2, y2 = map(int, box.xyxy[0])

    # Rectangle
    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)

    # Texte
    text = f"{label} {conf:.2f}"
    cv2.putText(
        img,
        text,
        (x1, y1 - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (0, 255, 0),
        2
    )

    # OpenCV attend du BGR
    img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    cv2.imshow("YOLO validation", img_bgr)
    cv2.waitKey(1)  # indispensable pour rafraîchir la fenêtre



def yolo(x_destination, y_destination, z_destination, velocity):
    global car_conf_history, truck_conf_history, last_seen_car_time, last_seen_truck_time, DELAY_MAX, N_MIN_YOLO_COUNTER, i, timer_car_stop, timer_truck_stop, car_stop, truck_stop, stop_time, detections, car_detection_delay, truck_detection_delay, car_validated, truck_validated
    car_detected = False
    truck_detected = False
    car_box = None
    truck_box = None

    # TIMEOUT
    stop_time = 0


    if (time.time() - car_detection_delay > 10) and car_validated:
        car_validated = False
    if (time.time() - truck_detection_delay > 10) and truck_validated :
        truck_validated = False


    # state of the drone during the capture
    angle_rgb = Drone.get_yaw_drone(client)
    pos_rgb = Drone.get_position(client)

    # send
    rgb = Drone.Sensor.Camera.get_rgb_image(client)

    '''
    while not Detection.result_queue.empty():
        Detection.result_queue.get_nowait()
    '''

    Detection.image_queue.put(rgb)

    i += 1
    #print(f"envoie n ° {i}")

    # receive
    if not Detection.result_queue.empty() :

        car_detected = False
        truck_detected = False
        car_box = None
        truck_box = None

        rgb_yolo, results = Detection.result_queue.get()


        for box in results[0].boxes:

            cls = int(box.cls[0])

            if Detection.model.names[cls] == "car":

                car_detected = True
                car_box = box
                car_conf = float(box.conf[0])
                break

            elif Detection.model.names[cls] == "truck":

                truck_detected = True
                truck_box = box
                truck_conf = float(box.conf[0])
                break



        if car_detected :
            # all(math.hypot(Drone.get_position(client).x_val - x_already_registred, Drone.get_position(client).y_val - y_already_registred) > 30 for x_already_registred, y_already_registred in detections)
            if car_conf >= 0.7 and not car_validated :
                
                
                downtime_counter = time.time()

                client.rotateToYawAsync(math.degrees(angle_rgb)).join()
                client.moveToPositionAsync(pos_rgb.x_val, pos_rgb.y_val, pos_rgb.z_val, 4).join()
                client.moveByVelocityBodyFrameAsync(-2, 0, 1, duration=1).join()

                time.sleep(1.5)

                rgb = Drone.Sensor.Camera.get_rgb_image(client)
                results = Detection.model(rgb, verbose=False)


                for box in results[0].boxes:

                    cls = int(box.cls[0])

                    if Detection.model.names[cls] == "car":

                        car_validated = True

                        car_box = box
                        car_conf = float(box.conf[0])
                        
                        distance, x_car_unreal, y_car_unreal = distance_to_the_object(car_box)


                        print(f"\nVoiture détectée à {distance}m !")
                        print(f"\nx_car_unreal : {x_car_unreal}\ny_car_unreal : {y_car_unreal}\n")


                        detections.append((Drone.get_position(client).x_val, Drone.get_position(client).y_val))

                        x_plan, y_plan, _ = FromUnreal.coordinates_to_plan_position(float(x_car_unreal), float(y_car_unreal), 0)

                        positions_detected_objects.append({"Object_type" : "car", "x" : x_plan, "y" : y_plan})
                        break

                stop_time = time.time() - downtime_counter
                car_detection_delay = time.time()

                return "STOP"



        if truck_detected :
            if truck_conf >= 0.7 and not truck_validated :

                downtime_counter = time.time()
                
                client.rotateToYawAsync(math.degrees(angle_rgb)).join()
                client.moveToPositionAsync(pos_rgb.x_val, pos_rgb.y_val, pos_rgb.z_val, 4).join()
                client.moveByVelocityBodyFrameAsync(-1, 0, 1, duration=1).join()

                time.sleep(0.5)

                rgb = Drone.Sensor.Camera.get_rgb_image(client)
                results = Detection.model(rgb, verbose=False)


                for box in results[0].boxes:

                    cls = int(box.cls[0])

                    if Detection.model.names[cls] == "truck":

                        truck_validated = True

                        truck_box = box
                        truck_conf = float(box.conf[0])
                        
                        distance, x_truck_unreal, y_truck_unreal = distance_to_the_object(truck_box)


                        print(f"\nCamion détecté à {distance}m !")
                        print(f"\nx_truck_unreal : {x_truck_unreal}\ny_truck_unreal : {y_truck_unreal}\n")

                        x_plan, y_plan, _ = FromUnreal.coordinates_to_plan_position(float(x_truck_unreal), float(y_truck_unreal), 0)

                        positions_detected_objects.append({"Object_type" : "truck", "x" : x_plan, "y" : y_plan})
                        break

                
                stop_time = time.time() - downtime_counter
                truck_detection_delay = time.time()
                
                return "STOP"



            


def take_a_photo() :
    global last_photo_position, last_photo_distance, photo_file_number, photos_folder_date, positions_photo_data

    drone_position = Drone.get_position(client)
    last_photo_distance = math.sqrt((drone_position.x_val - last_photo_position[0]) ** 2
                                    + (drone_position.y_val - last_photo_position[1]) ** 2
                                    + (drone_position.z_val - last_photo_position[2]) ** 2)
    
    if last_photo_distance >= 2 :
        last_photo_position = [drone_position.x_val, drone_position.y_val, drone_position.z_val]

        # Capture une image PNG depuis la caméra 0
        png_image = client.simGetImage("0", airsim.ImageType.Scene)

        # Convertir l'image PNG en JPEG
        image = Image.open(io.BytesIO(png_image))

        # Dossier photos
        photos_dir = default_path / f"photos-{photos_folder_date}"
        os.makedirs(photos_dir, exist_ok=True)

        # Nom du fichier
        photo_file_number += 1
        photo_file_name = f"rgb-{photo_file_number}.jpg"
        file_path = photos_dir / photo_file_name

        # Sauvegarder l'image en JPEG
        image.convert('RGB').save(file_path, "JPEG")

        x_img, y_img, z_img, yaw_deg, gimbal_pitch = FromAirsim.to_plan_position(client)
        photo_positions_data.append({"Filename": photo_file_name, "x": x_img, "y": y_img, "z": z_img, "yaw": yaw_deg, "gimbal_pitch": gimbal_pitch, "date": datetime.now().strftime("%Y-%m-%d_%H-%M-%S")})



def save_photo_and_detection_informations() :

    global photos_folder_date, photo_positions_data, positions_detected_objects

    photo_file_path = os.path.join(default_path, f"photos-{photos_folder_date}", "data_photos.json")
    with open(photo_file_path, "w") as f:
        json.dump(photo_positions_data, f, indent=4)
    print("Informations relatives aux photos enregistrees dans :", photo_file_path)

    detected_objects_file_path = os.path.join(default_path, f"photos-{photos_folder_date}", "detected_objects.json")
    with open(detected_objects_file_path, "w") as f:
        json.dump(positions_detected_objects, f, indent=4)
    print("Informations relatives aux photos enregistrees dans :", detected_objects_file_path)



def moveAndCapture(x_destination, y_destination, z_destination, velocity, yaw_mode = None) :


    if not yaw_mode :
        client.moveToPositionAsync(x_destination, y_destination, z_destination, velocity)
    else :
        client.moveToPositionAsync(x_destination, y_destination, z_destination, velocity, yaw_mode= yaw_mode)


    start_time = time.time()
    distance = math.sqrt(
        (x_destination - Drone.get_position(client).x_val)**2
        + (y_destination - Drone.get_position(client).y_val)**2
        + (z_destination - Drone.get_position(client).z_val)**2)

    TIMEOUT = distance / velocity + 5


    while True :
        current_position = Drone.get_position(client)

        distance_to_the_target = math.sqrt(
            (x_destination - current_position.x_val) ** 2 + 
            (y_destination - current_position.y_val) ** 2 + 
            (z_destination - current_position.z_val) ** 2)
        
        if distance_to_the_target < 1 :
            break

        if time.time() - start_time > TIMEOUT :
            break


        take_a_photo()
        state = yolo(x_destination, y_destination, z_destination, velocity)
        TIMEOUT += stop_time
        # print(f"timeout : {TIMEOUT}")

        if state == "STOP" :

            #print("lancement nouveau mouvement")

            current_position = Drone.get_position(client)
            current_x = current_position.x_val
            current_y = current_position.y_val

            delta_x = x_destination - current_x
            delta_y = y_destination - current_y

            angle_rad = math.atan2(delta_y, delta_x)
            angle_deg = math.degrees(angle_rad)
            angle_deg = (angle_deg + 180) % 360 - 180

            client.moveToPositionAsync(x_destination, y_destination, z_destination, velocity, yaw_mode = airsim.YawMode(is_rate = False, yaw_or_rate = angle_deg))

    


# =========================================
# PROGRAM
# =========================================



for point in waypoints_data :

    current_position = Drone.get_position(client)
    current_x = current_position.x_val
    current_y = current_position.y_val
    current_z = current_position.z_val 

    x_destination, y_destination, z_destination = FromUnreal.to_airsim_position(point["x"], point["y"], point["z"])

    delta_x = x_destination - current_x
    delta_y = y_destination - current_y
    delta_z = z_destination - current_z

    horizontal_distance = math.sqrt(delta_x ** 2 + delta_y ** 2)
    vertical_distance = abs(delta_z)

    angle_rad = math.atan2(delta_y, delta_x)
    angle_deg = math.degrees(angle_rad)
    angle_deg = (angle_deg + 180) % 360 - 180


    # move to the point | don't rotate for small movements
    if vertical_distance > 2 * horizontal_distance :
        moveAndCapture(x_destination, y_destination, z_destination, velocity)
    else :
        moveAndCapture(x_destination, y_destination, z_destination, velocity, yaw_mode = airsim.YawMode(is_rate = False, yaw_or_rate = angle_deg))


    if point["inspection"]:
        time.sleep(3)
        t = 0
        while t < 4 :
            gimbal_pitch = - math.radians(45) * math.sin(t * math.pi / 4)

            orientation = airsim.to_quaternion(gimbal_pitch, 0, 0)

            # Pose de la caméra (position fixe, orientation variable)
            pose = airsim.Pose(airsim.Vector3r(0, 0, 0), orientation)
            # Application de la pose
            client.simSetCameraPose("0", pose)

            t += 0.02
            time.sleep(0.02)


    # wait 0.5s before going to the next point
    time.sleep(0.5)


client.landAsync().join()

save_photo_and_detection_informations()