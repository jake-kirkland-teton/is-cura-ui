'''
Created on 22.10.2019

@author: thopiekar
'''

from string import Formatter
import time
import os
import uuid
import tempfile
import json
import zipfile
import re

import numpy

import pywim  # @UnresolvedImport

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtCore import QObject
from PyQt5.QtCore import QTime
from PyQt5.QtCore import QUrl
from PyQt5.QtNetwork import QNetworkReply
from PyQt5.QtNetwork import QNetworkRequest
from PyQt5.QtNetwork import QNetworkAccessManager
from PyQt5.QtQml import qmlRegisterSingletonType

from UM.i18n import i18nCatalog
from UM.Application import Application
from UM.Job import Job
from UM.Logger import Logger
from UM.Message import Message
from UM.PluginRegistry import PluginRegistry
from UM.Scene.SceneNode import SceneNode
from UM.Scene.Iterator.DepthFirstIterator import DepthFirstIterator

from cura.OneAtATimeIterator import OneAtATimeIterator
from cura.Settings.ExtruderManager import ExtruderManager

from .SmartSliceCloudProxy import SmartSliceCloudStatus
from .SmartSliceCloudProxy import SmartSliceCloudProxy

i18n_catalog = i18nCatalog("smartslice")

##  Formatter class that handles token expansion in start/end gcode
class GcodeStartEndFormatter(Formatter):
    def __init__(self, default_extruder_nr: int = -1) -> None:
        super().__init__()
        self._default_extruder_nr = default_extruder_nr

    def get_value(self, key: str, args: str, kwargs: dict) -> str: #type: ignore # [CodeStyle: get_value is an overridden function from the Formatter class]
        # The kwargs dictionary contains a dictionary for each stack (with a string of the extruder_nr as their key),
        # and a default_extruder_nr to use when no extruder_nr is specified

        extruder_nr = self._default_extruder_nr

        key_fragments = [fragment.strip() for fragment in key.split(",")]
        if len(key_fragments) == 2:
            try:
                extruder_nr = int(key_fragments[1])
            except ValueError:
                try:
                    extruder_nr = int(kwargs["-1"][key_fragments[1]]) # get extruder_nr values from the global stack #TODO: How can you ever provide the '-1' kwarg?
                except (KeyError, ValueError):
                    # either the key does not exist, or the value is not an int
                    Logger.log("w", "Unable to determine stack nr '%s' for key '%s' in start/end g-code, using global stack", key_fragments[1], key_fragments[0])
        elif len(key_fragments) != 1:
            Logger.log("w", "Incorrectly formatted placeholder '%s' in start/end g-code", key)
            return "{" + key + "}"

        key = key_fragments[0]

        default_value_str = "{" + key + "}"
        value = default_value_str
        # "-1" is global stack, and if the setting value exists in the global stack, use it as the fallback value.
        if key in kwargs["-1"]:
            value = kwargs["-1"][key]
        if str(extruder_nr) in kwargs and key in kwargs[str(extruder_nr)]:
            value = kwargs[str(extruder_nr)][key]

        if value == default_value_str:
            Logger.log("w", "Unable to replace '%s' placeholder in start/end g-code", key)

        return value

## Draft of an connection check
class ConnectivityChecker(QObject):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        url = QUrl("https://amazonaws.com/")
        req = QNetworkRequest(url)
        self.net_manager = QNetworkAccessManager()
        self.res = self.net_manager.get(req)
        self.res.finished.connect(self.processRes)
        self.res.error.connect(self.processErr)

    @pyqtSlot()
    def processRes(self):
        if self.res.bytesAvailable():
            # Success
            pass
        self.res.deleteLater()

    @pyqtSlot(QNetworkReply.NetworkError)
    def processErr(self, code):
        print(code)

class SmartSliceCloudJob(Job):
    # This job is responsible for uploading the backup file to cloud storage.
    # As it can take longer than some other tasks, we schedule this using a Cura Job.
    
    def __init__(self, connector) -> None:
        super().__init__()
        self.connector = connector
        
        self.cancled = False
        
        self._job_status = None
        self._wait_time = 0.05
        
        self.job_type = None
        self.ui_status_per_job_type = {pywim.smartslice.job.JobType.validation : SmartSliceCloudStatus.BusyValidating,
                                       pywim.smartslice.job.JobType.optimization : SmartSliceCloudStatus.BusyOptimizing,
                                       }


    @property
    def job_status(self):
        return self._job_status

    @job_status.setter
    def job_status(self, value):
        if value is not self._job_status:
            self._job_status = value
            Logger.log("d", "Status changed: {}".format(self.job_status))

    def processCloudJob(self, filepath):
        # Read the 3MF file into bytes
        threemf_fd = open(filepath, 'rb')
        threemf_data = threemf_fd.read()
        threemf_fd.close()
    
        # Create the HTTP client with the default connection parameters
        client = pywim.http.thor.Client2019POC()
    
        # Submit the 3MF data for a new task
        task = client.submit.post(threemf_data)
        Logger.log("d", "Status after post'ing: {}".format(task.status))
        
        # While the task status is not finished or failed continue to periodically
        # check the status. This is a naive way of waiting, since this could take
        # a while (minutes).
        while task.status not in (pywim.http.thor.TaskStatus.failed,
                                  pywim.http.thor.TaskStatus.finished):
            self.job_status = task.status
            
            time.sleep(self._wait_time)
            task = client.status.get(id=task.id)
    
        if task.status == pywim.http.thor.TaskStatus.failed:
            error_message = Message()
            error_message.setTitle("SmartSlice plugin")
            error_message.setText(i18n_catalog.i18nc("@info:status", "Error while processing the job:\n{}".format(task.error)))
            error_message.show()

            Logger.log("e", "An error occured while sending and receiving cloud job: {}".format(task.error))
            return None
        elif task.status == pywim.http.thor.TaskStatus.finished:
            # Get the task again, but this time with the results included
            task = client.result.get(id=task.id)
            return task
        else:
            error_message = Message()
            error_message.setTitle("SmartSlice plugin")
            error_message.setText(i18n_catalog.i18nc("@info:status", "Unexpected status occured:\n{}".format(task.error)))
            error_message.show()
            
            Logger.log("e", "An unexpected status occured while sending and receiving cloud job: {}".format(task.status))
            return None

    def run(self) -> None:
        if not self.job_type:
            error_message = Message()
            error_message.setTitle("SmartSlice plugin")
            error_message.setText(i18n_catalog.i18nc("@info:status", "Job type not set for processing:\nDon't know what to do!"))
            error_message.show()
        
        # TODO: Add instructions how to send a verification job here
        previous_connector_status = self.connector.status
        self.connector.status = self.ui_status_per_job_type[self.job_type]
        Job.yieldThread()
        
        job = self.connector.prepareJob(self.job_type)
        Logger.log("i", "Job prepared: {}".format(job))
        task = self.processCloudJob(job)
        
        #self.job_type == pywim.smartslice.job.JobType.optimization
        if task:
            result = task.result
            if result:
                result_dict = result.to_dict()
                print(result_dict)
                analyse = result.analyses[0]
                print(analyse)
                print(analyse.mass)
                print(analyse.print_time)
                print(analyse.modifier_meshes)
            
            if not self.connector._demo_was_underdimensioned_before:
                self.connector.status = SmartSliceCloudStatus.Underdimensioned
                self.connector._demo_was_underdimensioned_before = True
                
                self.connector._proxy.resultSafetyFactor = 0.5
                self.connector._proxy.resultMaximalDisplacement = 5
                
                self.connector._proxy.resultTimeInfill = QTime(1, 0, 0, 0)
                self.connector._proxy.resultTimeInnerWalls = QTime(0, 20, 0, 0)
                self.connector._proxy.resultTimeOuterWalls = QTime(0, 15, 0, 0)
                self.connector._proxy.resultTimeRetractions = QTime(0, 5, 0, 0)
                self.connector._proxy.resultTimeSkin = QTime(0, 10, 0, 0)
                self.connector._proxy.resultTimeSkirt = QTime(0, 1, 0, 0)
                self.connector._proxy.resultTimeTravel = QTime(0, 30, 0, 0)
            
            elif not self.connector._demo_was_overdimensioned_before:
                self.connector.status = SmartSliceCloudStatus.Overdimensioned
                self.connector._demo_was_overdimensioned_before = True
                
                self.connector._proxy.resultSafetyFactor = 2
                self.connector._proxy.resultMaximalDisplacement = 1
                
                self.connector._proxy.resultTimeInfill = QTime(2, 0, 0, 0)
                self.connector._proxy.resultTimeInnerWalls = QTime(0, 10, 0, 0)
                self.connector._proxy.resultTimeOuterWalls = QTime(0, 20, 0, 0)
                self.connector._proxy.resultTimeRetractions = QTime(0, 3, 0, 0)
                self.connector._proxy.resultTimeSkin = QTime(0, 15, 0, 0)
                self.connector._proxy.resultTimeSkirt = QTime(0, 2, 0, 0)
                self.connector._proxy.resultTimeTravel = QTime(0, 45, 0, 0)
            else:
                self.connector.status = SmartSliceCloudStatus.Optimized
                
                self.connector._proxy.resultSafetyFactor = 1
                self.connector._proxy.resultMaximalDisplacement = 2
                
                self.connector._proxy.resultTimeInfill = QTime(3, 0, 0, 0)
                self.connector._proxy.resultTimeInnerWalls = QTime(0, 10, 0, 0)
                self.connector._proxy.resultTimeOuterWalls = QTime(0, 20, 0, 0)
                self.connector._proxy.resultTimeRetractions = QTime(0, 3, 0, 0)
                self.connector._proxy.resultTimeSkin = QTime(0, 15, 0, 0)
                self.connector._proxy.resultTimeSkirt = QTime(0, 2, 0, 0)
                self.connector._proxy.resultTimeTravel = QTime(0, 45, 0, 0)
        else:
            self.connector.status = previous_connector_status
        

        

class SmartSliceCloudVerificationJob(SmartSliceCloudJob):
    def __init__(self, connector)->None:
        super().__init__(connector)
        
        self.job_type = pywim.smartslice.job.JobType.validation

class SmartSliceCloudOptimizeJob(SmartSliceCloudVerificationJob):
    def __init__(self, connector)->None:
        super().__init__(connector)
        
        self.job_type = pywim.smartslice.job.JobType.optimization

class SmartSliceCloudConnector(QObject):
    token_preference = "smartslice/token"
    
    def __init__(self, extension):
        super().__init__()
        self.extension = extension
        
        # DEMO variables
        self._demo_was_underdimensioned_before = False
        self._demo_was_overdimensioned_before = False
        
        # Variables 
        self._status = None
        self._job = None
        
        # Proxy
        self._proxy = SmartSliceCloudProxy(self)
        self._proxy.sliceButtonClicked.connect(self.onSliceButtonClicked)
        
        # Connecting signals
        self.doVerification.connect(self._doVerfication)
        self.doOptimization.connect(self._doOptimization)
        
        # Application stuff
        Application.getInstance().getPreferences().addPreference(self.token_preference, "")
        Application.getInstance().activityChanged.connect(self._onApplicationActivityChanged)
        
        # Caches
        self._all_extruders_settings = None
        
        # POC
        self._poc_default_infill_direction = 45

    def getProxy(self, engine, script_engine):
        return self._proxy

    def _onEngineCreated(self):
        qmlRegisterSingletonType(SmartSliceCloudProxy,
                                 "SmartSlice",
                                 1, 0,
                                 "Cloud",
                                 self.getProxy
                                 )
        
        self.status = SmartSliceCloudStatus.InvalidInput

    def updateSliceWidget(self):
        if self.status is SmartSliceCloudStatus.InvalidInput:
            self._proxy.sliceStatus = "Amount of loaded models is incorrect"
            self._proxy.sliceHint = "Make sure only one model is loaded!"
            self._proxy.sliceButtonText = "Waiting for model"
            self._proxy.sliceButtonEnabled = False
        elif self.status is SmartSliceCloudStatus.ReadyToVerify:
            self._proxy.sliceStatus = "Ready to validate"
            self._proxy.sliceHint = "Press on the button below to validate your part."
            self._proxy.sliceButtonText = "Validate"
            self._proxy.sliceButtonEnabled = True
        elif self.status is SmartSliceCloudStatus.BusyValidating:
            self._proxy.sliceStatus = "Validating your part"
            self._proxy.sliceHint = "Please wait until the validation is done."
            self._proxy.sliceButtonText = "Busy..."
            self._proxy.sliceButtonEnabled = False
        elif self.status is SmartSliceCloudStatus.Underdimensioned:
            self._proxy.sliceStatus = "Your part is underdesigned!"
            self._proxy.sliceHint = "Optimize to meet requirements."
            self._proxy.sliceButtonText = "Optimize"
            self._proxy.sliceButtonEnabled = True
        elif self.status is SmartSliceCloudStatus.Overdimensioned:
            self._proxy.sliceStatus = "Your part is overdesigned!"
            self._proxy.sliceHint = "Optimize to improve your part."
            self._proxy.sliceButtonText = "Optimize"
            self._proxy.sliceButtonEnabled = True
        elif self.status is SmartSliceCloudStatus.BusyOptimizing:
            self._proxy.sliceStatus = "Optimizing your part"
            self._proxy.sliceHint = "Please wait until the optimization is done."
            self._proxy.sliceButtonText = "Busy..."
            self._proxy.sliceButtonEnabled = False
        elif self.status is SmartSliceCloudStatus.Optimized:
            self._proxy.sliceStatus = "Part optimized"
            self._proxy.sliceHint = "Well done! Now your part suites your needs!"
            self._proxy.sliceButtonText = "Done"
            self._proxy.sliceButtonEnabled = False
        else:
            self._proxy.sliceStatus = "! INTERNAL ERRROR!"
            self._proxy.sliceHint = "! UNKNOWN STATUS ENUM SET!"
            self._proxy.sliceButtonText = "! FOOO !"
            self._proxy.sliceButtonEnabled = False
    
        # Setting icon path
        stage_path = PluginRegistry.getInstance().getPluginPath("SmartSliceStage")
        stage_images_path = os.path.join(stage_path, "images")
        icon_done_green = os.path.join(stage_images_path, "done_green.svg")
        icon_error_red = os.path.join(stage_images_path, "error_red.svg")
        icon_warning_yellow = os.path.join(stage_images_path, "warning_yellow.svg")
        current_icon = icon_done_green
        if self.status is SmartSliceCloudStatus.Overdimensioned:
            current_icon = icon_warning_yellow
        elif self.status is SmartSliceCloudStatus.Underdimensioned:
            current_icon = icon_error_red
        self._proxy.sliceIconImage = current_icon
        
        # Setting icon visibiltiy
        if self.status is SmartSliceCloudStatus.Optimized or self.status in SmartSliceCloudStatus.Optimizable:
            self._proxy.sliceIconVisible = True
        else:
            self._proxy.sliceIconVisible = False

    @property
    def status(self):
        return self._status
    
    @status.setter
    def status(self, value):
        if self._status is not value:
            self._status = value
            
            self.updateSliceWidget()
    
    @property
    def token(self):
        return Application.getInstance().getPreferences().getValue(self.token_preference)
    
    @token.setter
    def token(self, value):
        Application.getInstance().getPreferences().setValue(self.token_preference, value)
    
    def login(self):
        #username = self._proxy.loginName()
        #password = self._proxy.loginPassword()
        
        if True:
            self.token = "123456789qwertz"
            return True
        else:
            self.token = ""
            return False

    def getSliceableNodes(self):
        scene_node = Application.getInstance().getController().getScene().getRoot()
        sliceable_nodes = []

        for node in DepthFirstIterator(scene_node):
            if node.callDecoration("isSliceable"):
                sliceable_nodes.append(node)

        return sliceable_nodes

    def _onApplicationActivityChanged(self):
        slicable_nodes_count = len(self.getSliceableNodes())
        
        # TODO: Add check for anchors and loads here!
        
        if slicable_nodes_count == 1:
            self.status = SmartSliceCloudStatus.ReadyToVerify
        else:
            self.status = SmartSliceCloudStatus.InvalidInput
    
    def _onJobFinished(self, job):
        self._job = None
    
    doVerification = pyqtSignal()
    
    def _doVerfication(self):
        self._job = SmartSliceCloudVerificationJob(self)
        self._job.finished.connect(self._onJobFinished)
        self._job.start()
    
    doOptimization = pyqtSignal()
    
    def _doOptimization(self):
        self._job = SmartSliceCloudOptimizeJob(self)
        self._job.finished.connect(self._onJobFinished)
        self._job.start()
    
    def onSliceButtonClicked(self):
        if self.status is SmartSliceCloudStatus.ReadyToVerify:
            
            self.doVerification.emit()
        elif self.status in SmartSliceCloudStatus.Optimizable:
            self.status = SmartSliceCloudStatus.BusyOptimizing
            self.doOptimization.emit()

    @property
    def variables(self):
        return self.extension.getVariables(None, None)

    def prepareInitial3mf(self, threemf_path, mesh_nodes):
        # Getting 3MF writer and write our file
        threeMF_Writer = PluginRegistry.getInstance().getPluginObject("3MFWriter")
        threeMF_Writer.write(threemf_path, mesh_nodes)

        return True

    def extend3mf(self, filepath, mesh_nodes, job_type):
        global_stack = Application.getInstance().getGlobalContainerStack()
        machine_manager = Application.getInstance().getMachineManager()
        active_machine = machine_manager.activeMachine
        
        # NOTE: As agreed during the POC, we want to analyse and optimize only one model at the moment.
        #       The lines below will partly need to be executed as "for model in models: bla bla.."
        mesh_node = mesh_nodes[0]
        
        mesh_node_stack = mesh_node.callDecoration("getStack")
        
        active_extruder_position = mesh_node.callDecoration("getActiveExtruderPosition")
        if active_extruder_position is None:
            active_extruder_position = 0
        else:
            active_extruder_position = int(active_extruder_position)

        extruders = list(active_machine.extruders.values())
        extruders = sorted(extruders,
                           key = lambda extruder: extruder.getMetaDataEntry("position")
                           )

        material_guids_per_extruder = []
        for extruder in extruders:
            material_guids_per_extruder.append(extruder.material.getMetaData().get("GUID", ""))

        # TODO: Needs to be determined from the used model
        guid = material_guids_per_extruder[active_extruder_position]
        
        # Determine material properties from material database
        this_dir = os.path.split(__file__)[0]
        database_location = os.path.join(this_dir, "data", "POC_material_database.json")
        jdata = json.loads(open(database_location).read())
        material_found = None
        for material in jdata["materials"]:
            if "cura-guid" not in material.keys():
                continue
            if guid in material["cura-guid"]:
                material_found = material
                break
        
        if not material_found:
            # TODO: Alternatively just raise an exception here
            return False
        
        job = pywim.smartslice.job.Job()

        job.type = job_type
    
        # Create the bulk material definition. This likely will be pre-defined
        # in a materials database or file somewhere
        job.bulk = pywim.fea.model.Material(name=material_found["name"])
        job.bulk.density = material_found["density"]
        job.bulk.elastic = pywim.fea.model.Elastic(properties={'E': material_found["elastic"]['E'],
                                                               'nu': material_found["elastic"]['nu']})
        job.bulk.failure_yield = pywim.fea.model.Yield(type='von_mises',
                                                       properties={'Sy': material_found['failure_yield']['Sy']}
                                                       )
        job.bulk.fracture = pywim.fea.model.Fracture(material_found['fracture']['KIc'])
    
        # Setup optimization configuration
        job.optimization.min_safety_factor = self.variables.safetyFactor
        job.optimization.max_displacement = self.variables.maxDeflect
    
        # Setup the chop model - chop is responsible for creating an FEA model
        # from the triangulated surface mesh, slicer configuration, and
        # the prescribed boundary conditions
        
        # The chop.model.Model class has an attribute for defining
        # the mesh, however, it's not necessary that we do so.
        # When the back-end reads the 3MF it will obtain the mesh
        # from the 3MF object model, therefore, defining it in the 
        # chop object would be redundant.
        #job.chop.meshes.append( ... ) <-- Not necessary
    
        # Define the load step for the FE analysis
        step = pywim.chop.model.Step(name='default')
    
        # Create the fixed boundary conditions (anchor points)
        anchor1 = pywim.chop.model.FixedBoundaryCondition(name='anchor1')
    
        # Add the face Ids from the STL mesh that the user selected for
        # this anchor
        anchor1.face.extend(
            (0, 249, 1, 250)
        )
    
        step.boundary_conditions.append(anchor1)
    
        # Add any other boundary conditions in a similar manner...
    
        # Create an applied force
        force1 = pywim.chop.model.Force(name='force1')
    
        # Set the components on the force vector. In this example
        # we have 100 N, 200 N, and 50 N in the x, y, and z
        # directions respectfully.
        force1.force.set(
            (2., 0., 0.)
        )
    
        # Add the face Ids from the STL mesh that the user selected for
        # this force
        force1.face.extend(
            (255, 256, 248, 247)
        )
    
        step.loads.append(force1)
    
        # Add any other loads in a similar manner...
    
        # Append the step definition to the chop model. Smart Slice only
        # supports one step right now. In the future we may allow multiple
        # loading steps.
        job.chop.steps.append(step)
    
        # Now we need to setup the print/slicer configuration
        
        print_config = pywim.am.Config()
        print_config.layer_width = active_machine.getProperty("line_width", "value")
        print_config.layer_height = active_machine.getProperty("layer_height", "value")
        print_config.walls = mesh_node_stack.getProperty("wall_line_count", "value")
        
        # skin angles - CuraEngine vs. pywim
        # > https://github.com/Ultimaker/CuraEngine/blob/master/src/FffGcodeWriter.cpp#L402 
        skin_angles = active_machine.getProperty("skin_angles", "value")
        if type(skin_angles) is str:
            skin_angles = eval(skin_angles)
        if len(skin_angles) > 0:
            print_config.skin_orientations.extend(tuple(skin_angles))
        else:
            print_config.skin_orientations.extend((45, 135))
        
        
        print_config.bottom_layers = mesh_node_stack.getProperty("top_layers", "value")
        print_config.top_layers = mesh_node_stack.getProperty("bottom_layers", "value")
        
        # infill pattern - Cura vs. pywim 
        infill_pattern = mesh_node_stack.getProperty("infill_pattern", "value")
        infill_pattern_to_pywim_dict = {"grid": pywim.am.InfillType.grid,
                                        "triangles": pywim.am.InfillType.triangle,
                                        "cubic": pywim.am.InfillType.cubic
                                        }
        if infill_pattern in infill_pattern_to_pywim_dict.keys():
            print_config.infill.pattern = infill_pattern_to_pywim_dict[infill_pattern]
        else:
            print_config.infill.pattern = pywim.am.InfillType.unknown
        
        print_config.infill.density = mesh_node_stack.getProperty("infill_sparse_density", "value")
        
        # infill_angles - Setting defaults from the CuraEngine
        # > https://github.com/Ultimaker/CuraEngine/blob/master/src/FffGcodeWriter.cpp#L366
        infill_angles = mesh_node_stack.getProperty("infill_angles", "value")
        if type(infill_angles) is str:
            infill_angles = eval(infill_angles)
        if not len(infill_angles):
            # Check the URL below for the default angles. They are infill type depended.
            print_config.infill.orientation = self._poc_default_infill_direction
        else:
            if len(infill_angles) > 1:
                Logger.log("w", "More than one infill angle is set! Only the first will be taken!")
                Logger.log("d", "Ignoring the angles: {}".format(infill_angles[1:]))
            print_config.infill.orientation = infill_angles[0]
        # ... and so on, check pywim.am.Config for full definition
    
        # The am.Config contains an "auxiliary" dictionary which should
        # be used to define the slicer specific settings. These will be
        # passed on directly to the slicer (CuraEngine).
        print_config.auxiliary = self._buildGlobalSettingsMessage()
    
        # Setup the slicer configuration. See each class for more
        # information.
        extruders = ()
        for extruder_stack in global_stack.extruderList:
            extruder_object = pywim.chop.machine.Extruder(diameter=extruder_stack.getProperty("machine_nozzle_size",
                                                                                     "value"))
            pickled_info = self._buildExtruderMessage(extruder_stack)
            extruder_object.id = pickled_info["id"]
            extruder_object.print_config.auxiliary = pickled_info["settings"]
            extruders += (extruder_object, )
        
        printer = pywim.chop.machine.Printer(name=active_machine.getName(),
                                             extruders=extruders
                                             )
    
        # And finally set the slicer to the Cura Engine with the config and printer defined above
        job.chop.slicer = pywim.chop.slicer.CuraEngine(config=print_config,
                                                       printer=printer)
    
        threemf_file = zipfile.ZipFile(filepath, 'a')
        threemf_file.writestr('SmartSlice/job.json',
                              job.to_json()
                              )
        threemf_file.close()
        

        return True

    def determineTempDirectory(self):
        temporary_directory = tempfile.gettempdir()
        base_subdirectory_name = "smartslice"
        private_subdirectory_name = base_subdirectory_name
        abs_private_subdirectory_name = os.path.join(temporary_directory,
                                                     private_subdirectory_name)
        private_subdirectory_suffix_num = 1
        while os.path.exists(abs_private_subdirectory_name) and not os.path.isdir(abs_private_subdirectory_name):
            private_subdirectory_name = "{}_{}".format(base_subdirectory_name,
                                                       private_subdirectory_suffix_num)
            abs_private_subdirectory_name = os.path.join(temporary_directory,
                                                         private_subdirectory_name)
            private_subdirectory_suffix_num += 1
        
        if not os.path.exists(abs_private_subdirectory_name):
            os.makedirs(abs_private_subdirectory_name)
        
        return abs_private_subdirectory_name
        

    # Sending jobs to AWS
    # - jtype: Job type to be sent. Can be either:
    #          > pywim.smartslice.job.JobType.validation
    #          > pywim.smartslice.job.JobType.optimization
    def prepareJob(self, jtype):
        # Using tempfile module to probe for a temporary file path
        # TODO: We can do this more elegant of course, too.
        
        # Setting up file output
        filename = "{}.3mf".format(uuid.uuid1())
        filedir = self.determineTempDirectory()
        filepath = os.path.join(filedir, filename)
        
        Logger.log("d", "Saving temporary (and custom!) 3MF file at: {}".format(filepath))

        # Checking whether count of models == 1
        mesh_nodes = self.getSliceableNodes()
        if len(mesh_nodes) is not 1:
            Logger.log("d", "Found {} meshes!".format(["no", "too many"][len(mesh_nodes) > 1]))
            return None

        Logger.log("d", "Creating initial 3MF file")
        self.prepareInitial3mf(filepath, mesh_nodes)
        Logger.log("d", "Adding additional job info")
        self.extend3mf(filepath,
                       mesh_nodes,
                       jtype)

        if not os.path.exists(filepath):
            return None
        
        return filepath

    def replicateCuraEngineMessages(self):
        global_stack = Application.getInstance().getGlobalContainerStack()
        if not global_stack:
            return
        
        # Build messages for extruder stacks
        extruders_message = []
        for extruder_stack in global_stack.extruderList:
            extruders_message.append(self._buildExtruderMessage(extruder_stack))
        
        return {"object_lists": self._buildObjectsListsMessage(global_stack),
                "global_settings": self._buildGlobalSettingsMessage(global_stack),
                "limit_to_extruder": self._buildGlobalInheritsStackMessage(global_stack),
                "extruders": extruders_message,
                }
        
    ##  Check if a node has per object settings and ensure that they are set correctly in the message
    #   \param node Node to check.
    #   \param message object_lists message to put the per object settings in
    def _handlePerObjectSettings(self, node):
        stack = node.callDecoration("getStack")

        # Check if the node has a stack attached to it and the stack has any settings in the top container.
        if not stack:
            return

        # Check all settings for relations, so we can also calculate the correct values for dependent settings.
        top_of_stack = stack.getTop()  # Cache for efficiency.
        changed_setting_keys = top_of_stack.getAllKeys()

        # Add all relations to changed settings as well.
        for key in top_of_stack.getAllKeys():
            instance = top_of_stack.getInstance(key)
            self._addRelations(changed_setting_keys, instance.definition.relations)

        # Ensure that the engine is aware what the build extruder is.
        changed_setting_keys.add("extruder_nr")

        settings = []
        # Get values for all changed settings
        for key in changed_setting_keys:
            setting = {}
            setting["name"] = key
            extruder = int(round(float(stack.getProperty(key, "limit_to_extruder"))))

            # Check if limited to a specific extruder, but not overridden by per-object settings.
            if extruder >= 0 and key not in changed_setting_keys:
                limited_stack = ExtruderManager.getInstance().getActiveExtruderStacks()[extruder]
            else:
                limited_stack = stack

            setting["value"] = str(limited_stack.getProperty(key, "value"))
            
            settings.append(setting)
        
        return settings
    
    def _cacheAllExtruderSettings(self):
        global_stack = Application.getInstance().getGlobalContainerStack()

        # NB: keys must be strings for the string formatter
        self._all_extruders_settings = {
            "-1": self._buildReplacementTokens(global_stack)
        }
        for extruder_stack in ExtruderManager.getInstance().getActiveExtruderStacks():
            extruder_nr = extruder_stack.getProperty("extruder_nr", "value")
            self._all_extruders_settings[str(extruder_nr)] = self._buildReplacementTokens(extruder_stack)
    
    ##  Creates a dictionary of tokens to replace in g-code pieces.
    #
    #   This indicates what should be replaced in the start and end g-codes.
    #   \param stack The stack to get the settings from to replace the tokens
    #   with.
    #   \return A dictionary of replacement tokens to the values they should be
    #   replaced with.
    def _buildReplacementTokens(self, stack):
        result = {}
        for key in stack.getAllKeys():
            value = stack.getProperty(key, "value")
            result[key] = value

        result["print_bed_temperature"] = result["material_bed_temperature"] # Renamed settings.
        result["print_temperature"] = result["material_print_temperature"]
        result["travel_speed"] = result["speed_travel"]
        result["time"] = time.strftime("%H:%M:%S") #Some extra settings.
        result["date"] = time.strftime("%d-%m-%Y")
        result["day"] = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][int(time.strftime("%w"))]

        initial_extruder_stack = Application.getInstance().getExtruderManager().getUsedExtruderStacks()[0]
        initial_extruder_nr = initial_extruder_stack.getProperty("extruder_nr", "value")
        result["initial_extruder_nr"] = initial_extruder_nr

        return result

    ##  Replace setting tokens in a piece of g-code.
    #   \param value A piece of g-code to replace tokens in.
    #   \param default_extruder_nr Stack nr to use when no stack nr is specified, defaults to the global stack
    def _expandGcodeTokens(self, value, default_extruder_nr) -> str:
        if not self._all_extruders_settings:
            self._cacheAllExtruderSettings()

        try:
            # any setting can be used as a token
            fmt = GcodeStartEndFormatter(default_extruder_nr = default_extruder_nr)
            if self._all_extruders_settings is None:
                return ""
            settings = self._all_extruders_settings.copy()
            settings["default_extruder_nr"] = default_extruder_nr
            return str(fmt.format(value, **settings))
        except:
            Logger.logException("w", "Unable to do token replacement on start/end g-code")
            return str(value)

    def modifyInfillAnglesInSettingDict(self, settings):
        for key, value in settings.items():
            if key == "infill_angles":
                Logger.log("d", "Found infill_angles!")
                if type(value) is str:
                    value = eval(value)
                if len(value) is 0:
                    settings[key] = [self._poc_default_infill_direction]
                else:
                    settings[key] = [value[0]]
        
        return settings
    
    
    ##  Sends all global settings to the engine.
    #
    #   The settings are taken from the global stack. This does not include any
    #   per-extruder settings or per-object settings.
    def _buildGlobalSettingsMessage(self, stack = None):
        if not stack:
            stack = Application.getInstance().getGlobalContainerStack()
        
        if not stack:
            return
        
        if not self._all_extruders_settings:
            self._cacheAllExtruderSettings()

        if self._all_extruders_settings is None:
            return

        settings = self._all_extruders_settings["-1"].copy()

        # Pre-compute material material_bed_temp_prepend and material_print_temp_prepend
        start_gcode = settings["machine_start_gcode"]
        bed_temperature_settings = ["material_bed_temperature", "material_bed_temperature_layer_0"]
        pattern = r"\{(%s)(,\s?\w+)?\}" % "|".join(bed_temperature_settings) # match {setting} as well as {setting, extruder_nr}
        settings["material_bed_temp_prepend"] = re.search(pattern, start_gcode) == None
        print_temperature_settings = ["material_print_temperature", "material_print_temperature_layer_0", "default_material_print_temperature", "material_initial_print_temperature", "material_final_print_temperature", "material_standby_temperature"]
        pattern = r"\{(%s)(,\s?\w+)?\}" % "|".join(print_temperature_settings) # match {setting} as well as {setting, extruder_nr}
        settings["material_print_temp_prepend"] = re.search(pattern, start_gcode) == None

        # Replace the setting tokens in start and end g-code.
        # Use values from the first used extruder by default so we get the expected temperatures
        initial_extruder_stack = Application.getInstance().getExtruderManager().getUsedExtruderStacks()[0]
        initial_extruder_nr = initial_extruder_stack.getProperty("extruder_nr", "value")

        settings["machine_start_gcode"] = self._expandGcodeTokens(settings["machine_start_gcode"], initial_extruder_nr)
        settings["machine_end_gcode"] = self._expandGcodeTokens(settings["machine_end_gcode"], initial_extruder_nr)

        settings = self.modifyInfillAnglesInSettingDict(settings)

        for key, value in settings.items():
            if type(value) is not str:
                settings[key] = str(value)

        return settings

    ##  Sends all global settings to the engine.
    #
    #   The settings are taken from the global stack. This does not include any
    #   per-extruder settings or per-object settings.
    def _buildObjectsListsMessage(self, global_stack):
        scene = Application.getInstance().getController().getScene()
        
        active_buildplate = Application.getInstance().getMultiBuildPlateModel().activeBuildPlate
        
        with scene.getSceneLock():
            # Remove old layer data.
            for node in DepthFirstIterator(scene.getRoot()):
                if node.callDecoration("getLayerData") and node.callDecoration("getBuildPlateNumber") == active_buildplate:
                    # Singe we walk through all nodes in the scene, they always have a parent.
                    node.getParent().removeChild(node)
                    break

            # Get the objects in their groups to print.
            object_groups = []
            if global_stack.getProperty("print_sequence", "value") == "one_at_a_time":
                for node in OneAtATimeIterator(scene.getRoot()):
                    temp_list = []

                    # Node can't be printed, so don't bother sending it.
                    if getattr(node, "_outside_buildarea", False):
                        continue

                    # Filter on current build plate
                    build_plate_number = node.callDecoration("getBuildPlateNumber")
                    if build_plate_number is not None and build_plate_number != active_buildplate:
                        continue

                    children = node.getAllChildren()
                    children.append(node)
                    for child_node in children:
                        mesh_data = child_node.getMeshData()
                        if mesh_data and mesh_data.getVertices() is not None:
                            temp_list.append(child_node)

                    if temp_list:
                        object_groups.append(temp_list)
                    Job.yieldThread()
                if len(object_groups) == 0:
                    Logger.log("w", "No objects suitable for one at a time found, or no correct order found")
            else:
                temp_list = []
                has_printing_mesh = False
                for node in DepthFirstIterator(scene.getRoot()):
                    mesh_data = node.getMeshData()
                    if node.callDecoration("isSliceable") and mesh_data and mesh_data.getVertices() is not None:
                        is_non_printing_mesh = bool(node.callDecoration("isNonPrintingMesh"))

                        # Find a reason not to add the node
                        if node.callDecoration("getBuildPlateNumber") != active_buildplate:
                            continue
                        if getattr(node, "_outside_buildarea", False) and not is_non_printing_mesh:
                            continue

                        temp_list.append(node)
                        if not is_non_printing_mesh:
                            has_printing_mesh = True

                    Job.yieldThread()

                # If the list doesn't have any model with suitable settings then clean the list
                # otherwise CuraEngine will crash
                if not has_printing_mesh:
                    temp_list.clear()

                if temp_list:
                    object_groups.append(temp_list)
        
        extruders_enabled = {position: stack.isEnabled for position, stack in global_stack.extruders.items()}
        filtered_object_groups = []
        has_model_with_disabled_extruders = False
        associated_disabled_extruders = set()
        for group in object_groups:
            stack = global_stack
            skip_group = False
            for node in group:
                # Only check if the printing extruder is enabled for printing meshes
                is_non_printing_mesh = node.callDecoration("evaluateIsNonPrintingMesh")
                extruder_position = node.callDecoration("getActiveExtruderPosition")
                if not is_non_printing_mesh and not extruders_enabled[extruder_position]:
                    skip_group = True
                    has_model_with_disabled_extruders = True
                    associated_disabled_extruders.add(extruder_position)
            if not skip_group:
                filtered_object_groups.append(group)
        
        if has_model_with_disabled_extruders:
                associated_disabled_extruders = {str(c) for c in sorted([int(p) + 1 for p in associated_disabled_extruders])}
                self.setMessage(", ".join(associated_disabled_extruders))
                return
    
        object_lists_message = []
        for group in filtered_object_groups:
            group_message_message = {}
            parent = group[0].getParent()
            if parent is not None and parent.callDecoration("isGroup"):
                group_message_message["settings"] = self._handlePerObjectSettings(parent)
    
            group_message_message["objects"] = []
            for _object in group:
                mesh_data = object.getMeshData()
                if mesh_data is None:
                    continue
                rot_scale = _object.getWorldTransformation().getTransposed().getData()[0:3, 0:3]
                translate = _object.getWorldTransformation().getData()[:3, 3]
    
                # This effectively performs a limited form of MeshData.getTransformed that ignores normals.
                verts = mesh_data.getVertices()
                verts = verts.dot(rot_scale)
                verts += translate
    
                # Convert from Y up axes to Z up axes. Equals a 90 degree rotation.
                verts[:, [1, 2]] = verts[:, [2, 1]]
                verts[:, 1] *= -1
    
                obj = {}
                obj["id"] = id(_object)
                obj["name"] = _object.getName()
                indices = mesh_data.getIndices()
                if indices is not None:
                    flat_verts = numpy.take(verts, indices.flatten(), axis=0)
                else:
                    flat_verts = numpy.array(verts)
    
                obj["vertices"] = flat_verts.tolist()
    
                obj["settings"] = self._handlePerObjectSettings(_object)
                
                group_message_message["objects"].append(obj)
            
            object_lists_message.append(group_message_message)

        return object_lists_message

    ##  Sends for some settings which extruder they should fallback to if not
    #   set.
    #
    #   This is only set for settings that have the limit_to_extruder
    #   property.
    #
    #   \param stack The global stack with all settings, from which to read the
    #   limit_to_extruder property.
    def _buildGlobalInheritsStackMessage(self, stack):
        limit_to_extruder_message = []
        for key in stack.getAllKeys():
            extruder_position = int(round(float(stack.getProperty(key, "limit_to_extruder"))))
            if extruder_position >= 0:  # Set to a specific extruder.
                setting_extruder = {}
                setting_extruder["name"] = key
                setting_extruder["extruder"] = extruder_position
                limit_to_extruder_message.append(setting_extruder)
        return limit_to_extruder_message
            
    ##  Create extruder message from stack
    def _buildExtruderMessage(self, stack) -> dict:
        extruder_message = {}
        extruder_message["id"] = int(stack.getMetaDataEntry("position"))
        if not self._all_extruders_settings:
            self._cacheAllExtruderSettings()

        if self._all_extruders_settings is None:
            return

        extruder_nr = stack.getProperty("extruder_nr", "value")
        settings = self._all_extruders_settings[str(extruder_nr)].copy()

        # Also send the material GUID. This is a setting in fdmprinter, but we have no interface for it.
        settings["material_guid"] = stack.material.getMetaDataEntry("GUID", "")

        # Replace the setting tokens in start and end g-code.
        extruder_nr = stack.getProperty("extruder_nr", "value")
        settings["machine_extruder_start_code"] = self._expandGcodeTokens(settings["machine_extruder_start_code"], extruder_nr)
        settings["machine_extruder_end_code"] = self._expandGcodeTokens(settings["machine_extruder_end_code"], extruder_nr)

        settings = self.modifyInfillAnglesInSettingDict(settings)

        for key, value in settings.items():
            if type(value) is not str:
                settings[key] = str(value)

        extruder_message["settings"] = settings
        
        return extruder_message