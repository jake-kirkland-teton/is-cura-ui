import math

from typing import Optional

from UM.Math.Color import Color
from UM.Math.Vector import Vector
from UM.Math.Quaternion import Quaternion
from UM.Mesh.MeshBuilder import MeshBuilder
from UM.Scene.ToolHandle import ToolHandle
from UM.Scene.SceneNode import SceneNode

class LoadRotator(ToolHandle):
    """Provides the circular toolhandle and arrow for the load direction"""

    color = Color(0.4, 0.4, 1., 1.)

    INNER_RADIUS = 60
    LINE_WIDTH = 1.0
    OUTER_RADIUS = INNER_RADIUS + LINE_WIDTH
    ACTIVE_INNER_RADIUS = INNER_RADIUS - 3
    ACTIVE_OUTER_RADIUS = OUTER_RADIUS + 3
    ACTIVE_LINE_WIDTH = LINE_WIDTH + 3

    def __init__(self, parent = None):
        super().__init__(parent)

        self._name = "LoadRotator"
        self._auto_scale = False

        self.center = Vector(0, 0, 0)
        self.rotation_axis = Vector.Unit_Z

    def buildMesh(self):
        mb = MeshBuilder()

        #SOLIDMESH
        mb.addDonut(
            inner_radius = self.INNER_RADIUS,
            outer_radius = self.OUTER_RADIUS,
            width = self.LINE_WIDTH,
            axis = self.rotation_axis,
            color = self.color
        )

        self.setSolidMesh(mb.build())

        #SELECTIONMESH
        mb.addDonut(
            inner_radius = self.ACTIVE_INNER_RADIUS,
            outer_radius = self.ACTIVE_OUTER_RADIUS,
            width = self.ACTIVE_LINE_WIDTH,
            axis = self.rotation_axis,
            color = ToolHandle.AllAxisSelectionColor
        )

        self.setSelectionMesh(mb.build())

    def _onSelectionCenterChanged(self) -> None:
        pass
