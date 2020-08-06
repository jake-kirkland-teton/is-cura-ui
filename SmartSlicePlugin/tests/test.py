from cura.CuraApplication import CuraApplication
from UM.Math.Vector import Vector

from threading import Thread
from ..utils import getPrintableNodes


class SmartSliceTest:
    run = True

    def __init__(self):
        self.stage = True

        self.app = CuraApplication.getInstance()
        self.controller = self.app.getController()
        self.scene = self.controller.getScene()
        self.root = self.scene.getRoot()

        self.file = "/home/colman/Downloads/pedal_fixture-v2_z_build.stl"

    def stageCheck(self):
        return self.stage

    def readFile(self):
        """"
        Read in file from location
        """
        from PyQt5.QtCore import QUrl
        if len(getPrintableNodes()) == 0:
            self.app.readLocalFile(QUrl.fromLocalFile(self.file))
            del QUrl

        self.app.activityChanged.connect(self.setStage)

    def setStage(self):
        """"
        Sets active stage to smart slice
        """
        self.app.activityChanged.disconnect(self.setStage)
        self.controller.setActiveStage("SmartSlicePlugin")

    def testSmartSliceLogin(self):
        pass
        #possibly get rid of this as smart slice ui is publiic on github

    def testSmartSliceStage(self):
        pass
        # test 1 remove part and asser that stage is no longer smart slice stage
        # test 2 add multiple printable parts in preview stage and try and switch to smartslice: assert that smart slivce stage is not selected
        # test 3 add single part and switch to smart slice stage: assert that current stage is smart slice

    def testSmartSliceRequirements(self):
        pass
        # test 1 - 3 enter value for FOS Displacement and force magnitude: assert that values getting back are valeus that were just entered

    def faceSelectionTest(self):
        pass
        # test 1 add load face: assert that child node is load face node that was just added
        # test 2 add anchor face: assert that child node is anchor face that was added

    def validationTest(self):
        pass
        # try to run validation: assert that if underdimensioned results are less than deesired, vice versa for overdimenshioned

    def optimizationTest(self):


    def runTestSuite(self):
        self.readFile()
