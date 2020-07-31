import math

from typing import Optional

from UM.Math.Color import Color
from UM.Math.Vector import Vector
from UM.Math.Quaternion import Quaternion
from UM.Mesh.MeshBuilder import MeshBuilder
from UM.Scene.ToolHandle import ToolHandle
from UM.Scene.SceneNode import SceneNode


class LoadHandle(ToolHandle):
    """Provides the circular toolhandle and arrow for the load direction"""

    color = Color(0.4, 0.4, 1., 1.)

    ARROW_HEAD_LENGTH = 8
    ARROW_TAIL_LENGTH = 22
    ARROW_TOTAL_LENGTH = ARROW_HEAD_LENGTH + ARROW_TAIL_LENGTH
    ARROW_HEAD_WIDTH = 2.8
    ARROW_TAIL_WIDTH = 0.8

    INNER_RADIUS = 2.0 * ARROW_TOTAL_LENGTH
    LINE_WIDTH = 1.0
    OUTER_RADIUS = INNER_RADIUS + LINE_WIDTH
    ACTIVE_INNER_RADIUS = INNER_RADIUS - 3
    ACTIVE_OUTER_RADIUS = OUTER_RADIUS + 3
    ACTIVE_LINE_WIDTH = LINE_WIDTH + 3

    def __init__(self, parent = None):
        super().__init__(parent)

        self._name = "RotateLoadHandle"
        self._auto_scale = False

        self._center = None
        self._rotation_axis = Vector.Unit_Z
        self._arrow_direction = None

    def buildMesh(self):
        mb = MeshBuilder()

        #SOLIDMESH
        mb.addDonut(
            inner_radius = self.INNER_RADIUS,
            outer_radius = self.OUTER_RADIUS,
            width = self.LINE_WIDTH,
            axis = self._rotation_axis,
            color = self.color
        )

        self.setSolidMesh(mb.build())

        #SELECTIONMESH
        mb.addDonut(
            inner_radius = self.ACTIVE_INNER_RADIUS,
            outer_radius = self.ACTIVE_OUTER_RADIUS,
            width = self.ACTIVE_LINE_WIDTH,
            axis = self._rotation_axis,
            color = ToolHandle.AllAxisSelectionColor
        )

        self.setSelectionMesh(mb.build())

    def _onSelectionCenterChanged(self) -> None:
        pass

    def setCenterAndRotationAxis(self, center: Vector, rotation_axis: Vector, arrow_direction: Vector = None):
        """Sets the center and the plane of the rotation handle, then rotates the load arrow to the desired direction"""
        axis = self._rotation_axis.cross(rotation_axis)
        angle = self._rotation_axis.angleToVector(rotation_axis)

        if axis.length() < 1.e-3:
            axis = rotation_axis

        matrix = Quaternion()
        matrix.setByAngleAxis(angle, axis)
        self.rotate(matrix, SceneNode.TransformSpace.World)

        self._rotation_axis = rotation_axis

        self.rotateLoad(arrow_direction)

        self._center = center
        # if self._parent:
        #     self._center += self._parent.getWorldPosition()
        self.setPosition(center)

    def rotateLoad(self, arrow_direction: Vector):
        if arrow_direction is None:
            return

        if self._arrow_direction is None:
            self._arrow_direction = arrow_direction
            return

        self.rotateLoadByAngle(
            arrow_direction.angleToVector(self._arrow_direction)
        )
        self._arrow_direction = arrow_direction

    def rotateLoadByAngle(self, angle: float):
        matrix = Quaternion()
        matrix.setByAngleAxis(angle, self._rotation_axis)
        self.rotate(matrix)

