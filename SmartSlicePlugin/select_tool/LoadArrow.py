import math

from typing import Optional
from enum import Enum

from UM.Math.Color import Color
from UM.Math.Vector import Vector
from UM.Math.Quaternion import Quaternion
from UM.Mesh.MeshBuilder import MeshBuilder
from UM.Scene.ToolHandle import ToolHandle
from UM.Scene.SceneNode import SceneNode

from ..utils import angleBetweenVectors


class LoadArrow(ToolHandle):
    """Provides the arrow for the load direction"""

    color = Color(0.4, 0.4, 1., 1.)

    ARROW_HEAD_LENGTH = 8
    ARROW_TAIL_LENGTH = 22
    ARROW_TOTAL_LENGTH = ARROW_HEAD_LENGTH + ARROW_TAIL_LENGTH
    ARROW_HEAD_WIDTH = 2.8
    ARROW_TAIL_WIDTH = 0.8

    def __init__(self, parent = None, start: Vector = Vector(0, 0, 0), direction: Vector = Vector.Unit_X):
        super().__init__(parent)

        self._name = "LoadArrow"
        self._auto_scale = False

        self.start = start
        self.direction = direction

    def buildMesh(self):
        if self.direction is None:
            return

        mb = MeshBuilder()

        self.direction = self.direction.normalized()

        p_base0 = Vector(
            self.start.x + self.direction.x * self.ARROW_HEAD_LENGTH,
            self.start.y + self.direction.y * self.ARROW_HEAD_LENGTH,
            self.start.z + self.direction.z * self.ARROW_HEAD_LENGTH
        )
        p_tail0 = Vector(
            self.start.x + self.direction.x * self.ARROW_TOTAL_LENGTH,
            self.start.y + self.direction.y * self.ARROW_TOTAL_LENGTH,
            self.start.z + self.direction.z * self.ARROW_TOTAL_LENGTH
        )

        p_base0 = Vector(
            self.start.x + self.direction.x * self.ARROW_TAIL_LENGTH,
            self.start.y + self.direction.y * self.ARROW_TAIL_LENGTH,
            self.start.z + self.direction.z * self.ARROW_TAIL_LENGTH
        )
        p_head = p_tail0
        p_tail0 = self.start

        p_base1 = Vector(p_base0.x, p_base0.y + self.ARROW_HEAD_WIDTH, p_base0.z)
        p_base2 = Vector(p_base0.x, p_base0.y - self.ARROW_HEAD_WIDTH, p_base0.z)
        p_base3 = Vector(p_base0.x + self.ARROW_HEAD_WIDTH, p_base0.y, p_base0.z)
        p_base4 = Vector(p_base0.x - self.ARROW_HEAD_WIDTH, p_base0.y, p_base0.z)
        p_base5 = Vector(p_base0.x, p_base0.y, p_base0.z + self.ARROW_HEAD_WIDTH)
        p_base6 = Vector(p_base0.x, p_base0.y, p_base0.z - self.ARROW_HEAD_WIDTH)

        mb.addFace(p_base1, p_head, p_base3, color=self.color)
        mb.addFace(p_base3, p_head, p_base2, color=self.color)
        mb.addFace(p_base2, p_head, p_base4, color=self.color)
        mb.addFace(p_base4, p_head, p_base1, color=self.color)
        mb.addFace(p_base5, p_head, p_base1, color=self.color)
        mb.addFace(p_base6, p_head, p_base1, color=self.color)
        mb.addFace(p_base6, p_head, p_base2, color=self.color)
        mb.addFace(p_base2, p_head, p_base5, color=self.color)
        mb.addFace(p_base3, p_head, p_base5, color=self.color)
        mb.addFace(p_base5, p_head, p_base4, color=self.color)
        mb.addFace(p_base4, p_head, p_base6, color=self.color)
        mb.addFace(p_base6, p_head, p_base3, color=self.color)

        p_tail1 = Vector(p_tail0.x, p_tail0.y + self.ARROW_TAIL_WIDTH, p_tail0.z)
        p_tail2 = Vector(p_tail0.x, p_tail0.y - self.ARROW_TAIL_WIDTH, p_tail0.z)
        p_tail3 = Vector(p_tail0.x + self.ARROW_TAIL_WIDTH, p_tail0.y, p_tail0.z)
        p_tail4 = Vector(p_tail0.x - self.ARROW_TAIL_WIDTH, p_tail0.y, p_tail0.z)
        p_tail5 = Vector(p_tail0.x, p_tail0.y, p_tail0.z + self.ARROW_TAIL_WIDTH)
        p_tail6 = Vector(p_tail0.x, p_tail0.y, p_tail0.z - self.ARROW_TAIL_WIDTH)

        p_tail_base1 = Vector(p_base0.x, p_base0.y + self.ARROW_TAIL_WIDTH, p_base0.z)
        p_tail_base2 = Vector(p_base0.x, p_base0.y - self.ARROW_TAIL_WIDTH, p_base0.z)
        p_tail_base3 = Vector(p_base0.x + self.ARROW_TAIL_WIDTH, p_base0.y, p_base0.z)
        p_tail_base4 = Vector(p_base0.x - self.ARROW_TAIL_WIDTH, p_base0.y, p_base0.z)
        p_tail_base5 = Vector(p_base0.x, p_base0.y, p_base0.z + self.ARROW_TAIL_WIDTH)
        p_tail_base6 = Vector(p_base0.x, p_base0.y, p_base0.z - self.ARROW_TAIL_WIDTH)

        mb.addFace(p_tail1, p_tail_base1, p_tail3, color=self.color)
        mb.addFace(p_tail3, p_tail_base3, p_tail2, color=self.color)
        mb.addFace(p_tail2, p_tail_base2, p_tail4, color=self.color)
        mb.addFace(p_tail4, p_tail_base4, p_tail1, color=self.color)
        mb.addFace(p_tail5, p_tail_base5, p_tail1, color=self.color)
        mb.addFace(p_tail6, p_tail_base6, p_tail1, color=self.color)
        mb.addFace(p_tail6, p_tail_base6, p_tail2, color=self.color)
        mb.addFace(p_tail2, p_tail_base2, p_tail5, color=self.color)
        mb.addFace(p_tail3, p_tail_base3, p_tail5, color=self.color)
        mb.addFace(p_tail5, p_tail_base5, p_tail4, color=self.color)
        mb.addFace(p_tail4, p_tail_base4, p_tail6, color=self.color)
        mb.addFace(p_tail6, p_tail_base6, p_tail3, color=self.color)

        mb.addFace(p_tail_base1, p_tail_base3, p_tail3, color=self.color)
        mb.addFace(p_tail_base3, p_tail_base2, p_tail2, color=self.color)
        mb.addFace(p_tail_base2, p_tail_base4, p_tail4, color=self.color)
        mb.addFace(p_tail_base4, p_tail_base1, p_tail1, color=self.color)
        mb.addFace(p_tail_base5, p_tail_base1, p_tail1, color=self.color)
        mb.addFace(p_tail_base6, p_tail_base1, p_tail1, color=self.color)
        mb.addFace(p_tail_base6, p_tail_base2, p_tail2, color=self.color)
        mb.addFace(p_tail_base2, p_tail_base5, p_tail5, color=self.color)
        mb.addFace(p_tail_base3, p_tail_base5, p_tail5, color=self.color)
        mb.addFace(p_tail_base5, p_tail_base4, p_tail4, color=self.color)
        mb.addFace(p_tail_base4, p_tail_base6, p_tail6, color=self.color)
        mb.addFace(p_tail_base6, p_tail_base3, p_tail3, color=self.color)

        self.setSolidMesh(mb.build())

    def _onSelectionCenterChanged(self) -> None:
        pass

    def flip(self, normalAxis: Vector):

        self.rotateByAngle(math.pi)

        self.start = self.start + self.ARROW_TOTAL_LENGTH * self.direction
        self.direction = -1 * self.direction

        self.setPosition(self.start)

    def rotateByVector(self, direction: Vector):
        if direction is None:
            return

        if self.direction is None:
            self.direction = direction
            return

        self.rotatebyAngle(
            angleBetweenVectors(direction, self.direction)
        )
        self.direction = direction

    def rotateByAngle(self, angle: float):
        self.rotate(
            Quaternion.fromAngleAxis(angle, self._rotation_axis)
        )
