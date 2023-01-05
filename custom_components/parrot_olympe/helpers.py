"""Parrot Olympe helper."""

import logging
import time
import threading
import cv2
import numpy as np

import olympe
from olympe.messages.wifi import rssi_changed
from olympe.messages.common.CommonState import BatteryStateChanged
from olympe.messages.ardrone3.PilotingState import (
    AltitudeChanged,
    FlyingStateChanged,
)

_LOGGER = logging.getLogger(__name__)


class ParrotOlympeHelper:
    """Connects to Parrot Olympe to get information."""

    def __init__(self, address) -> None:
        """Initialize the class object."""

        olympe.log.update_config({"loggers": {"olympe": {"level": "ERROR"}}})
        self.address = address
        self.drone = olympe.Drone(self.address)
        self.drone_connected = False
        self.drone_frame = None
        self.drone_states = self.DroneListener(self.drone)
        self.drone_states.subscribe()
        self.started = True

    def connect(self):
        """Start thread to connect to drone."""

        self.thread = threading.Thread(target=self.thread_connect)
        self.thread.setDaemon(True)
        self.thread.start()

    def thread_connect(self):
        """Connects to Anafi Drone."""

        while self.started:
            # Trying to connect to controller
            while not self.drone.connected:
                time.sleep(1)
                self.drone.connect()
                if self.drone.connected:
                    _LOGGER.info("Connected to controller")
                else:
                    _LOGGER.info("Retrying controller connection")

            # Trying to connect to drone
            connection_state = self.drone.connection_state()
            while not connection_state and self.drone.connected:
                time.sleep(1)
                connection_state = self.drone.connection_state()
                if not connection_state:
                    _LOGGER.info("Retrying drone connection")
                    self.drone_connected = False
            if not self.drone_connected and connection_state:
                _LOGGER.info("Connected to drone")
                self.drone_connected = True
                self.video_start()

            time.sleep(15)
        _LOGGER.info("Stoped connect thread")

    def disconnect(self):
        """Disconnect drone gracefully."""

        self.video_stop()
        self.started = False
        self.thread.join()
        _LOGGER.info("Disconnected")

    def video_start(self):
        """Start video stream."""

        self.drone.streaming.set_callbacks(
            raw_cb=self.yuv_frame_cb,
        )
        self.drone.streaming.start()

    def yuv_frame_cb(self, yuv_frame):
        """Read and convert video frame."""

        cv2_cvt_color_flag = {
            olympe.VDEF_I420: cv2.COLOR_YUV2BGR_I420,
            olympe.VDEF_NV12: cv2.COLOR_YUV2BGR_NV12,
        }[yuv_frame.format()]

        # Use OpenCV to convert the yuv frame to RGB
        print("new frame")
        self.drone_frame = cv2.cvtColor(
            yuv_frame.as_ndarray(),
            cv2_cvt_color_flag)

    def get_image(self):
        """Convert image to jpg."""

        frame = self.drone_frame
        if self.drone_frame is None:
            frame = np.zeros((768, 1360, 3), np.uint8)

        ret, buffer = cv2.imencode('.jpg', frame)
        return buffer.tobytes()

    def video_stop(self):
        """Stop Video gracefully."""

        self.drone.streaming.stop()
        self.drone_frame = None

    class DroneListener(olympe.EventListener):
        """Listen to drone events."""

        def __init__(self, *args, **kwds):
            """Initialize Drone Listener."""

            super().__init__(*args, **kwds)
            drone = args[0]
            self.alt = 0
            self.rssi = 0
            self.battery = 0
            self.state = ""
            try:
                self.battery = drone.get_state(BatteryStateChanged)['percent']
            except:
                pass
            try:
                self.state = drone.get_state(FlyingStateChanged)['state'].name
            except:
                pass
            try:
                self.rssi = drone.get_state(rssi_changed)['rssi']
            except:
                pass

        @olympe.listen_event(rssi_changed(_policy="wait"))
        def rssi_change(self, event, scheduler):
            """Returns RSSI."""

            self.rssi = event.args['rssi']

        @olympe.listen_event(BatteryStateChanged(_policy="wait"))
        def BatteryStateChange(self, event, scheduler):
            """ Return Battery Charge"""

            self.battery = event.args["percent"]

        @olympe.listen_event(AltitudeChanged(_policy="wait"))
        def AltitudeChange(self, event, scheduler):
            """Returns Altitude."""

            self.alt = event.args['altitude']

        @olympe.listen_event(FlyingStateChanged(_policy="wait"))
        def FlyingStateChange(self, event, scheduler):
            """Returns drone state."""

            self.state = event.args['state'].name


if __name__ == "__main__":
    poh = ParrotOlympeHelper("10.202.0.1")
    poh.connect()
    time.sleep(5)
    poh.video_start()

    while(True):
        if poh.drone_frame is not None:
            cv2.imshow('frame', poh.drone_frame)
            cv2.waitKey(1)

    cv2.destroyAllWindows()
