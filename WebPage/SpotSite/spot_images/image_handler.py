from PIL import Image
import io
from io import BytesIO
import base64
import bosdyn
import time

from SpotSite.utils import start_thread
from SpotSite.spot_images import stitch_images
from SpotSite.spot_logging import log
from SpotSite.utils import output_to_socket


class Image_Handler:
    def __init__(self, update_robot_state_func=None, image_client=None):
        self.image_stitcher = None
        self._show_video_feed = False
        self._update_robot_state = update_robot_state_func
        self._image_client = image_client

    def set_show_video_feed(self, value):
        self._show_video_feed = value

    def _start_video_loop(self, update_robot_state_func, image_client) -> None:
        """
        Creates a thread to start the main video loop
        """

        self._update_robot_state = update_robot_state_func
        self._image_client = image_client
        self._show_video_feed = True
        if self._update_robot_state is None or self._image_client is None:
            return

        start_thread(self._video_loop)

    def _video_loop(self) -> None:
        """
        Houses and runs the main video feed loop
        """
        self.image_stitcher = stitch_images.Stitcher()
        start_thread(self.image_stitcher.start_glfw_loop)
        log("Started video loop")
        while self._show_video_feed:
            time.sleep(0.01)
            self._get_images()
            self._update_robot_state()

    def _stitch_images(self, image1: bosdyn.client.image, image2: bosdyn.client.image) -> Image:
        """
        Sttiches the right and left from camera images

        Args:
            image1 (bosdyn.client.image): The right camera image
            image2 (bosdyn.client.image): The left camera image

        Returns:
            Image: The stitched image
        """
        try:
            return self.image_stitcher.stitch(image1, image2)
        except bosdyn.client.frame_helpers.ValidateFrameTreeError:
            output_to_socket(
                -1, "<red><bold>Issue with cameras, robot must be rebooted</bold></red>", all=True)

    def _encode_base64(self, image: Image) -> str:
        """
        Encodes an image in base64

        Args:
            image (Image): The image

        Returns:
            str: The image bytes encoded in base64
        """
        if image is None:
            return
        buf = io.BytesIO()
        image.save(buf, format='JPEG')

        bytes_image = buf.getvalue()

        return base64.b64encode(bytes_image).decode("utf8")

    def _get_images(self) -> None:
        """
        Gets and displays all relevant images for the video feed
        """
        try:
            self._send_image("front")
            self._send_image("back")
        except Exception as e:
            pass

    def _stitched_or_stamped(self, image: Image, front_right, front_left) -> str:
        if image is not None:
            return self._encode_base64(image)
        front_right = front_right.shot.image.data
        front_left = front_left.shot.image.data

        img_file = BytesIO(front_right)
        front_right = Image.open(img_file)
        front_right = front_right.rotate(-90)

        img_file = BytesIO(front_left)
        front_left = Image.open(img_file)
        front_left = front_left.rotate(-90)

        full_image = Image.new("RGB", (1280, 480), "white")
        full_image.paste(front_left, (640, 0))
        full_image.paste(front_right, (0, 0))

        return self._encode_base64(full_image)

    def _send_image(self, camera_name: str) -> None:
        """
        Gets and updates the client with an image

        Args:
            camera_name (str): The name of the desired image
        """
        try:
            if camera_name == "front":
                front_right = self._image_client.get_image_from_sources(
                    ["frontright_fisheye_image"])[0]
                front_left = self._image_client.get_image_from_sources(
                    ["frontleft_fisheye_image"])[0]
                image = self._stitch_images(front_right, front_left)
                image = self._stitched_or_stamped(
                    image, front_right, front_left)
            if camera_name == "back":
                back = self._image_client.get_image_from_sources(
                    ["back_fisheye_image"])[0].shot.image.data
                image = base64.b64encode(back).decode("utf8")

            if camera_name == "left":
                left = self._image_client.get_image_from_sources(
                    ["left_fisheye_image"])[0].shot.image.data
                image = base64.b64encode(left).decode("utf8")

            output_to_socket(-1, image,
                                all=True, type=("@" + camera_name))
        except AttributeError:
            pass
