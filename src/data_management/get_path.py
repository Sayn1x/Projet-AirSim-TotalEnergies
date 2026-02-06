from pathlib import Path
import json



class GetPath:

    base = Path("./data")

    # =====================

    settings_yolo_depth = base / "settings_presets/yolo_depth_detection.json"

    settingsjson = "C:/Users/frekp/OneDrive/Documents/AirSim/settings.json"

    drone_initial_UE_coordinates = base / "drone_initial_coordinates.json"

    plan_data = base / "plan/plan_data.json"
    plan = base / "plan/assets/plan.tiff"

    arrow = base / "plan/assets/arrow.png"

    waypoints = base / "waypoints"




class Json:

    @staticmethod
    def read(path : Path):
        with open(path) as f:
            data = json.load(f)

        return data
    

    @staticmethod
    def write(path : Path, data):
        with open(path, "w") as f:
            json.dump(data, f, indent=4)
