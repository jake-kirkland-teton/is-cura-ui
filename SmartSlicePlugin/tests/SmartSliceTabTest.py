from unittest.mock import MagicMock, patch

import pytest

from ..stage.SmartSliceStage import SmartSliceStage
from UM.Scene.SceneNode import SceneNode
from UM.PluginObject import PluginObject
from cura.Machines.Models.MultiBuildPlateModel import MultiBuildPlateModel
from cura.Scene.CuraSceneController import CuraSceneController
from cura.UI.ObjectsModel import ObjectsModel
from UM.Scene.Selection import Selection


@pytest.fixture
def objects_model() -> ObjectsModel:
    return MagicMock(spec = ObjectsModel)

@pytest.fixture
def multi_build_plate_model() -> MultiBuildPlateModel:
    return MagicMock(spec = MultiBuildPlateModel)

@pytest.fixture
def ss_stage() -> SmartSliceStage:
    return MagicMock(spec = SmartSliceStage)

@pytest.fixture
def mocked_application():
    mocked_application = MagicMock()
    mocked_controller = MagicMock()
    mocked_stage = MagicMock()
    mocked_extruder_manager = MagicMock()
    mocked_application.getController = MagicMock(return_value = mocked_controller)
    mocked_application.getExtruderManager = MagicMock(return_value = mocked_extruder_manager)
    mocked_controller.getStage = MagicMock(return_value = mocked_stage)
    mocked_controller.getActiveStage = MagicMock(return_value = mocked_stage)
    mocked_stage.getPluginId = MagicMock(return_value = "SmartSlicePlugin")
    return mocked_application

def test_checkScene(ss_stage):
    returned_scene_node = None
    with patch("UM.Application.Application.getInstance", MagicMock(return_value = mocked_application))
        ss_stage._exit_stage_if_scene_is_invalid = MagicMock(return_value = SceneNode())
        returned_scene_node = ss_stage._checkScene()
        assert returned_scene_node not None
'''
This is a work in progress, it's a much more complicated test.

def test_onStageSelected(ss_stage, mocked_application):
    with patch("CuraApplication.getInstance"):
        controller = CuraSceneController(objects_model, multi_build_plate_model)
        controller.getActiveView = MagicMock(return_value = "{name:\"active_view\"}")
        controller.setActiveView = MagicMock()
        ss_stage.getStageFaceSupported = MagicMock(return_value = True)
        ss_stage._exit_stage_if_scene_is_invalid = MagicMock(return_value = SceneNode())
        ss_stage._connector.api_connection.openConnection = MagicMock()

'''
