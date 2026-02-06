from queue import Queue
from ultralytics import YOLO


class Detection :

    model = YOLO("yolov8x.pt", verbose=False)

    image_queue = Queue(maxsize=1)
    result_queue = Queue(maxsize=1)


    def yolo_loop():
        while True:
            rgb = Detection.image_queue.get()
            results = Detection.model(rgb, verbose=False, conf=0.6)
            Detection.result_queue.put((rgb, results))

