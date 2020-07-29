import math

from UM.Math.Vector import Vector
from UM.Mesh.MeshBuilder import MeshBuilder
from UM.Scene.ToolHandle import ToolHandle

from ..stage.SmartSliceScene import LoadFace


class RotateLoadHandle(ToolHandle):
    """Provides the circular toolhandles for each axis for the rotate tool"""

    INNER_RADIUS = 2.0 * LoadFace.ARROW_TOTAL_LENGTH
    LINE_WIDTH = 1.0
    OUTER_RADIUS = INNER_RADIUS + LINE_WIDTH
    ACTIVE_INNER_RADIUS = INNER_RADIUS - 3
    ACTIVE_OUTER_RADIUS = OUTER_RADIUS + 3
    ACTIVE_LINE_WIDTH = LINE_WIDTH + 3

    def __init__(self, parent = None):
        super().__init__(parent)

        self._name = "RotateLoadHandle"

        self._auto_scale = False

    def buildMesh(self):
        #SOLIDMESH
        mb = MeshBuilder()

        mb.addDonut(
            inner_radius = self.INNER_RADIUS,
            outer_radius = self.OUTER_RADIUS,
            width = self.LINE_WIDTH,
            color = self._z_axis_color
        )

        mb.addDonut(
            inner_radius = self.INNER_RADIUS,
            outer_radius = self.OUTER_RADIUS,
            width = self.LINE_WIDTH,
            axis = Vector.Unit_X,
            angle = math.pi / 2,
            color = self._y_axis_color
        )

        mb.addDonut(
            inner_radius = self.INNER_RADIUS,
            outer_radius = self.OUTER_RADIUS,
            width = self.LINE_WIDTH,
            axis = Vector.Unit_Y,
            angle = math.pi / 2,
            color = self._x_axis_color
        )
        self.setSolidMesh(mb.build())

        #SELECTIONMESH
        mb = MeshBuilder()

        mb.addDonut(
            inner_radius = self.ACTIVE_INNER_RADIUS,
            outer_radius = self.ACTIVE_OUTER_RADIUS,
            width = self.ACTIVE_LINE_WIDTH,
            color = ToolHandle.ZAxisSelectionColor
        )

        mb.addDonut(
            inner_radius = self.ACTIVE_INNER_RADIUS,
            outer_radius = self.ACTIVE_OUTER_RADIUS,
            width = self.ACTIVE_LINE_WIDTH,
            axis = Vector.Unit_X,
            angle = math.pi / 2,
            color = ToolHandle.YAxisSelectionColor
        )

        mb.addDonut(
            inner_radius = self.ACTIVE_INNER_RADIUS,
            outer_radius = self.ACTIVE_OUTER_RADIUS,
            width = self.ACTIVE_LINE_WIDTH,
            axis = Vector.Unit_Y,
            angle = math.pi / 2,
            color = ToolHandle.XAxisSelectionColor
        )

        self.setSelectionMesh(mb.build())
