import os
import time

from cura.CuraApplication import CuraApplication
from UM.Logger import Logger
from UM.Math.Vector import Vector
from UM.PluginRegistry import PluginRegistry
from PyQt5.QtCore import QUrl

from threading import Thread
from ..SmartSliceCloudProxy import SmartSliceCloudProxy
from ..utils import getPrintableNodes
from ..stage import SmartSliceStage


class SmartSliceTest():
    run = True

    def __init__(self, proxy: SmartSliceCloudProxy):
        self.stage = True

        self.app = CuraApplication.getInstance()
        self.controller = self.app.getController()
        self.scene = self.controller.getScene()
        self.root = self.scene.getRoot()
        self.proxy = proxy

        self.file = None

    def stageCheck(self):
        return self.stage

    def readFile(self):
        """"
        Read in file from location
        """
        self.file = os.path.join(PluginRegistry.getInstance().getPluginPath("SmartSlicePlugin"), "test_pedal.stl")

        if len(getPrintableNodes()) == 0:
            self.app.readLocalFile(QUrl.fromLocalFile(self.file))

        self.app.activityChanged.connect(self.setStage)

    def setStage(self):
        """"
        Sets active stage to smart slice
        """
        self.app.activityChanged.disconnect(self.setStage)
        self.controller.activeStageChanged.connect(self.testSmartSliceStage)
        self.controller.setActiveStage("SmartSlicePlugin")

    def testSmartSliceLogin(self):
        pass
        #possibly get rid of this as smart slice ui is publiic on github

    def testSmartSliceStage(self):
        self.controller.activeStageChanged.disconnect(self.testSmartSliceStage)
        stage = self.controller.getActiveStage()
        assert isinstance(stage, SmartSliceStage.SmartSliceStage)

        # test 1 remove part and asser that stage is no longer smart slice stage
        printable_nodes = getPrintableNodes()
        if len(printable_nodes) == 1:
            self.controller.activeStageChanged.connect(self.testSmartSliceStageExited)
            self.root.removeChild(printable_nodes[0])
            printable_nodes = getPrintableNodes()

    def testSmartSliceStageExited(self):
        self.controller.activeStageChanged.disconnect(self.testSmartSliceStageExited)
        stage = self.controller.getActiveStage()
        assert not isinstance(stage, SmartSliceStage.SmartSliceStage)
        self.addTwoModels()

    def addTwoModels(self):
        # test 2 add multiple printable parts in preview stage and try and switch to smartslice: assert that smart slivce stage is not selected
        if len(getPrintableNodes()) == 0:
            self.app.readLocalFile(QUrl.fromLocalFile(self.file))
            self.app.readLocalFile(QUrl.fromLocalFile(self.file))

        self.app.activityChanged.connect(self.testMultipleModels)

    def testMultipleModels(self):
        printable_nodes = getPrintableNodes()
        self.app.activityChanged.disconnect(self.testMultipleModels)
        self.controller.setActiveStage("SmartSlicePlugin")
        stage = self.controller.getActiveStage()
        assert not isinstance(stage, SmartSliceStage.SmartSliceStage)

        # test 3 remove a single part and switch to smart slice stage: assert that current stage is smart slice
        self.root.removeChild(printable_nodes[1])
        self.controller.setActiveStage("SmartSlicePlugin")
        stage = self.controller.getActiveStage()
        assert isinstance(stage, SmartSliceStage.SmartSliceStage)

        self.testSmartSliceRequirements()

    def testSmartSliceRequirements(self):
        from ..requirements_tool.SmartSliceRequirements import SmartSliceRequirements
        requirements = SmartSliceRequirements.getInstance()
        requirements.setTargetSafetyFactor(2.0)
        assert self.proxy.targetSafetyFactor == 2.0

        #requirements.setTargetSafetyFactor(0.1)
        #assert self.proxy.targetSafetyFactor == 1.0


        # test 1 - 3 enter value for FOS Displacement and force magnitude: assert that values getting back are valeus that were just entered

    def faceSelectionTest(self):
        pass
        # test 1 add load face: assert that child node is load face node that was just added
        # test 2 add anchor face: assert that child node is anchor face that was added

    def validationTest(self):
        pass
        # try to run validation: assert that if underdimensioned results are less than deesired, vice versa for overdimenshioned

    def optimizationTest(self):
        pass


    def runTestSuite(self):
        self.readFile()
