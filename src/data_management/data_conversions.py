import airsim
import math

from .get_path import GetPath, Json
from .drone_basic_functions import Drone


drone_initial_UE_coordinates = Json.read(GetPath.drone_initial_UE_coordinates)

UE_X_INITIAL_DRONE = drone_initial_UE_coordinates["x"]
UE_Y_INITIAL_DRONE = drone_initial_UE_coordinates["y"]
UE_Z_INITIAL_DRONE = drone_initial_UE_coordinates["z"]

plan_data = Json.read(GetPath.plan_data)

PLAN_HEIGHT = plan_data["height"]
PLAN_X_ORIGIN = plan_data["x_unreal_origin_in_px"]
PLAN_Y_ORIGIN = plan_data["y_unreal_origin_in_px"]
# SCALE_PLAN must be multiplied by x_unreal and y_unreal to get x and y on the plan
SCALE_PLAN = plan_data["100m"] / 10000



class FromAirsim:

    @staticmethod
    def to_unreal_position(client):
        drone_position = Drone.get_position(client)

        # meters (AirSim unit) -> cm (UE unit)
        drone_position_delta = [drone_position.x_val * 100, drone_position.y_val * 100, - drone_position.z_val * 100]

        x_unreal = UE_X_INITIAL_DRONE + drone_position_delta[0]
        y_unreal = UE_Y_INITIAL_DRONE + drone_position_delta[1]
        z_unreal = UE_Z_INITIAL_DRONE + drone_position_delta[2]

        return x_unreal, y_unreal, z_unreal

    

    @staticmethod
    def to_plan_position(client):
        x_unreal, y_unreal, z_unreal = FromAirsim.to_unreal_position(client)

        # coordinates of the point on the map 
        x_img = round((PLAN_X_ORIGIN + (x_unreal * SCALE_PLAN)), 3)
        y_img = round(((PLAN_HEIGHT - PLAN_Y_ORIGIN) - (y_unreal * SCALE_PLAN)), 3)

        # altitude | cm -> meter conversion
        altitude = round(((z_unreal - UE_Z_INITIAL_DRONE) / 100), 3)

        yaw_rad = airsim.to_eularian_angles(client.getMultirotorState().kinematics_estimated.orientation)[2]
        # angle conversion to get 0° on the -y axis of UE
        yaw_deg = round( ((((math.degrees(yaw_rad) + 360) % 360) + 90) % 360), 3)

        gimbal_pitch = round(Drone.obtain_absolute_camera_pitch(client), 3)

        return x_img, y_img, altitude, yaw_deg, gimbal_pitch
    

    class Coordinates:

        @staticmethod
        def to_unreal_position(client, x_airsim, y_airsim, z_airsim) :

            x_unreal = UE_X_INITIAL_DRONE + x_airsim * 100
            y_unreal = UE_Y_INITIAL_DRONE + y_airsim * 100
            z_unreal = UE_Z_INITIAL_DRONE + z_airsim * 100

            return x_unreal, y_unreal, z_unreal
    

class FromPlan:

    @staticmethod
    def to_unreal_position(x_plan, y_plan):
        x_unreal = (x_plan - PLAN_X_ORIGIN) * (1 / SCALE_PLAN)
        y_unreal = (y_plan - PLAN_Y_ORIGIN) * (1 / SCALE_PLAN)

        return x_unreal, y_unreal
    


class FromUnreal:

    @staticmethod
    def to_airsim_position(x_unreal, y_unreal, z_unreal):
        x_airsim = (x_unreal - UE_X_INITIAL_DRONE) / 100
        y_airsim = (y_unreal - UE_Y_INITIAL_DRONE) / 100
        z_airsim = - ((z_unreal - UE_Z_INITIAL_DRONE) / 100)

        return x_airsim, y_airsim, z_airsim
    
    @staticmethod
    def coordinates_to_plan_position(x, y, z):
        x_plan = round((PLAN_X_ORIGIN + (x * SCALE_PLAN)), 3)
        y_plan = round(PLAN_Y_ORIGIN + (y * SCALE_PLAN), 3)

        # altitude | cm -> meter conversion
        altitude = round(((z - UE_Z_INITIAL_DRONE) / 100), 3)

        return x_plan, y_plan, altitude

