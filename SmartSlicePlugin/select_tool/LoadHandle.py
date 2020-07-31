import math

from typing import Optional

from UM.Math.Color import Color
from UM.Math.Vector import Vector
from UM.Math.Quaternion import Quaternion
from UM.Mesh.MeshBuilder import MeshBuilder
from UM.Scene.ToolHandle import ToolHandle
from UM.Scene.SceneNode import SceneNode

from .LoadArrow import LoadArrow
from ..utils import angleBetweenVectors


class LoadHandle(ToolHandle):
    """Provides the circular toolhandle and arrow for the load direction"""

    color = Color(0.4, 0.4, 1., 1.)

    INNER_RADIUS = 2.0 * LoadArrow.ARROW_TOTAL_LENGTH
    LINE_WIDTH = 1.0
    OUTER_RADIUS = INNER_RADIUS + LINE_WIDTH
    ACTIVE_INNER_RADIUS = INNER_RADIUS - 3
    ACTIVE_OUTER_RADIUS = OUTER_RADIUS + 3
    ACTIVE_LINE_WIDTH = LINE_WIDTH + 3

    def __init__(self, parent = None):
        super().__init__(parent)

        self._name = "LoadHandle"
        self._auto_scale = False

        self._center = Vector(0, 0, 0)
        self._rotation_axis = Vector.Unit_Z
        self._arrow_direction = Vector.Unit_X

        self.show_rotation = True

        self._arrow = LoadArrow(self, self._center, self._arrow_direction)

    def buildMesh(self):
        mb = MeshBuilder()

        if self.show_rotation:

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

        self._arrow.buildMesh()

    def _onSelectionCenterChanged(self) -> None:
        pass

    def setCenterAndRotationAxis(self, center: Vector, rotation_axis: Vector, arrow_direction: Vector = None):
        """Sets the center and the plane of the rotation handle, then rotates the load arrow to the desired direction"""
        axis = self._rotation_axis.cross(rotation_axis)
        angle = angleBetweenVectors(rotation_axis, self._rotation_axis)

        if axis.length() < 1.e-3:
            axis = rotation_axis

        matrix = Quaternion.fromAngleAxis(angle, axis)
        self.rotate(matrix, SceneNode.TransformSpace.World)

        self._rotation_axis = rotation_axis

        translation = center - self._center
        self._center = center
        self.setPosition(center)

        self._arrow.start += translation
        self._arrow.direction = matrix.rotate(self._arrow.direction)

        self._arrow.rotateByVector(arrow_direction)

    def setEnabled(self, enabled: bool):
        super().setEnabled(enabled)
        for child in self._children:
            child.setEnabled(enabled)

    def setVisible(self, visible: bool):
        super().setVisible(visible)
        for child in self._children:
            child.setVisible(visible)
