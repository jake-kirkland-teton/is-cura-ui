from UM.Math.Color import Color
from UM.Scene.ToolHandle import ToolHandle

class LoadToolHandle(ToolHandle):
    """Base for the Smart Slice Tool Handles"""

    PADDING = 3

    ARROW_HEAD_LENGTH = 8
    ARROW_TAIL_LENGTH = 22
    ARROW_TOTAL_LENGTH = ARROW_HEAD_LENGTH + ARROW_TAIL_LENGTH
    ARROW_HEAD_WIDTH = 2.8
    ARROW_TAIL_WIDTH = 0.8

    ACTIVE_ARROW_HEAD_LENGTH = ARROW_HEAD_LENGTH + PADDING
    ACTIVE_ARROW_TAIL_LENGTH = ARROW_TAIL_LENGTH - PADDING
    ACTIVE_ARROW_HEAD_WIDTH = ARROW_HEAD_WIDTH + PADDING
    ACTIVE_ARROW_TAIL_WIDTH = ARROW_TAIL_WIDTH + PADDING

    INNER_RADIUS = 2 * ARROW_TOTAL_LENGTH
    LINE_WIDTH = 1.0
    OUTER_RADIUS = INNER_RADIUS + LINE_WIDTH
    ACTIVE_INNER_RADIUS = INNER_RADIUS - PADDING
    ACTIVE_OUTER_RADIUS = OUTER_RADIUS + PADDING
    ACTIVE_LINE_WIDTH = LINE_WIDTH + PADDING

    def __init__(self, parent = None):
        super().__init__(parent)
        self._auto_scale = False

    def _onSelectionCenterChanged(self) -> None:
        pass

    def buildMesh(self):
        from UM.Qt.QtApplication import QtApplication
        theme = QtApplication.getInstance().getTheme()

        self._disabled_axis_color = Color(*theme.getColor("disabled_axis").getRgb())
        self._x_axis_color = Color(*theme.getColor("x_axis").getRgb())
        self._y_axis_color = Color(*theme.getColor("y_axis").getRgb())
        self._z_axis_color = Color(*theme.getColor("z_axis").getRgb())
        self._all_axis_color = Color(*theme.getColor("all_axis").getRgb())

        self._axis_color_map = {
            self.NoAxis: self._disabled_axis_color,
            self.XAxis: self._x_axis_color,
            self.YAxis: self._y_axis_color,
            self.ZAxis: self._z_axis_color,
            self.AllAxis: self._all_axis_color
        }
