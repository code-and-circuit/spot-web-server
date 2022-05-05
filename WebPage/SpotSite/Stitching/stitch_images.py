# Copyright (c) 2021 Boston Dynamics, Inc.  All rights reserved.
#
# Downloading, reproducing, distributing or otherwise using the SDK Software
# is subject to the terms and conditions of the Boston Dynamics Software
# Development Kit License (20191101-BDSDK-SL).

"""Stitch frontleft_fisheye_image, frontright_fisheye_image from images.protodata."""

import OpenGL
import bosdyn.api
import bosdyn.client.util
import io
import os
import numpy
import sys
import time

from OpenGL.GL import *
from OpenGL.GL import shaders, GL_VERTEX_SHADER
from OpenGL.GLU import *
from OpenGL.GLUT import *
from pil import Image
from pil import ImageOps
from bosdyn.api import image_pb2
from bosdyn.client.frame_helpers import BODY_FRAME_NAME, get_vision_tform_body, get_a_tform_b
from ctypes import *


class ImagePreppedForOpenGL():
    """Prep image for OpenGL from Spot image_response."""

    def extract_image(self, image_response):
        """Return numpy_array of input image_response image."""
        image_format = image_response.shot.image.format

        if image_format == image_pb2.Image.FORMAT_RAW:
            raise Exception("Won't work.  Yet.")
        elif image_format == image_pb2.Image.FORMAT_JPEG:
            numpy_array = numpy.asarray(Image.open(
                io.BytesIO(image_response.shot.image.data)))
        else:
            raise Exception("Won't work.")

        return numpy_array

    def __init__(self, image_response):
        self.image = self.extract_image(image_response)
        self.body_T_image_sensor = get_a_tform_b(image_response.shot.transforms_snapshot,
                                                 BODY_FRAME_NAME, image_response.shot.frame_name_image_sensor)
        self.vision_T_body = get_vision_tform_body(
            image_response.shot.transforms_snapshot)
        if not self.body_T_image_sensor:
            raise Exception("Won't work.")

        if image_response.source.pinhole:
            resolution = numpy.asarray([
                image_response.source.cols,
                image_response.source.rows])

            focal_length = numpy.asarray([
                image_response.source.pinhole.intrinsics.focal_length.x,
                image_response.source.pinhole.intrinsics.focal_length.y])

            principal_point = numpy.asarray([
                image_response.source.pinhole.intrinsics.principal_point.x,
                image_response.source.pinhole.intrinsics.principal_point.y])
        else:
            raise Exception("Won't work.")

        sensor_T_vo = (self.vision_T_body * self.body_T_image_sensor).inverse()

        camera_projection_mat = numpy.eye(4)
        camera_projection_mat[0, 0] = (focal_length[0] / resolution[0])
        camera_projection_mat[0, 2] = (principal_point[0] / resolution[0])
        camera_projection_mat[1, 1] = (focal_length[1] / resolution[1])
        camera_projection_mat[1, 2] = (principal_point[1] / resolution[1])

        self.MVP = camera_projection_mat.dot(sensor_T_vo.to_matrix())


class ImageInsideOpenGL():
    """Create OpenGL Texture"""

    def __init__(self, numpy_array):
        glEnable(GL_TEXTURE_2D)
        self.pointer = glGenTextures(1)
        glActiveTexture(GL_TEXTURE0 + self.pointer)
        glBindTexture(GL_TEXTURE_2D, self.pointer)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, numpy_array.shape[1], numpy_array.shape[0], 0,
                     GL_LUMINANCE, GL_UNSIGNED_BYTE, numpy_array)
        glTexParameter(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameter(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

    def update(self, numpy_array):
        """Update texture (no-op)"""
        glActiveTexture(GL_TEXTURE0 + self.pointer)
        glBindTexture(GL_TEXTURE_2D, self.pointer)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, numpy_array.shape[1], numpy_array.shape[0], 0,
                     GL_LUMINANCE, GL_UNSIGNED_BYTE, numpy_array)


class CompiledShader():
    """OpenGL shader compile"""

    def __init__(self, vert_shader, frag_shader):
        self.program = shaders.compileProgram(
            shaders.compileShader(vert_shader, GL_VERTEX_SHADER),
            shaders.compileShader(frag_shader, GL_FRAGMENT_SHADER)
        )
        self.camera1_MVP = glGetUniformLocation(self.program, 'camera1_MVP')
        self.camera2_MVP = glGetUniformLocation(self.program, 'camera2_MVP')

        self.image1_texture = glGetUniformLocation(self.program, 'image1')
        self.image2_texture = glGetUniformLocation(self.program, 'image2')

        self.image1 = None
        self.image2 = None

    def use(self):
        """Call glUseProgram."""
        glUseProgram(self.program)

    def set_matrix(self, matrix, is_camera1):
        """Call glUniformMatrix4fv"""
        if is_camera1:
            glUniformMatrix4fv(self.camera1_MVP, 1, GL_TRUE, matrix)
        else:
            glUniformMatrix4fv(self.camera2_MVP, 1, GL_TRUE, matrix)

    def set_camera1_mvp(self, matrix):
        """Set left camera matrix"""
        self.set_matrix(matrix, True)

    def set_camera2_mvp(self, matrix):
        """Set right camera matrix"""
        self.set_matrix(matrix, False)

    def set_texture(self, data_pointer, shader_pointer, texture):
        """Apply texture."""
        glActiveTexture(GL_TEXTURE0 + texture)
        glBindTexture(GL_TEXTURE_2D, data_pointer)
        glUniform1i(shader_pointer, texture)

    def set_image1_texture(self, image):
        """Set first texture."""
        if self.image1 is None:
            self.image1 = ImageInsideOpenGL(image)
        else:
            self.image1.update(image)

        self.set_texture(self.image1.pointer, self.image1_texture, 0)

    def set_image2_texture(self, image):
        """Set second texture."""
        if self.image2 is None:
            self.image2 = ImageInsideOpenGL(image)
        else:
            self.image2.update(image)

        self.set_texture(self.image2.pointer, self.image2_texture, 1)


def proto_vec_T_numpy(vec):
    return numpy.array([vec.x, vec.y, vec.z])


def mat4mul3(mat, vec, vec4=1):
    ret = numpy.matmul(mat, numpy.append(vec, vec4))
    return ret[:-1]


def normalize(vec):
    norm = numpy.linalg.norm(vec)
    if norm == 0:
        raise ValueError("norm function returned 0.")
    return vec / norm


def draw_geometry(plane_wrt_vo, plane_norm_wrt_vo, sz_meters):
    """Draw as GL_TRIANGLES."""
    plane_left_wrt_vo = normalize(numpy.cross(
        numpy.array([0, 0, 1]), plane_norm_wrt_vo))
    if plane_left_wrt_vo is None:
        return
    plane_up_wrt_vo = normalize(numpy.cross(
        plane_norm_wrt_vo, plane_left_wrt_vo))
    if plane_up_wrt_vo is None:
        return

    plane_up_wrt_vo = plane_up_wrt_vo * sz_meters
    plane_left_wrt_vo = plane_left_wrt_vo * sz_meters

    vertices = (
        plane_wrt_vo + plane_left_wrt_vo - plane_up_wrt_vo,
        plane_wrt_vo + plane_left_wrt_vo + plane_up_wrt_vo,
        plane_wrt_vo - plane_left_wrt_vo + plane_up_wrt_vo,
        plane_wrt_vo - plane_left_wrt_vo - plane_up_wrt_vo,
    )

    indices = (0, 1, 2, 0, 2, 3)

    glBegin(GL_TRIANGLES)
    for index in indices:
        glVertex3fv(vertices[index])
    glEnd()


def draw_routine(display, image_1, image_2, program):
    """OpenGL Draw"""
    rect_sz_meters = 7
    rect_stitching_distance_meters = 2.0

    vo_T_body = image_1.vision_T_body.to_matrix()

    eye_wrt_body = proto_vec_T_numpy(image_1.body_T_image_sensor.position) \
        + proto_vec_T_numpy(image_2.body_T_image_sensor.position)

    # Add the two real camera norms together to get the fake camera norm.
    eye_norm_wrt_body = numpy.array(image_1.body_T_image_sensor.rot.transform_point(0, 0, 1)) \
        + numpy.array(image_2.body_T_image_sensor.rot.transform_point(0, 0, 1))

    # Make the virtual camera centered.
    eye_wrt_body[1] = 0
    eye_norm_wrt_body[1] = 0

    # Make sure our normal has length 1
    eye_norm_wrt_body = normalize(eye_norm_wrt_body)

    plane_wrt_body = eye_wrt_body + eye_norm_wrt_body * rect_stitching_distance_meters

    plane_wrt_vo = mat4mul3(vo_T_body, plane_wrt_body)
    plane_norm_wrt_vo = mat4mul3(vo_T_body, eye_norm_wrt_body, 0)

    eye_wrt_vo = mat4mul3(vo_T_body, eye_wrt_body)
    up_wrt_vo = mat4mul3(vo_T_body, numpy.array([0, 0, 1]), 0)

    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(110, (display[0] / display[1]), 0.1, 50.0)

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    gluLookAt(eye_wrt_vo[0], eye_wrt_vo[1], eye_wrt_vo[2],
              plane_wrt_vo[0], plane_wrt_vo[1], plane_wrt_vo[2],
              up_wrt_vo[0], up_wrt_vo[1], up_wrt_vo[2])

    program.use()
    program.set_camera1_mvp(image_1.MVP)
    program.set_camera2_mvp(image_2.MVP)
    program.set_image1_texture(image_1.image)
    program.set_image2_texture(image_2.image)

    draw_geometry(plane_wrt_vo, plane_norm_wrt_vo, rect_sz_meters)


class Stitcher:
    def __init__(self):
        self._width = 1080
        self._height = 720
        self._display = (self._width, self._height)

        self._program = None
        self._image_1 = None
        self._image_2 = None
        self._images_should_exist = True

        self._stitched_image = None
        self.frame_num = 0
        self._is_running = False

    def start_glut_loop(self):
        self._init_glut()
        self._load_shaders()
        self._start_glut()

    def _init_glut(self):
        glutInit()
        glutInitDisplayMode(GLUT_RGBA)
        glutInitWindowSize(self._width, self._height)
        glutInitWindowPosition(0, 0)
        window = glutCreateWindow("Image Stitching")
        #glutHideWindow()

    def _load_shaders(self):
        with open('SpotSite\\Stitching\\shader_vert.glsl', 'r') as file:
            vert_shader = file.read()
        with open('SpotSite\\Stitching\\shader_frag.glsl', 'r') as file:
            frag_shader = file.read()

        self._program = CompiledShader(vert_shader, frag_shader)

    def _start_glut(self):
        glutDisplayFunc(self._update_image)
        glutIdleFunc(glutPostRedisplay)
        glutMainLoop()

    def _draw_string(self, string, x, y, color):
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glColor3f(color[0], color[1], color[2])
        glRasterPos2f(x / self._width, y / self._height)
        for char in string:
            glutBitmapCharacter(GLUT_BITMAP_TIMES_ROMAN_24, ord(char))

    def _save_image(self):
        glPixelStorei(GL_PACK_ALIGNMENT, 1)
        data = glReadPixels(0, 0, self._width, self._height,
                            GL_RGB, GL_UNSIGNED_BYTE)
        image = Image.frombytes("RGB", self._display, data)
        self._stitched_image = ImageOps.flip(image)

    def _do_stitching(self):
        if not self._images_should_exist:
            return

        if self._image_1 is None or self._image_2 is None:
            return

        image_1 = ImagePreppedForOpenGL(self._image_1)
        image_2 = ImagePreppedForOpenGL(self._image_2)
        draw_routine(self._display, image_1, image_2, self._program)

    def _update_image(self):
        self._is_running = True
        glutSwapBuffers()
        glClearColor(1, 1, 1, 0)
        glClear(GL_COLOR_BUFFER_BIT)

        self._do_stitching()
        self._save_image()

    def stitch(self, image_1, image_2):
        if not self._is_running:
            return  
        self._images_should_exist = False

        self._image_1 = image_1
        self._image_2 = image_2

        self._images_should_exist = True
        return self._stitched_image
