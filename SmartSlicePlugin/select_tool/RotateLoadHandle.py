import math

from UM.Math.Color import Color
from UM.Math.Vector import Vector
from UM.Mesh.MeshBuilder import MeshBuilder
from UM.Scene.ToolHandle import ToolHandle
from UM.Scene.SceneNode import SceneNode


class RotateLoadHandle(ToolHandle):
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

    def __init__(self, parent = None, center: Vector = Vector(0, 0, 0), center_axis: Vector = Vector.Unit_X):
        super().__init__(parent)

        self._name = "RotateLoadHandle"

        self._center = center
        if parent is not None:
            self._center = center + parent.getWorldPosition()
        self._axis = center_axis.normalized()
        self._auto_scale = False

    def buildMesh(self):
        mb = MeshBuilder()

        rotation_axis = self._axis.cross(Vector.Unit_Z)
        if rotation_axis.length() < 1.e-3:
            rotation_axis = Vector.Unit_Z

        angle = self._axis.angleToVector(Vector.Unit_Z)

        #SOLIDMESH
        mb.addDonut(
            inner_radius = self.INNER_RADIUS,
            outer_radius = self.OUTER_RADIUS,
            width = self.LINE_WIDTH,
            center = self._center,
            axis = rotation_axis,
            angle = angle,
            color = self.color
        )

        self.setSolidMesh(mb.build())

        #SELECTIONMESH
        mb.addDonut(
            inner_radius = self.ACTIVE_INNER_RADIUS,
            outer_radius = self.ACTIVE_OUTER_RADIUS,
            width = self.ACTIVE_LINE_WIDTH,
            center = self._center,
            axis = rotation_axis,
            angle = angle,
            color = ToolHandle.AllAxisSelectionColor
        )

        self.setSelectionMesh(mb.build())

    def _onSelectionCenterChanged(self) -> None:
        pass
