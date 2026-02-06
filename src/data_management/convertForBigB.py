#this paragraph contains instructions to add the parent directory in the python path.
import sys
extra_path="C:/local/j0015562/PYTHON_CODES/Geospatial_BigB/src/datamodel"
try:
    sys.path.index(extra_path)
except:  # noqa: E722
    sys.path.append(extra_path)
    
#now you can use import of any routine of BigB
import Drone_Trajectory as DJ

print('ok')