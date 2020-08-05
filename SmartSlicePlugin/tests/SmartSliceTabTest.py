from unittest.mock import MagicMock, patch

import pytest

from ..stage.SmartSliceStage import SmartSliceStage
from UM.Scene.SceneNode import SceneNode
from cura.Machines.Models.MultiBuildPlateModel import MultiBuildPlateModel
from cura.Scene.CuraSceneController import CuraSceneController
from cura.UI.ObjectsModel import ObjectsModel


@pytest.fixture
def objects_model() -> ObjectsModel:
    return MagicMock(spec=ObjectsModel)

@pytest.fixture
def multi_build_plate_model() -> MultiBuildPlateModel:
    return MagicMock(spec=MultiBuildPlateModel)

@pytest.fixture
def ss_stage() -> SmartSliceStage:
    return MagicMock(spec=SmartSliceStage)

@pytest.fixture
def mocked_application():
    mocked_application = MagicMock()
    mocked_controller = MagicMock()
    mocked_stage = MagicMock()
    mocked_application.getController = MagicMock(return_value=mocked_controller)
    mocked_controller.getStage = MagicMock(return_value=mocked_stage)
    return mocked_application

def test_onStageSelected(ss_stage, mocked_application):
    with patch("CuraApplication.getInstance"):
        controller = CuraSceneController(objects_model, multi_build_plate_model)