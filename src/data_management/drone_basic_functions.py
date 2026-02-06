import airsim
import math
import numpy as np


class Drone:

    @staticmethod
    def initialization():
        client = airsim.MultirotorClient()
        client.confirmConnection()
        client.enableApiControl(True)
        client.armDisarm(True)
        return client
    
    
    @staticmethod
    def takeoff(client):
        client.takeoffAsync().join()


    @staticmethod
    def get_position(client):
        return client.getMultirotorState().kinematics_estimated.position

    @staticmethod
    def get_rotation(client):
        return client.getMultirotorState().kinematics_estimated.orientation
    

    @staticmethod
    def get_yaw_drone(client):
        '''
        retourne le yaw ABSOLU du drone dans le repère MONDE, en radians.
        '''
        rotation = client.getMultirotorState().kinematics_estimated.orientation

        roll, pitch, yaw = airsim.to_eularian_angles(rotation)

        return yaw

    @staticmethod
    def get_pitch_drone(client):
        rotation = client.getMultirotorState().kinematics_estimated.orientation

        roll, pitch, yaw = airsim.to_eularian_angles(rotation)

        return pitch
    
    @staticmethod
    def get_roll_drone(client):
        rotation = client.getMultirotorState().kinematics_estimated.orientation

        roll, pitch, yaw = airsim.to_eularian_angles(rotation)

        return roll
    
    

    @staticmethod
    def get_camera_pitch(client):
        # Récupération des infos de la caméra 
        cam_info = client.simGetCameraInfo("0")

        # Orientation en quaternion 
        q = cam_info.pose.orientation

        pitch, roll, yaw = airsim.to_eularian_angles(q)

        pitch_rad = pitch
        pitch_deg = math.degrees(pitch_rad)


        return pitch_deg
    

    @staticmethod
    def obtain_absolute_camera_pitch(client):
        # Pitch du drone
        drone_q = Drone.get_rotation(client)
        drone_pitch, _, _ = airsim.to_eularian_angles(drone_q)
        drone_pitch_deg = math.degrees(drone_pitch)

        # Pitch caméra relatif
        cam_pitch_deg = Drone.get_camera_pitch(client)

        # Pitch caméra absolu
        cam_pitch_world = drone_pitch_deg + cam_pitch_deg

        return cam_pitch_world
    




    class Sensor:
        
        class Camera:

            @staticmethod
            def get_camera_pitch(client):
                # Récupération des infos de la caméra 
                cam_info = client.simGetCameraInfo("0")

                # Orientation en quaternion 
                q = cam_info.pose.orientation

                pitch, roll, yaw = airsim.to_eularian_angles(q)

                pitch_rad = pitch
                pitch_deg = math.degrees(pitch_rad)


                return pitch_deg
            

            @staticmethod
            def obtain_absolute_camera_pitch(client):
                # Pitch du drone
                drone_q = Drone.get_rotation(client)
                drone_pitch, _, _ = airsim.to_eularian_angles(drone_q)
                drone_pitch_deg = math.degrees(drone_pitch)

                # Pitch caméra relatif
                cam_pitch_deg = Drone.get_camera_pitch(client)

                # Pitch caméra absolu
                cam_pitch_world = drone_pitch_deg + cam_pitch_deg

                return cam_pitch_world
            

            @staticmethod
            def get_depth_map(client):

                responses = client.simGetImages([
                    airsim.ImageRequest("0", airsim.ImageType.DepthPerspective, True)
                ])

                resp = responses[0]

                depth_array = np.array(resp.image_data_float, dtype=np.float32)

                depth_image = depth_array.reshape(resp.height, resp.width)

                return depth_image
            

            @staticmethod
            def get_rgb_image(client):
                    '''
                    Retourne une image NumpPy (OpenCV)
                    '''
                    responses = client.simGetImages([airsim.ImageRequest("0", airsim.ImageType.Scene, False, False)])
                    img1d = np.frombuffer(responses[0].image_data_uint8, dtype=np.uint8)
                    image = img1d.reshape(responses[0].height, responses[0].width, 3)

                    return image

            

