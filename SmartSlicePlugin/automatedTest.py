from cura.CuraApplication import CuraApplication
from UM.Math.Vector import Vector

from threading import Thread

from .utils import getPrintableNodes, makeInteractiveMesh
from .select_tool.SmartSliceSelectTool import SmartSliceSelectTool, Force


class SmartSliceTest():
    def __init__(self):
        self.runTest = True
        self.stage = True

        self.app = CuraApplication.getInstance()
        self.controller = self.app.getController()
        self.scene = self.controller.getScene()
        self.root = self.scene.getRoot()

        self.sel_tool = None
        self._interactive_mesh = None

        self.force = Force(magnitude=75.)

        self.verify = False

        self.node = None

        self.loadMagnitude = 75.0
        self.loadDirection = False

        self.file = "/home/colman/Downloads/pedal_fixture-v2_z_build.stl"

    def stageCheck(self):
        return self.stage

    def set_run(self):
        """"
        sets checks for SmartSLiceCloudConnector to determine which function to run
        """
        self.runTest = False
        self.stage = True

    def readFile(self):
        """"
        Read in file from location
        """
        from PyQt5.QtCore import QUrl
        if self.runTest and len(getPrintableNodes()) == 0:
            self.app.readLocalFile(QUrl.fromLocalFile(self.file))
            self.testFileReader()
            self.set_run()
            del QUrl

    @staticmethod

    def testFileReader():
        """"
        checks that file had been read into cura
        """
        assert len(getPrintableNodes()) > 0

    def setStage(self):
        """"
        Sets active stage to smart slice
        """
        # TODO change logical flow to main function
        if self.stage and len(getPrintableNodes()) > 0:
            self.controller.setActiveStage("SmartSlicePlugin")
            # set check so stage doesnt try and switch on any activity changed
            self.stage = False
            # make sel tool properties available to class
            self.sel_tool = SmartSliceSelectTool.getInstance()

            # set and test load magnitude and direction
            self.setLoadMagnitude(self.loadMagnitude)
            self.setLoadDirection(self.loadDirection)

            # set anchor face and asserts that there is a face selected
            self.anchorFace()
            # sets load direction and asserts that there is a face selected
            self.loadFace()

    @staticmethod
    def getMeshData():
        node = getPrintableNodes()[0]
        md = node.getMeshData()
        return md

    def anchorFace(self):
        """"
        draw anchor face from given data
        """
        aface = self.sel_tool.anchorFace()

        self._interactive_mesh = makeInteractiveMesh(self.getMeshData())
        selected_triangles = list(self._interactive_mesh.select_planar_face(235))
        self.testFaceSelection(selected_triangles)
        aface.triangles = selected_triangles

        self.sel_tool.returnHandle().drawSelection(1, selected_triangles)
        self.sel_tool.selectedFaceChanged.emit()

    def loadFace(self):
        """"
        draw load face with magnitude and direction
        """
        lFace = self.sel_tool.loadFace()
        selected_triangles = list(self._interactive_mesh.select_planar_face(249))
        self.testFaceSelection(selected_triangles)
        lFace.triangles = selected_triangles

        if len(lFace.triangles) > 0:
            tri = lFace.triangles[0]

            # Convert from a pywim.geom.Vector to UM.Math.Vector
            self.force.normal = Vector(
                tri.normal.r,
                tri.normal.s,
                tri.normal.t
            )

        self.sel_tool.returnHandle().drawSelection(2, selected_triangles)

        self.sel_tool.selectedFaceChanged.emit()

        self.verify = True

    @staticmethod
    def testFaceSelection(triangles):
        """"
        assert that selected face is returning triangles
        """
        assert len(triangles) > 0

    def verificationSetter(self):
        """"
        For running verification from SmartSliceCloudConnector
        """
        return self.verify

    def setVerification(self):
        """"
        Helper function for verification setter
        """
        self.verify = False

    def main(self):
        thread = Thread(target=self.readFile)
        thread.start()

    def setLoadMagnitude(self, value: float):
        """"
        sets load magnitude to given value
        """
        self.sel_tool.force.magnitude = value
        self.sel_tool.propertyChanged.emit()
        self.sel_tool.toolPropertyChanged.emit("LoadMagnitude")
        self.testSetLoadMagnitude(value)

    def testSetLoadMagnitude(self, value: float):
        """"
        checkss if load magnitude is correct type and value that it is set to
        """
        assert type(self.sel_tool.getLoadMagnitude() == float)
        assert self.sel_tool.getLoadMagnitude() == 55.5

    def setLoadDirection(self, value: bool):
        """
        simple function to set load direction
        """
        self.sel_tool.setLoadDirection(value)
        self.testLoadDirection(value)

    def testLoadDirection(self, value: bool):
        """
        simple assertation test to check if
        """
        assert type(self.sel_tool.getLoadDirection()) is bool
        assert self.sel_tool.getLoadDirection() is value

    def testValidationResults(self):
        """"
        If underdimensioned check if max disp or safety factor is higher than user input
        If Overdimensioned check if max disp or safety factor are less than user input
        """

