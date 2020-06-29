from cura.CuraApplication import CuraApplication
from UM.Math.Vector import Vector

from threading import Thread

from .utils import getPrintableNodes, makeInteractiveMesh
from .select_tool.SmartSliceSelectTool import SmartSliceSelectTool, Force

def getMeshData():
    node = getPrintableNodes()[0]
    md = node.getMeshData()
    return md


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

    def stageCheck(self):
        return self.stage

    def set_run(self):
        self.runTest = False
        self.stage = True

    def readFile(self):
        from PyQt5.QtCore import QUrl
        if self.runTest and len(getPrintableNodes()) == 0:
            self.app.readLocalFile(QUrl.fromLocalFile('/home/colman/Downloads/pedal_fixture-v2_z_build.stl'))
            self.set_run()
            del QUrl

    def setStage(self):
        """"
        Sets active stage to smart slice
        """
        # TODO change logical flow to main function
        if self.stage and len(getPrintableNodes()) > 0:
            self.controller.setActiveStage("SmartSlicePlugin")
            self.stage = False
            self.sel_tool = SmartSliceSelectTool.getInstance()
            self.anchorFace()
            self.loadFace()

    def anchorFace(self):
        """"
        draw anchor face from given data
        """
        aface = self.sel_tool.anchorFace()

        self._interactive_mesh = makeInteractiveMesh(getMeshData())
        selected_triangles = list(self._interactive_mesh.select_planar_face(235))
        aface.triangles = selected_triangles

        self.sel_tool.returnHandle().drawSelection(1, selected_triangles)
        self.sel_tool.selectedFaceChanged.emit()

    def loadFace(self):
        """"
        draw load face with magnitude and direction
        """
        lFace = self.sel_tool.loadFace()
        selected_triangles = list(self._interactive_mesh.select_planar_face(249))
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

    def verificationSetter(self):
        return self.verify

    def setVerification(self):
        self.verify = False

    def main(self):
        thread = Thread(target=self.readFile)
        thread.start()

    def faceSelectedTest(self):

