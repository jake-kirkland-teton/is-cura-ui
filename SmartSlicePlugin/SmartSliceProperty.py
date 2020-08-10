from typing import List, Optional

import copy
from enum import Enum

from UM.Settings.SettingInstance import InstanceState

from cura.CuraApplication import CuraApplication
from cura.Scene.CuraSceneNode import CuraSceneNode

from . utils import getPrintableNodes, findChildSceneNode, angleBetweenVectors
from .stage.SmartSliceScene import HighlightFace, AnchorFace, LoadFace, Root


class SmartSlicePropertyColor():
    SubheaderColor = "#A9A9A9"
    WarningColor = "#F3BA1A"
    ErrorColor = "#F15F63"
    SuccessColor = "#5DBA47"


class TrackedProperty:
    def value(self):
        raise NotImplementedError()

    def cache(self):
        raise NotImplementedError()

    def restore(self):
        raise NotImplementedError()

    def changed(self) -> bool:
        raise NotImplementedError()

    def _getMachineAndExtruder(self):
        machine = CuraApplication.getInstance().getMachineManager().activeMachine
        extruder = None
        if machine and len(machine.extruderList) > 0:
            extruder = machine.extruderList[0]
        return machine, extruder


class ContainerProperty(TrackedProperty):
    NAMES = []

    def __init__(self, name):
        self.name = name
        self._cached_value = None

    @classmethod
    def CreateAll(cls) -> List['ContainerProperty']:
        return list(
            map( lambda n: cls(n), cls.NAMES )
        )

    def cache(self):
        self._cached_value = self.value()

    def changed(self) -> bool:
        return self._cached_value != self.value()


class GlobalProperty(ContainerProperty):
    NAMES = [
        "layer_height",                       #   Layer Height
        "layer_height_0",                     #   Initial Layer Height
        "quality",
        "magic_spiralize",
        "wireframe_enabled",
        "adaptive_layer_height_enabled"
    ]

    def value(self):
        machine, extruder = self._getMachineAndExtruder()
        if machine:
            return machine.getProperty(self.name, "value")
        return None

    def restore(self):
        machine, extruder = self._getMachineAndExtruder()
        if machine and self._cached_value and self._cached_value != self.value():
            machine.setProperty(self.name, "value", self._cached_value, set_from_cache=True)
            machine.setProperty(self.name, "state", InstanceState.Default, set_from_cache=True)


class ExtruderProperty(ContainerProperty):
    NAMES = [
        "line_width",                       #  Line Width
        "wall_line_width",                  #  Wall Line Width
        "wall_line_width_x",                #  Outer Wall Line Width
        "wall_line_width_0",                #  Inner Wall Line Width
        "wall_line_count",                  #  Wall Line Count
        "wall_thickness",                   #  Wall Thickness
        "skin_angles",                      #  Skin (Top/Bottom) Angles
        "top_layers",                       #  Top Layers
        "bottom_layers",                    #  Bottom Layers
        "infill_pattern",                   #  Infill Pattern
        "infill_sparse_density",            #  Infill Density
        "infill_angles",                    #  Infill Angles
        "infill_line_distance",             #  Infill Line Distance
        "infill_sparse_thickness",          #  Infill Line Width
        "infill_line_width",                #  Infill Line Width
        "alternate_extra_perimeter",        #  Alternate Extra Walls
        "initial_layer_line_width_factor",  # % Scale for the initial layer line width
        "top_bottom_pattern",               # Top / Bottom pattern
        "top_bottom_pattern_0",             # Initial top / bottom pattern
        "gradual_infill_steps",
        "mold_enabled",
        "magic_mesh_surface_mode",
        "spaghetti_infill_enabled",
        "magic_fuzzy_skin_enabled",
        "skin_line_width"
    ]

    def value(self):
        machine, extruder = self._getMachineAndExtruder()
        if extruder:
            return extruder.getProperty(self.name, "value")
        return None

    def restore(self):
        machine, extruder = self._getMachineAndExtruder()
        if extruder and self._cached_value and self._cached_value != self.value():
            extruder.setProperty(self.name, "value", self._cached_value, set_from_cache=True)
            extruder.setProperty(self.name, "state", InstanceState.Default, set_from_cache=True)


class SelectedMaterial(TrackedProperty):
    def __init__(self):
        self._cached_material = None

    def value(self):
        machine, extruder = self._getMachineAndExtruder()
        if extruder:
            return extruder.material

    def cache(self):
        self._cached_material = self.value()

    def restore(self):
        machine, extruder = self._getMachineAndExtruder()
        if extruder and self._cached_material:
            extruder.material = self._cached_material

    def changed(self) -> bool:
        return not (self._cached_material is self.value())


class Scene(TrackedProperty):
    def __init__(self):
        self._print_node = None
        self._print_node_scale = None
        self._print_node_ori = None

    def value(self):
        nodes = getPrintableNodes()
        if nodes:
            n = nodes[0]
            return (n, n.getScale(), n.getOrientation())
        return None, None, None

    def cache(self):
        self._print_node, self._print_node_scale, self._print_node_ori = self.value()

    def restore(self):
        self._print_node.setScale(self._print_node_scale)
        self._print_node.setOrientation(self._print_node_ori)
        self._print_node.transformationChanged.emit(self._print_node)

    def changed(self) -> bool:
        node, scale, ori = self.value()

        if self._print_node is not node:
            # What should we do here? The entire model was swapped out
            self.cache()
            return False

        return \
            scale != self._print_node_scale or \
            ori != self._print_node_ori


class ModifierMesh(TrackedProperty):
    def __init__(self, node=None, name=None):
        self.parent_changed = False
        self.mesh_name = name
        self._node = node
        self._properties = None
        self._prop_changed = None
        self._names = [
            "line_width",                       #  Line Width
            "wall_line_width",                  #  Wall Line Width
            "wall_line_width_x",                #  Outer Wall Line Width
            "wall_line_width_0",                #  Inner Wall Line Width
            "wall_line_count",                  #  Wall Line Count
            "wall_thickness",                   #  Wall Thickness
            "top_layers",                       #  Top Layers
            "bottom_layers",                    #  Bottom Layers
            "infill_pattern",                   #  Infill Pattern
            "infill_sparse_density",            #  Infill Density
            "infill_sparse_thickness",          #  Infill Line Width
            "infill_line_width",                #  Infill Line Width
            "top_bottom_pattern",               # Top / Bottom pattern
        ]

    def value(self):
        if self._node:
            stack = self._node.callDecoration("getStack").getTop()
            properties = tuple([stack.getProperty(property, "value") for property in self._names])
            return properties
        return None

    def cache(self):
        self._properties = self.value()

    def changed(self):
        if self._node:
            properties = self.value()
            prop_changed = [[name, prop] for name, prop in zip(self._names, self._properties) if prop not in properties]
            if prop_changed:
                self._prop_changed = prop_changed[0]
                return True

    def restore(self):
        if self._node and self._prop_changed:
            node = self._node.callDecoration("getStack").getTop()
            node.setProperty(self._prop_changed[0], "value", self._prop_changed[1])
            self._prop_changed = None

    def parentChanged(self, parent):
        self.parent_changed = True


class ToolProperty(TrackedProperty):
    def __init__(self, tool, property):
        self._tool = tool
        self._property = property
        self._cached_value = None

    @property
    def name(self):
        return self._property

    def value(self):
        return getattr(self._tool, 'get' + self._property)()

    def cache(self):
        self._cached_value = self.value()

    def restore(self):
        getattr(self._tool, 'set' + self._property)(self._cached_value)

    def changed(self) -> bool:
        return self._cached_value != self.value()


class SmartSliceFace(TrackedProperty):

    class Properties():

        def __init__(self):
            self.direction = None
            self.pull = None
            self.direction_type = None
            self.magnitude = None
            self.surface_type = None
            self.triangles = None
            self.axis = None

    def __init__(self, face):
        self.face = face
        self._properties = self.Properties()

    def value(self):
        return self.face

    def cache(self):
        face = self.value()
        self._properties.triangles = face.getTriangles()
        self._properties.surface_type = face.surface_type
        self._properties.axis = face.axis

        if isinstance(face, LoadFace):
            self._properties.direction = face.activeArrow.direction
            self._properties.direction_type = face.force.direction_type
            self._properties.pull = face.force.pull
            self._properties.magnitude = face.force.magnitude

    def changed(self) -> bool:
        face = self.value()

        def checkBase(face, properties):
            return face.getTriangles() != properties.triangles or \
                face.axis != properties.axis or \
                face.surface_type != properties.surface_type

        if isinstance(face, LoadFace):
            return checkBase(face, self._properties) or \
                face.force.magnitude != self._properties.magnitude or \
                face.force.direction_type != self._properties.direction_type or \
                face.force.pull != self._properties.pull or \
                face.activeArrow.direction != self._properties.direction

        else:
            return checkBase(face, self._properties)

    def restore(self):
        if isinstance(self.face, LoadFace):
            self.face.force.magnitude = self._properties.magnitude
            self.face.force.pull = self._properties.pull
            self.face.force.direction_type = self._properties.direction_type

        self.face.surface_type = self._properties.surface_type
        self.face.setMeshDataFromPywimTriangles(self._properties.triangles, self._properties.axis)

        # Rotate the load arrow back to match
        if isinstance(self.face, LoadFace):
            self.face.setArrow(self._properties.direction)

class SmartSliceSceneRoot(TrackedProperty):
    def __init__(self, root: Root = None):
        self._root = root
        self._faces = [] # HighlightFaces

    def value(self):
        faces = []
        if self._root:
            for child in self._root.getAllChildren():
                if isinstance(child, HighlightFace):
                    faces.append(child)
        return faces

    def cache(self):
        self._faces = self.value()

    def changed(self) -> bool:
        faces = self.value()
        if len(self._faces) != len(faces):
            return True

        #     if f not in faces: # check the id(f) not in [id(f2) for f2 in faces]
        #         return True
        return False

    def restore(self):
        if self._root is None:
            return

        faces = self.value()

        # Remove any faces which were added
        for f in faces:
            if f not in self._faces:
                self._root.removeChild(f)

        # Add any faces which were removed
        for f in self._faces:
            if f not in faces:
                self._root.addChild(f)
