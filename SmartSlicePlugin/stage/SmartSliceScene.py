from typing import List, Any
from enum import Enum

import enum

from UM.Logger import Logger
from UM.Mesh.MeshBuilder import MeshBuilder
from UM.Math.Color import Color
from UM.Math.Vector import Vector
from UM.Math.Matrix import Matrix
from UM.Scene.SceneNode import SceneNode
from UM.Scene.Iterator.DepthFirstIterator import DepthFirstIterator
from UM.Signal import Signal
from UM.Application import Application

from ..utils import makeInteractiveMesh, getPrintableNodes
from ..select_tool.LoadHandle import LoadHandle

import pywim
import numpy

class Force:

    class DirectionType(Enum):
        Normal = 1
        Parallel = 2

    def __init__(self, directionType: DirectionType = DirectionType.Normal,
        direction: Vector = Vector.Unit_X, magnitude: float = 0.0, pull: bool = False):

        self.directionType = directionType
        self.direction = direction
        self.magnitude = magnitude
        self.pull = pull

    def loadVector(self, rotation: Matrix = None) -> Vector:
        scale = self.magnitude if self.pull else -self.magnitude

        v = Vector(
            self.direction.x * scale,
            self.direction.y * scale,
            self.direction.z * scale,
        )

        if rotation:
            vT = numpy.dot(rotation.getData(), v.getData())
            return Vector(vT[0], vT[1], vT[2])

        return v


class Root(SceneNode):
    faceAdded = Signal()
    faceRemoved = Signal()
    loadPropertyChanged = Signal()
    rootChanged = Signal()

    def __init__(self):
        super().__init__(name='_SmartSlice', visible=True)

    def initialize(self, parent: SceneNode):
        parent.addChild(self)

        mesh_data = parent.getMeshData()

        if mesh_data:
            Logger.log('d', 'Compute interactive mesh from SceneNode {}'.format(parent.getName()))

            self._interactive_mesh = makeInteractiveMesh(mesh_data)

        self.rootChanged.emit(self)

    def getInteractiveMesh(self) -> pywim.geom.tri.Mesh:
        return self._interactive_mesh

    def addFace(self, bc):
        self.addChild(bc)
        self.faceAdded.emit(bc)

    def removeFace(self, bc):
        self.removeChild(bc)
        self.faceRemoved.emit(bc)

    def magnitudeChanged(self):
        self.loadPropertyChanged.emit()

    def loadStep(self, step):
        for bc in step.boundary_conditions:
            face = AnchorFace(str(bc.name))
            face.setMeshDataFromPywimTriangles(self._interactive_mesh.triangles_from_ids(bc.face))
            self.addFace(face)

        for bc in step.loads:
            face = LoadFace(str(bc.name))
            face.setMeshDataFromPywimTriangles(self._interactive_mesh.triangles_from_ids(bc.face))
            face.force.magnitude = abs(sum(bc.force))

            load_tuple = bc.force
            load_vector = Vector(
                load_tuple[0],
                load_tuple[1],
                load_tuple[2]
            )

            __, rotation = self.rotation()
            rotated_load_vector = numpy.dot(rotation.getData(), load_vector.getData())
            rotated_vector = Vector(rotated_load_vector[0], rotated_load_vector[1], rotated_load_vector[2])

            rotated_load = pywim.geom.Vector(
                rotated_vector.x,
                rotated_vector.y,
                rotated_vector.z
            )

            if len(face.getTriangles()) > 0:
                face_normal = face.getTriangles()[0].normal
                face.force.direction = Vector(
                    face_normal.r,
                    face_normal.s,
                    face_normal.t
                )

                if face_normal.angle(rotated_load) < self._interactive_mesh._COPLANAR_ANGLE:
                    face.setArrowDirection(True)
                else:
                    face.setArrowDirection(False)

            self.addFace(face)

    def createSteps(self) -> pywim.WimList:
        steps = pywim.WimList(pywim.chop.model.Step)

        step = pywim.chop.model.Step(name='step-1')

        normal_mesh = getPrintableNodes()[0]

        transformation, __ = self.rotation()

        mesh_transformation = normal_mesh.getLocalTransformation()
        mesh_transformation.preMultiply(transformation)

        _, mesh_rotation, _, _ = mesh_transformation.decompose()

        # Add boundary conditions from the selected faces in the Smart Slice node
        for bc_node in DepthFirstIterator(self):
            if hasattr(bc_node, 'pywimBoundaryCondition'):
                bc = bc_node.pywimBoundaryCondition(step, mesh_rotation)

        steps.add(step)

        return steps

    def setOrigin(self):
        controller = Application.getInstance().getController()
        camTool = controller.getCameraTool()
        camTool.setOrigin(self.getParent().getBoundingBox().center)

    @staticmethod
    def rotation():
        transformation = Matrix()
        transformation.setRow(1, [0, 0, 1, 0])
        transformation.setRow(2, [0, -1, 0, 0])
        _, rotation, _, _ = transformation.decompose()
        return transformation, rotation

class HighlightFace(SceneNode):

    class SurfaceType(enum.Enum):
        Flat = 1
        Concave = 2
        Convex = 3

    def __init__(self, name: str):
        super().__init__(name=name, visible=True)

        self._triangles = []
        self.surface_type = self.SurfaceType.Flat
        self._axis = None

    def _annotatedMeshData(self, mb: MeshBuilder):
        pass

    def _setupTools(self):
        pass

    def getTriangleIndices(self) -> List[int]:
        return [t.id for t in self._triangles]

    def getTriangles(self):
        return self._triangles

    def setMeshDataFromPywimTriangles(
        self, tris: List[pywim.geom.tri.Triangle],
        axis: pywim.geom.Vector = None
    ):
        self._triangles = tris
        self._axis = axis

        mb = MeshBuilder()

        for tri in self._triangles:
            mb.addFace(tri.v1, tri.v2, tri.v3)

        self._annotatedMeshData(mb)

        mb.calculateNormals()

        self.setMeshData(mb.build())

        self._setupTools()

    def pywimBoundaryCondition(self, step: pywim.chop.model.Step, mesh_rotation: Matrix):
        raise NotImplementedError()

    def enableTools(self):
        pass

    def disableTools(self):
        pass

    @classmethod
    def findPointsCenter(self, points) -> Vector :
        """
            Find center point among all input points.
            Input:
                points   (list) a list of one or more pywim.geom.Vertex points.
            Output: (Vector) A single vector averaging the input points.
        """
        xs = 0
        ys = 0
        zs = 0
        for p in points:
            xs += p.x
            ys += p.y
            zs += p.z
        num_p = len(points)
        return Vector(xs / num_p, ys / num_p, zs / num_p)

    @classmethod
    def findFaceCenter(self, triangles) -> Vector:
        """
            Find center of face.  Return point is guaranteed to be on face.
            Inputs:
                triangles: (list) Triangles. All triangles assumed to be in same plane.
        """
        c_point = self.findPointsCenter(
            [point for tri in triangles for point in tri.points])  # List comprehension creates list of points.
        for tri in triangles:
            if LoadFace._triangleContainsPoint(tri, c_point):
                return c_point

        # When center point is not on face, choose instead center point of middle triangle.
        index = len(triangles) // 2
        tri = triangles[index]
        return self.findPointsCenter(tri.points)

    @staticmethod
    def _triangleContainsPoint(triangle, point):
        v1 = triangle.v1
        v2 = triangle.v2
        v3 = triangle.v3

        area_2 = LoadFace._threePointArea2(v1, v2, v3)
        alpha = LoadFace._threePointArea2(point, v2, v3) / area_2
        beta = LoadFace._threePointArea2(point, v3, v1) / area_2
        gamma = LoadFace._threePointArea2(point, v1, v2) / area_2

        total = alpha + beta + gamma

        return total > 0.99 and total < 1.01

    @staticmethod
    def _threePointArea2(p, q, r):
        pq = (q.x - p.x, q.y - p.y, q.z - p.z)
        pr = (r.x - p.x, r.y - p.y, r.z - p.z)

        vect = numpy.cross(pq, pr)

        # Return area X 2
        return numpy.sqrt(vect[0] ** 2 + vect[1] ** 2 + vect[2] ** 2)

class AnchorFace(HighlightFace):
    color = Color(1., 0.4, 0.4, 1.)

    def pywimBoundaryCondition(self, step: pywim.chop.model.Step, mesh_rotation: Matrix):
        # Create the fixed boundary conditions (anchor points)
        anchor = pywim.chop.model.FixedBoundaryCondition(name=self.getName())

        # Add the face Ids from the STL mesh that the user selected for this anchor
        a = self._triangles
        b = self.getTriangleIndices()
        anchor.face.extend(self.getTriangleIndices())

        Logger.log("d", "Smart Slice {} Triangles: {}".format(self.getName(), anchor.face))

        step.boundary_conditions.append(anchor)

        return anchor

class LoadFace(HighlightFace):
    color = LoadHandle.color

    def __init__(self, name: str):
        super().__init__(name)

        self.force = Force()
        self._axis = None

        self._tool_handle = LoadHandle(parent=self)
        self._tool_handle.buildMesh()
        self.disableTools()

    def setMeshDataFromPywimTriangles(
        self, tris: List[pywim.geom.tri.Triangle],
        axis:pywim.geom.Vector = None
    ):

        # If there is no axis, we don't know where to put the arrow, so we don't do anything
        if not axis or len(tris) == 0:
            self.disableTools()
            return

        super().setMeshDataFromPywimTriangles(tris, axis)

    def setArrowDirection(self, checked):
        self.force.pull = checked  # Check box checked indicates pulling force
        self.setMeshDataFromPywimTriangles(self._triangles, self.surface_type, None)

    def pywimBoundaryCondition(self, step: pywim.chop.model.Step, mesh_rotation: Matrix):

        force = pywim.chop.model.Force(name=self.getName())

        load_vec = self.force.loadVector(mesh_rotation)

        Logger.log("d", "Smart Slice {} Vector: {}".format(self.getName(), load_vec))

        force.force.set(
            [float(load_vec.x), float(load_vec.y), float(load_vec.z)]
        )

        # Add the face Ids from the STL mesh that the user selected for this force
        force.face.extend(self.getTriangleIndices())

        Logger.log("d", "Smart Slice {} Triangles: {}".format(self.getName(), force.face))

        step.loads.append(force)

        return force

    def _setupTools(self):
        if self.surface_type == HighlightFace.SurfaceType.Flat and self.force.directionType is Force.DirectionType.Parallel:
            self.enableTools()

        elif self.surface_type != HighlightFace.SurfaceType.Flat and self.force.directionType is Force.DirectionType.Normal:
            self.enableTools()

        else:
            # self.disableTools()
            self.enableTools()

    def enableTools(self):
        self._tool_handle.setEnabled(True)
        self._tool_handle.setVisible(True)

        if self._axis is None:
            self.disableTools()
            return

        center = Vector(
            self._axis.origin.x,
            self._axis.origin.y,
            self._axis.origin.z,
        )

        rotation_axis = Vector(
            self._axis.r,
            self._axis.s,
            self._axis.t
        )

        self._tool_handle.setCenterAndRotationAxis(center, rotation_axis, None)

    def disableTools(self):
        self._tool_handle.setEnabled(False)
        self._tool_handle.setVisible(False)

