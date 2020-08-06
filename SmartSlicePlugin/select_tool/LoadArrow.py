from UM.Math.Vector import Vector
from UM.Math.Quaternion import Quaternion
from UM.Mesh.MeshBuilder import MeshBuilder
from UM.Scene.ToolHandle import ToolHandle
from UM.Scene.SceneNode import SceneNode

from ..utils import angleBetweenVectors
from .LoadToolHandle import LoadToolHandle

class LoadArrow(LoadToolHandle):
    """Provides the arrow for the load direction"""

    def __init__(self, parent = None):
        super().__init__(parent)

        self._name = "LoadArrow"

        self.direction = -1 * Vector.Unit_X

    def buildMesh(self):
        super().buildMesh()

        mb = MeshBuilder()
        color = self._y_axis_color

        start = LoadToolHandle.ARROW_TOTAL_LENGTH * Vector.Unit_X

        p_head = Vector(
            start.x + self.direction.x * LoadToolHandle.ARROW_TOTAL_LENGTH,
            start.y + self.direction.y * LoadToolHandle.ARROW_TOTAL_LENGTH,
            start.z + self.direction.z * LoadToolHandle.ARROW_TOTAL_LENGTH
        )

        p_base0 = Vector(
            start.x + self.direction.x * LoadToolHandle.ARROW_TAIL_LENGTH,
            start.y + self.direction.y * LoadToolHandle.ARROW_TAIL_LENGTH,
            start.z + self.direction.z * LoadToolHandle.ARROW_TAIL_LENGTH
        )

        p_tail0 = start

        p_base1 = Vector(p_base0.x, p_base0.y + LoadToolHandle.ARROW_HEAD_WIDTH, p_base0.z)
        p_base2 = Vector(p_base0.x, p_base0.y - LoadToolHandle.ARROW_HEAD_WIDTH, p_base0.z)
        p_base3 = Vector(p_base0.x + LoadToolHandle.ARROW_HEAD_WIDTH, p_base0.y, p_base0.z)
        p_base4 = Vector(p_base0.x - LoadToolHandle.ARROW_HEAD_WIDTH, p_base0.y, p_base0.z)
        p_base5 = Vector(p_base0.x, p_base0.y, p_base0.z + LoadToolHandle.ARROW_HEAD_WIDTH)
        p_base6 = Vector(p_base0.x, p_base0.y, p_base0.z - LoadToolHandle.ARROW_HEAD_WIDTH)

        mb.addFace(p_base1, p_head, p_base3, color=color)
        mb.addFace(p_base3, p_head, p_base2, color=color)
        mb.addFace(p_base2, p_head, p_base4, color=color)
        mb.addFace(p_base4, p_head, p_base1, color=color)
        mb.addFace(p_base5, p_head, p_base1, color=color)
        mb.addFace(p_base6, p_head, p_base1, color=color)
        mb.addFace(p_base6, p_head, p_base2, color=color)
        mb.addFace(p_base2, p_head, p_base5, color=color)
        mb.addFace(p_base3, p_head, p_base5, color=color)
        mb.addFace(p_base5, p_head, p_base4, color=color)
        mb.addFace(p_base4, p_head, p_base6, color=color)
        mb.addFace(p_base6, p_head, p_base3, color=color)

        p_tail1 = Vector(p_tail0.x, p_tail0.y + LoadToolHandle.ARROW_TAIL_WIDTH, p_tail0.z)
        p_tail2 = Vector(p_tail0.x, p_tail0.y - LoadToolHandle.ARROW_TAIL_WIDTH, p_tail0.z)
        p_tail3 = Vector(p_tail0.x + LoadToolHandle.ARROW_TAIL_WIDTH, p_tail0.y, p_tail0.z)
        p_tail4 = Vector(p_tail0.x - LoadToolHandle.ARROW_TAIL_WIDTH, p_tail0.y, p_tail0.z)
        p_tail5 = Vector(p_tail0.x, p_tail0.y, p_tail0.z + LoadToolHandle.ARROW_TAIL_WIDTH)
        p_tail6 = Vector(p_tail0.x, p_tail0.y, p_tail0.z - LoadToolHandle.ARROW_TAIL_WIDTH)

        p_tail_base1 = Vector(p_base0.x, p_base0.y + LoadToolHandle.ARROW_TAIL_WIDTH, p_base0.z)
        p_tail_base2 = Vector(p_base0.x, p_base0.y - LoadToolHandle.ARROW_TAIL_WIDTH, p_base0.z)
        p_tail_base3 = Vector(p_base0.x + LoadToolHandle.ARROW_TAIL_WIDTH, p_base0.y, p_base0.z)
        p_tail_base4 = Vector(p_base0.x - LoadToolHandle.ARROW_TAIL_WIDTH, p_base0.y, p_base0.z)
        p_tail_base5 = Vector(p_base0.x, p_base0.y, p_base0.z + LoadToolHandle.ARROW_TAIL_WIDTH)
        p_tail_base6 = Vector(p_base0.x, p_base0.y, p_base0.z - LoadToolHandle.ARROW_TAIL_WIDTH)

        mb.addFace(p_tail1, p_tail_base1, p_tail3, color=color)
        mb.addFace(p_tail3, p_tail_base3, p_tail2, color=color)
        mb.addFace(p_tail2, p_tail_base2, p_tail4, color=color)
        mb.addFace(p_tail4, p_tail_base4, p_tail1, color=color)
        mb.addFace(p_tail5, p_tail_base5, p_tail1, color=color)
        mb.addFace(p_tail6, p_tail_base6, p_tail1, color=color)
        mb.addFace(p_tail6, p_tail_base6, p_tail2, color=color)
        mb.addFace(p_tail2, p_tail_base2, p_tail5, color=color)
        mb.addFace(p_tail3, p_tail_base3, p_tail5, color=color)
        mb.addFace(p_tail5, p_tail_base5, p_tail4, color=color)
        mb.addFace(p_tail4, p_tail_base4, p_tail6, color=color)
        mb.addFace(p_tail6, p_tail_base6, p_tail3, color=color)

        mb.addFace(p_tail_base1, p_tail_base3, p_tail3, color=color)
        mb.addFace(p_tail_base3, p_tail_base2, p_tail2, color=color)
        mb.addFace(p_tail_base2, p_tail_base4, p_tail4, color=color)
        mb.addFace(p_tail_base4, p_tail_base1, p_tail1, color=color)
        mb.addFace(p_tail_base5, p_tail_base1, p_tail1, color=color)
        mb.addFace(p_tail_base6, p_tail_base1, p_tail1, color=color)
        mb.addFace(p_tail_base6, p_tail_base2, p_tail2, color=color)
        mb.addFace(p_tail_base2, p_tail_base5, p_tail5, color=color)
        mb.addFace(p_tail_base3, p_tail_base5, p_tail5, color=color)
        mb.addFace(p_tail_base5, p_tail_base4, p_tail4, color=color)
        mb.addFace(p_tail_base4, p_tail_base6, p_tail6, color=color)
        mb.addFace(p_tail_base6, p_tail_base3, p_tail3, color=color)

        self.setSolidMesh(mb.build())

        # SELECTION MESH
        mb = MeshBuilder()

        color = ToolHandle.YAxisSelectionColor

        p_base0 = Vector(
            start.x + self.direction.x * LoadToolHandle.ACTIVE_ARROW_TAIL_LENGTH,
            start.y + self.direction.y * LoadToolHandle.ACTIVE_ARROW_TAIL_LENGTH,
            start.z + self.direction.z * LoadToolHandle.ACTIVE_ARROW_TAIL_LENGTH
        )

        p_tail0 = start

        p_base1 = Vector(p_base0.x, p_base0.y + LoadToolHandle.ACTIVE_ARROW_HEAD_WIDTH, p_base0.z)
        p_base2 = Vector(p_base0.x, p_base0.y - LoadToolHandle.ACTIVE_ARROW_HEAD_WIDTH, p_base0.z)
        p_base3 = Vector(p_base0.x + LoadToolHandle.ACTIVE_ARROW_HEAD_WIDTH, p_base0.y, p_base0.z)
        p_base4 = Vector(p_base0.x - LoadToolHandle.ACTIVE_ARROW_HEAD_WIDTH, p_base0.y, p_base0.z)
        p_base5 = Vector(p_base0.x, p_base0.y, p_base0.z + LoadToolHandle.ACTIVE_ARROW_HEAD_WIDTH)
        p_base6 = Vector(p_base0.x, p_base0.y, p_base0.z - LoadToolHandle.ACTIVE_ARROW_HEAD_WIDTH)

        mb.addFace(p_base1, p_head, p_base3, color=color)
        mb.addFace(p_base3, p_head, p_base2, color=color)
        mb.addFace(p_base2, p_head, p_base4, color=color)
        mb.addFace(p_base4, p_head, p_base1, color=color)
        mb.addFace(p_base5, p_head, p_base1, color=color)
        mb.addFace(p_base6, p_head, p_base1, color=color)
        mb.addFace(p_base6, p_head, p_base2, color=color)
        mb.addFace(p_base2, p_head, p_base5, color=color)
        mb.addFace(p_base3, p_head, p_base5, color=color)
        mb.addFace(p_base5, p_head, p_base4, color=color)
        mb.addFace(p_base4, p_head, p_base6, color=color)
        mb.addFace(p_base6, p_head, p_base3, color=color)

        p_tail1 = Vector(p_tail0.x, p_tail0.y + LoadToolHandle.ACTIVE_ARROW_TAIL_WIDTH, p_tail0.z)
        p_tail2 = Vector(p_tail0.x, p_tail0.y - LoadToolHandle.ACTIVE_ARROW_TAIL_WIDTH, p_tail0.z)
        p_tail3 = Vector(p_tail0.x + LoadToolHandle.ACTIVE_ARROW_TAIL_WIDTH, p_tail0.y, p_tail0.z)
        p_tail4 = Vector(p_tail0.x - LoadToolHandle.ACTIVE_ARROW_TAIL_WIDTH, p_tail0.y, p_tail0.z)
        p_tail5 = Vector(p_tail0.x, p_tail0.y, p_tail0.z + LoadToolHandle.ACTIVE_ARROW_TAIL_WIDTH)
        p_tail6 = Vector(p_tail0.x, p_tail0.y, p_tail0.z - LoadToolHandle.ACTIVE_ARROW_TAIL_WIDTH)

        p_tail_base1 = Vector(p_base0.x, p_base0.y + LoadToolHandle.ACTIVE_ARROW_TAIL_WIDTH, p_base0.z)
        p_tail_base2 = Vector(p_base0.x, p_base0.y - LoadToolHandle.ACTIVE_ARROW_TAIL_WIDTH, p_base0.z)
        p_tail_base3 = Vector(p_base0.x + LoadToolHandle.ACTIVE_ARROW_TAIL_WIDTH, p_base0.y, p_base0.z)
        p_tail_base4 = Vector(p_base0.x - LoadToolHandle.ACTIVE_ARROW_TAIL_WIDTH, p_base0.y, p_base0.z)
        p_tail_base5 = Vector(p_base0.x, p_base0.y, p_base0.z + LoadToolHandle.ACTIVE_ARROW_TAIL_WIDTH)
        p_tail_base6 = Vector(p_base0.x, p_base0.y, p_base0.z - LoadToolHandle.ACTIVE_ARROW_TAIL_WIDTH)

        mb.addFace(p_tail1, p_tail_base1, p_tail3, color=color)
        mb.addFace(p_tail3, p_tail_base3, p_tail2, color=color)
        mb.addFace(p_tail2, p_tail_base2, p_tail4, color=color)
        mb.addFace(p_tail4, p_tail_base4, p_tail1, color=color)
        mb.addFace(p_tail5, p_tail_base5, p_tail1, color=color)
        mb.addFace(p_tail6, p_tail_base6, p_tail1, color=color)
        mb.addFace(p_tail6, p_tail_base6, p_tail2, color=color)
        mb.addFace(p_tail2, p_tail_base2, p_tail5, color=color)
        mb.addFace(p_tail3, p_tail_base3, p_tail5, color=color)
        mb.addFace(p_tail5, p_tail_base5, p_tail4, color=color)
        mb.addFace(p_tail4, p_tail_base4, p_tail6, color=color)
        mb.addFace(p_tail6, p_tail_base6, p_tail3, color=color)

        mb.addFace(p_tail_base1, p_tail_base3, p_tail3, color=color)
        mb.addFace(p_tail_base3, p_tail_base2, p_tail2, color=color)
        mb.addFace(p_tail_base2, p_tail_base4, p_tail4, color=color)
        mb.addFace(p_tail_base4, p_tail_base1, p_tail1, color=color)
        mb.addFace(p_tail_base5, p_tail_base1, p_tail1, color=color)
        mb.addFace(p_tail_base6, p_tail_base1, p_tail1, color=color)
        mb.addFace(p_tail_base6, p_tail_base2, p_tail2, color=color)
        mb.addFace(p_tail_base2, p_tail_base5, p_tail5, color=color)
        mb.addFace(p_tail_base3, p_tail_base5, p_tail5, color=color)
        mb.addFace(p_tail_base5, p_tail_base4, p_tail4, color=color)
        mb.addFace(p_tail_base4, p_tail_base6, p_tail6, color=color)
        mb.addFace(p_tail_base6, p_tail_base3, p_tail3, color=color)

        self.setSelectionMesh(mb.build())

    @property
    def headPosition(self):
        return self.getPosition()

    @property
    def tailPosition(self):
        return self.getPosition() - self.direction * self.ARROW_TOTAL_LENGTH
