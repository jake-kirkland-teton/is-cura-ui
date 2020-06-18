import time
import os
import io
import uuid
import json
import tempfile
import math
from pathlib import Path

import numpy

import pywim  # @UnresolvedImport

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import QTime, QUrl, QObject
from PyQt5.QtQml import qmlRegisterSingletonType

from UM.i18n import i18nCatalog
from UM.Application import Application
from UM.Job import Job
from UM.Logger import Logger
from UM.Math.Matrix import Matrix
from UM.Mesh.MeshBuilder import MeshBuilder
from UM.Message import Message
from UM.Operations.AddSceneNodeOperation import AddSceneNodeOperation
from UM.Operations.GroupedOperation import GroupedOperation
from UM.PluginRegistry import PluginRegistry
from UM.Scene.SceneNode import SceneNode
from UM.Settings.SettingInstance import SettingInstance
from UM.Signal import Signal

from cura.Operations.SetParentOperation import SetParentOperation
from cura.Scene.BuildPlateDecorator import BuildPlateDecorator
from cura.Scene.CuraSceneNode import CuraSceneNode
from cura.Scene.SliceableObjectDecorator import SliceableObjectDecorator
from cura.Settings.ExtruderStack import ExtruderStack
from cura.UI.PrintInformation import PrintInformation

from .SmartSliceCloudProxy import SmartSliceCloudStatus
from .SmartSliceCloudProxy import SmartSliceCloudProxy
from .SmartSlicePropertyHandler import SmartSlicePropertyHandler
from .SmartSliceJobHandler import SmartSliceJobHandler

from .requirements_tool.SmartSliceRequirements import SmartSliceRequirements
from .select_tool.SmartSliceSelectTool import SmartSliceSelectTool

from .utils import getPrintableNodes
from .utils import getNodeActiveExtruder

i18n_catalog = i18nCatalog("smartslice")

class SmartSliceCloudJob(Job):
    # This job is responsible for uploading the backup file to cloud storage.
    # As it can take longer than some other tasks, we schedule this using a Cura Job.

    class JobException(Exception):
        def __init__(self, problem : str):
            super().__init__(problem)
            self.problem = problem

    def __init__(self, connector) -> None:
        super().__init__()
        self.connector = connector
        self.job_type = None
        self._id = 0
        self._saved = False

        self.canceled = False

        self._job_status = None
        self._wait_time = 1.0

        # get connection settings from preferences
        preferences = Application.getInstance().getPreferences()

        protocol = preferences.getValue(self.connector.http_protocol_preference)
        hostname = preferences.getValue(self.connector.http_hostname_preference)
        port = preferences.getValue(self.connector.http_port_preference)
        if type(port) is not int:
            port = int(port)

        self._client = pywim.http.thor.Client2020POC(
            protocol=protocol,
            hostname=hostname,
            port=port
        )

        Logger.log("d", "SmartSlice HTTP Client: {}".format(self._client.address))

    @property
    def job_status(self):
        return self._job_status

    @job_status.setter
    def job_status(self, value):
        if value is not self._job_status:
            self._job_status = value
            Logger.log("d", "Status changed: {}".format(self.job_status))

    @property
    def saved(self):
        return self._saved

    @saved.setter
    def saved(self, value):
        if self._saved != value:
            self._saved = value

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
    # - job_type: Job type to be sent. Can be either:
    #             > pywim.smartslice.job.JobType.validation
    #             > pywim.smartslice.job.JobType.optimization
    def prepareJob(self) -> io.BytesIO:
        # Using tempfile module to probe for a temporary file path
        # TODO: We can do this more elegant of course, too.

        # Checking whether count of models == 1
        mesh_nodes = getPrintableNodes()
        if len(mesh_nodes) is not 1:
            Logger.log("d", "Found {} meshes!".format(["no", "too many"][len(mesh_nodes) > 1]))
            return None

        Logger.log("d", "Writing 3MF to memory")
        job = self.connector.smartSliceJobHandle.buildJobFor3mf(self.connector.activeMachine.getName())

        if not job:
            Logger.log("d", "Error building the Smart Slice job for 3MF")
            return None

        job.type = self.job_type

        stream = io.BytesIO()
        SmartSliceJobHandler.write3mf(stream, mesh_nodes, job)

        return stream

    def processCloudJob(self, stream: io.BytesIO):

        # Submit the 3MF data for a new task
        task = self._client.submit.post(stream)
        Logger.log("d", "Status after posting: {}".format(task.status))

        # While the task status is not finished or failed continue to periodically
        # check the status. This is a naive way of waiting, since this could take
        # a while (minutes).
        while task.status not in (pywim.http.thor.TaskStatus.failed,
                                  pywim.http.thor.TaskStatus.finished
                                  ) and not self.canceled:
            self.job_status = task.status

            time.sleep(self._wait_time)
            task = self._client.status.get(id=task.id)

        if not self.canceled:
            self.connector.propertyHandler._cancelChanges = False

            if task.status == pywim.http.thor.TaskStatus.failed:
                error_message = Message()
                error_message.setTitle("Smart Slice Solver")
                error_message.setText(i18n_catalog.i18nc("@info:status", "Error while processing the job:\n{}".format(task.error)))
                error_message.show()
                self.connector.cancelCurrentJob()

                Logger.log("e", "An error occured while sending and receiving cloud job: {}".format(task.error))
                self.connector.propertyHandler._cancelChanges = False
                return None
            elif task.status == pywim.http.thor.TaskStatus.finished:
                # Get the task again, but this time with the results included
                task = self._client.result.get(id=task.id)
                return task
            else:
                error_message = Message()
                error_message.setTitle("Smart Slice Solver")
                error_message.setText(i18n_catalog.i18nc("@info:status", "Unexpected status occured:\n{}".format(task.error)))
                error_message.show()
                self.connector.cancelCurrentJob()

                Logger.log("e", "An unexpected status occured while sending and receiving cloud job: {}".format(task.status))
                self.connector.propertyHandler._cancelChanges = False
                return None
        else:
            notification_message = Message()
            notification_message.setTitle("Smart Slice")
            notification_message.setText(i18n_catalog.i18nc("@info:status", "Job has been canceled!".format(task.error)))
            notification_message.show()
            self.connector.cancelCurrentJob()

    def run(self) -> None:
        if not self.job_type:
            error_message = Message()
            error_message.setTitle("Smart Slice")
            error_message.setText(i18n_catalog.i18nc("@info:status", "Job type not set for processing:\nDon't know what to do!"))
            error_message.show()
            self.connector.cancelCurrentJob()

        Job.yieldThread()  # Should allow the UI to update earlier

        try:
            job = self.prepareJob()
            Logger.log("i", "Smart Slice job prepared: {}".format(job))
        except SmartSliceCloudJob.JobException as exc:
            Logger.log("w", "Smart Slice job cannot be prepared: {}".format(exc.problem))

            self.setError(exc)
            Message(
                title='Smart Slice',
                text=i18n_catalog.i18nc("@info:status", exc.problem)
            ).show()

            return

        task = self.processCloudJob(job)

        try:
            os.remove(job)
        except:
            Logger.log("w", "Unable to remove temporary 3MF {}".format(job))

        if task and task.result and len(task.result.analyses) > 0:
            self._result = task.result

class SmartSliceCloudVerificationJob(SmartSliceCloudJob):

    def __init__(self, connector) -> None:
        super().__init__(connector)

        self.job_type = pywim.smartslice.job.JobType.validation


class SmartSliceCloudOptimizeJob(SmartSliceCloudVerificationJob):

    def __init__(self, connector) -> None:
        super().__init__(connector)

        self.job_type = pywim.smartslice.job.JobType.optimization

class SmartSliceCloudConnector(QObject):
    http_protocol_preference = "smartslice/http_protocol"
    http_hostname_preference = "smartslice/http_hostname"
    http_port_preference = "smartslice/http_port"
    http_token_preference = "smartslice/token"

    debug_save_smartslice_package_preference = "smartslice/debug_save_smartslice_package"
    debug_save_smartslice_package_location = "smartslice/debug_save_smartslice_package_location"

    def __init__(self):
        super().__init__()

        # Variables
        self._job = None
        self._jobs = {}
        self._current_job = 0
        self._jobs[self._current_job] = None

        # Proxy
        #General
        self._proxy = SmartSliceCloudProxy()
        self._proxy.sliceButtonClicked.connect(self.onSliceButtonClicked)
        self._proxy.secondaryButtonClicked.connect(self.onSecondaryButtonClicked)

        # Application stuff
        self.app_preferences = Application.getInstance().getPreferences()
        self.app_preferences.addPreference(self.http_protocol_preference, "https")
        self.app_preferences.addPreference(self.http_hostname_preference, "api-20.fea.cloud")
        self.app_preferences.addPreference(self.http_port_preference, 443)
        self.app_preferences.addPreference(self.http_token_preference, "")

        # Debug stuff
        self.app_preferences.addPreference(self.debug_save_smartslice_package_preference, False)
        default_save_smartslice_package_location = str(Path.home())
        self.app_preferences.addPreference(self.debug_save_smartslice_package_location, default_save_smartslice_package_location)
        self.debug_save_smartslice_package_message = None

        # Executing a set of function when some activitiy has changed
        Application.getInstance().activityChanged.connect(self._onApplicationActivityChanged)

        #  Machines / Extruders
        self.activeMachine = None
        self.propertyHandler = None # SmartSlicePropertyHandler

        Application.getInstance().engineCreatedSignal.connect(self._onEngineCreated)

        self._confirmDialog = []
        self.confirming = False

    onSmartSlicePrepared = pyqtSignal()

    @property
    def cloudJob(self):
        return self._jobs[self._current_job]

    def cancelCurrentJob(self):
        if self._jobs[self._current_job] is not None:
            self._jobs[self._current_job].cancel()
            self._jobs[self._current_job].canceled = True
            self._jobs[self._current_job] = None
            self.updateStatus()

    def _onSaveDebugPackage(self, messageId: str, actionId: str) -> None:
        dummy_job = SmartSliceCloudVerificationJob(self)
        if self.status == SmartSliceCloudStatus.ReadyToVerify:
            dummy_job.job_type = pywim.smartslice.job.JobType.validation
        elif self.status in SmartSliceCloudStatus.optimizable():
            dummy_job.job_type = pywim.smartslice.job.JobType.optimization
        else:
            Logger.log("e", "DEBUG: This is not a defined state. Provide all input to create the debug package.")
            return

        jobname = Application.getInstance().getPrintInformation().jobName
        debug_filename = "{}_smartslice.3mf".format(jobname)
        debug_filedir = self.app_preferences.getValue(self.debug_save_smartslice_package_location)
        dummy_job = dummy_job.prepareJob()

        # Save the stream
        filepath = os.path.join(debug_filedir, debug_filename)
        with open(filepath, 'wb') as f:
            f.write(dummy_job.getbuffer())

    def getProxy(self, engine, script_engine):
        return self._proxy

    def _onEngineCreated(self):
        qmlRegisterSingletonType(
            SmartSliceCloudProxy,
            "SmartSlice",
            1, 0,
            "Cloud",
            self.getProxy
        )

        self.activeMachine = Application.getInstance().getMachineManager().activeMachine
        self.propertyHandler = SmartSlicePropertyHandler(self)

        self.onSmartSlicePrepared.emit()
        self.propertyHandler.cacheChanges() # Setup Cache

        Application.getInstance().getMachineManager().printerConnectedStatusChanged.connect(self._refreshMachine)

        if self.app_preferences.getValue(self.debug_save_smartslice_package_preference):
            self.debug_save_smartslice_package_message = Message(
                title="[DEBUG] SmartSlicePlugin",
                text= "Click on the button below to generate a debug package",
                lifetime= 0,
            )
            self.debug_save_smartslice_package_message.addAction("", i18n_catalog.i18nc("@action", "Save package"), "", "")
            self.debug_save_smartslice_package_message.actionTriggered.connect(self._onSaveDebugPackage)
            self.debug_save_smartslice_package_message.show()

    def _refreshMachine(self):
        self.activeMachine = Application.getInstance().getMachineManager().activeMachine

    def updateSliceWidget(self):
        if self.status is SmartSliceCloudStatus.Errors:
            self._proxy.sliceStatus = ""
            self._proxy.sliceHint = ""
            self._proxy.sliceButtonText = "Validate"
            self._proxy.sliceButtonEnabled = False
            self._proxy.sliceButtonVisible = True
            self._proxy.sliceButtonFillWidth = True
            self._proxy.secondaryButtonVisible = False
            self._proxy.sliceInfoOpen = False
        elif self.status is SmartSliceCloudStatus.Cancelling:
            self._proxy.sliceStatus = ""
            self._proxy.sliceHint = ""
            self._proxy.sliceButtonText = "Cancelling"
            self._proxy.sliceButtonEnabled = False
            self._proxy.sliceButtonVisible = True
            self._proxy.sliceButtonFillWidth = True
            self._proxy.secondaryButtonVisible = False
            self._proxy.sliceInfoOpen = False
        elif self.status is SmartSliceCloudStatus.ReadyToVerify:
            self._proxy.sliceStatus = ""
            self._proxy.sliceHint = ""
            self._proxy.sliceButtonText = "Validate"
            self._proxy.sliceButtonEnabled = True
            self._proxy.sliceButtonVisible = True
            self._proxy.sliceButtonFillWidth = True
            self._proxy.secondaryButtonVisible = False
            self._proxy.sliceInfoOpen = False
        elif self.status is SmartSliceCloudStatus.BusyValidating:
            self._proxy.sliceStatus = "Validating requirements..."
            self._proxy.sliceHint = ""
            self._proxy.secondaryButtonText = "Cancel"
            self._proxy.sliceButtonVisible = False
            self._proxy.secondaryButtonVisible = True
            self._proxy.secondaryButtonFillWidth = True
            self._proxy.sliceInfoOpen = False
        elif self.status is SmartSliceCloudStatus.Underdimensioned:
            self._proxy.sliceStatus = "Requirements not met!"
            self._proxy.sliceHint = "Optimize to meet requirements?"
            self._proxy.sliceButtonText = "Optimize"
            self._proxy.secondaryButtonText = "Preview"
            self._proxy.sliceButtonEnabled = True
            self._proxy.sliceButtonVisible = True
            self._proxy.sliceButtonFillWidth = False
            self._proxy.secondaryButtonVisible = True
            self._proxy.secondaryButtonFillWidth = False
            self._proxy.sliceInfoOpen = True
        elif self.status is SmartSliceCloudStatus.Overdimensioned:
            self._proxy.sliceStatus = "Part appears overdesigned"
            self._proxy.sliceHint = "Optimize to reduce material?"
            self._proxy.sliceButtonText = "Optimize"
            self._proxy.secondaryButtonText = "Preview"
            self._proxy.sliceButtonEnabled = True
            self._proxy.sliceButtonVisible = True
            self._proxy.sliceButtonFillWidth = False
            self._proxy.secondaryButtonVisible = True
            self._proxy.secondaryButtonFillWidth = False
            self._proxy.sliceInfoOpen = True
        elif self.status is SmartSliceCloudStatus.BusyOptimizing:
            self._proxy.sliceStatus = "Optimizing..."
            self._proxy.sliceHint = ""
            self._proxy.secondaryButtonText = "Cancel"
            self._proxy.sliceButtonVisible = False
            self._proxy.secondaryButtonVisible = True
            self._proxy.secondaryButtonFillWidth = True
            self._proxy.sliceInfoOpen = False
        elif self.status is SmartSliceCloudStatus.Optimized:
            self._proxy.sliceStatus = ""
            self._proxy.sliceHint = ""
            self._proxy.secondaryButtonText = "Preview"
            self._proxy.sliceButtonVisible = False
            self._proxy.secondaryButtonVisible = True
            self._proxy.secondaryButtonFillWidth = True
            self._proxy.sliceInfoOpen = True
        else:
            self._proxy.sliceStatus = "Unknown status"
            self._proxy.sliceHint = "Sorry, something went wrong!"
            self._proxy.sliceButtonText = "..."
            self._proxy.sliceButtonEnabled = False
            self._proxy.sliceButtonVisible = True
            self._proxy.secondaryButtonVisible = False
            self._proxy.secondaryButtonFillWidth = False
            self._proxy.sliceInfoOpen = False

        # Setting icon path
        stage_path = PluginRegistry.getInstance().getPluginPath("SmartSlicePlugin")
        stage_images_path = os.path.join(stage_path, "stage", "images")
        icon_done_green = os.path.join(stage_images_path, "done_green.png")
        icon_error_red = os.path.join(stage_images_path, "error_red.png")
        icon_warning_yellow = os.path.join(stage_images_path, "warning_yellow.png")
        current_icon = icon_done_green
        if self.status is SmartSliceCloudStatus.Overdimensioned:
            current_icon = icon_warning_yellow
        elif self.status is SmartSliceCloudStatus.Underdimensioned:
            current_icon = icon_error_red
        current_icon = QUrl.fromLocalFile(current_icon)
        self._proxy.sliceIconImage = current_icon

        # Setting icon visibiltiy
        if self.status in (SmartSliceCloudStatus.Optimized,) + SmartSliceCloudStatus.optimizable():
            self._proxy.sliceIconVisible = True
        else:
            self._proxy.sliceIconVisible = False

        self._proxy.updateColorUI()


    @property
    def status(self):
        return self._proxy.sliceStatusEnum

    @status.setter
    def status(self, value):
        Logger.log("d", "Setting status: {} -> {}".format(self._proxy.sliceStatusEnum, value))
        if self._proxy.sliceStatusEnum is not value:
            self._proxy.sliceStatusEnum = value
        self.updateSliceWidget()

    @property
    def token(self):
        return Application.getInstance().getPreferences().getValue(self.token_preference)

    @token.setter
    def token(self, value):
        Application.getInstance().getPreferences().setValue(self.token_preference, value)

    def login(self):
        # username = self._proxy.loginName()
        # password = self._proxy.loginPassword()

        if True:
            self.token = "123456789qwertz"
            return True
        else:
            self.token = ""
            return False

    def _onApplicationActivityChanged(self):
        printable_nodes_count = len(getPrintableNodes())

        sel_tool = SmartSliceSelectTool.getInstance()

        if printable_nodes_count != 1 or len(self._proxy.errors) > 0:
            self.status = SmartSliceCloudStatus.Errors

    def _onJobFinished(self, job):
        if self._jobs[self._current_job] is None or self._jobs[self._current_job].canceled:
            Logger.log("d", "Smart Slice Job was Cancelled")
            return

        if self._jobs[self._current_job].hasError():
            self.updateStatus()
            Logger.logException("e", str(self._jobs[self._current_job].getError()))
            Message(
                title='Smart Slice job unexpectedly failed',
                text=str(error)
            ).show()
            return

        self.propertyHandler._propertiesChanged = []
        self._proxy.shouldRaiseConfirmation = False

        if self._jobs[self._current_job].getResults():
            self._process_analysis_result()
            if self._jobs[self._current_job].job_type == pywim.smartslice.job.JobType.optimization:
                self.status = SmartSliceCloudStatus.Optimized
            else:
                self.prepareOptimization()
        else:
            if self.status != SmartSliceCloudStatus.ReadyToVerify and self.status != SmartSliceCloudStatus.Errors:
                self.prepareOptimization() # Double Check Requirements
                Message(
                    title='SmartSlice',
                    text=i18n_catalog.i18nc("@info:status", "SmartSlice was unable to find a solution")
                ).show()

    def _process_analysis_result(self):
        # TODO: We need a per node solution here as soon as we want to analysis multiple models.
        our_only_node =  getPrintableNodes()[0]

        job = self._jobs[self._current_job]
        analysis = job.getResult.analyses[0]

        active_extruder = getNodeActiveExtruder(our_only_node)

        if job.job_type == pywim.smartslice.job.JobType.optimization and active_extruder:
            # TODO - Move this into a common class or function to apply an am.Config to GlobalStack/ExtruderStack
            if analysis.print_config.infill:
                infill_density = analysis.print_config.infill.density
                infill_pattern = analysis.print_config.infill.pattern

                if infill_pattern is None or infill_pattern == pywim.am.InfillType.unknown:
                    infill_pattern = pywim.am.InfillType.grid

                infill_pattern_name = SmartSliceJobHandler.INFILL_SMARTSLICE_CURA[infill_pattern]

                if infill_density:
                    Logger.log("d", "Update extruder infill density to {}".format(infill_density))
                    active_extruder.setProperty("infill_sparse_density", "value", infill_density, set_from_cache=True)
                    active_extruder.setProperty("infill_pattern", "value", infill_pattern_name, set_from_cache=True)
                    Application.getInstance().getMachineManager().forceUpdateAllSettings()

        # MODIFIER MESHES STUFF
        #our_only_node_stack = our_only_node.callDecoration("getStack")
        for modifier_mesh in analysis.modifier_meshes:
            # Building the scene node
            modifier_mesh_node = CuraSceneNode()
            modifier_mesh_node.setName("SmartSliceMeshModifier")
            modifier_mesh_node.setSelectable(True)
            modifier_mesh_node.setCalculateBoundingBox(True)

            # Building the mesh

            # # Preparing the data from pywim for MeshBuilder
            modifier_mesh_vertices = [[v.x, v.y, v.z] for v in modifier_mesh.vertices ]
            modifier_mesh_indices = [[triangle.v1, triangle.v2, triangle.v3] for triangle in modifier_mesh.triangles]

            # # Doing the actual build
            modifier_mesh_data = MeshBuilder()
            modifier_mesh_data.setVertices(numpy.asarray(modifier_mesh_vertices, dtype=numpy.float32))
            modifier_mesh_data.setIndices(numpy.asarray(modifier_mesh_indices, dtype=numpy.int32))
            modifier_mesh_data.calculateNormals()

            modifier_mesh_node.setMeshData(modifier_mesh_data.build())
            modifier_mesh_node.calculateBoundingBoxMesh()

            active_build_plate = Application.getInstance().getMultiBuildPlateModel().activeBuildPlate
            modifier_mesh_node.addDecorator(BuildPlateDecorator(active_build_plate))
            modifier_mesh_node.addDecorator(SliceableObjectDecorator())

            stack = modifier_mesh_node.callDecoration("getStack")
            settings = stack.getTop()

            modifier_mesh_node_infill_pattern = SmartSliceJobHandler.INFILL_SMARTSLICE_CURA[modifier_mesh.print_config.infill.pattern]
            definition_dict = {
                "infill_mesh" : True,
                "infill_pattern" : modifier_mesh_node_infill_pattern,
                "infill_sparse_density": modifier_mesh.print_config.infill.density,
                }
            Logger.log("d", "definition_dict: {}".format(definition_dict))

            for key, value in definition_dict.items():
                definition = stack.getSettingDefinition(key)
                new_instance = SettingInstance(definition, settings)
                new_instance.setProperty("value", value)

                new_instance.resetState()  # Ensure that the state is not seen as a user state.
                settings.addInstance(new_instance)

            op = GroupedOperation()
            # First add node to the scene at the correct position/scale, before parenting, so the eraser mesh does not get scaled with the parent
            op.addOperation(AddSceneNodeOperation(
                modifier_mesh_node,
                Application.getInstance().getController().getScene().getRoot()
            ))
            op.addOperation(SetParentOperation(modifier_mesh_node, our_only_node))
            op.push()

            # Use the data from the SmartSlice engine to translate / rotate / scale the mod mesh
            modifier_mesh_transform_matrix = Matrix(modifier_mesh.transform)
            modifier_mesh_node.setTransformation(modifier_mesh_transform_matrix)

            Application.getInstance().getController().getScene().sceneChanged.emit(modifier_mesh_node)

        self._proxy.resultSafetyFactor = analysis.structural.min_safety_factor
        self._proxy.resultMaximalDisplacement = analysis.structural.max_displacement

        qprint_time = QTime(0, 0, 0, 0)
        qprint_time = qprint_time.addSecs(analysis.print_time)
        self._proxy.resultTimeTotal = qprint_time

        # TODO: Reactivate the block as soon as we have the single print times again!
        #self._proxy.resultTimeInfill = QTime(1, 0, 0, 0)
        #self._proxy.resultTimeInnerWalls = QTime(0, 20, 0, 0)
        #self._proxy.resultTimeOuterWalls = QTime(0, 15, 0, 0)
        #self._proxy.resultTimeRetractions = QTime(0, 5, 0, 0)
        #self._proxy.resultTimeSkin = QTime(0, 10, 0, 0)
        #self._proxy.resultTimeSkirt = QTime(0, 1, 0, 0)
        #self._proxy.resultTimeTravel = QTime(0, 30, 0, 0)

        if len(analysis.extruders) == 0:
            # This shouldn't happen
            material_volume = [0.0]
        else:
            material_volume = [analysis.extruders[0].material_volume]

        material_extra_info = self._calculateAdditionalMaterialInfo(material_volume)
        Logger.log("d", "material_extra_info: {}".format(material_extra_info))

        # for pos in len(material_volume):
        pos = 0
        self._proxy.materialLength = material_extra_info[0][pos]
        self._proxy.materialWeight = material_extra_info[1][pos]
        self._proxy.materialCost = material_extra_info[2][pos]
        # Below is commented out because we don't necessarily need it right now.
        # We aren't sending multiple materials to optimize, so the material here
        # won't change. And this assignment causes the "Lose Validation Results"
        # pop-up to show.
        #self._proxy.materialName = material_extra_info[3][pos]

    def updateStatus(self):
        job, self._proxy.errors = self.smartSliceJobHandle.checkJob()

        if len(self._proxy.errors) > 0 or job is None:
            self.status = SmartSliceCloudStatus.Errors
        elif self.status == SmartSliceCloudStatus.Errors or self.status == SmartSliceCloudStatus.Cancelling:
            self.status = SmartSliceCloudStatus.ReadyToVerify

        Application.getInstance().activityChanged.emit()

    def doVerfication(self):
        #  Check if model has an existing modifier mesh
        #    and ask user if they would like to proceed if so
        if self.propertyHandler.hasModMesh():
            self.propertyHandler.askToRemoveModMesh()
        else:
            self.status = SmartSliceCloudStatus.BusyValidating

            self.propertyHandler._cancelChanges = False
            self._current_job += 1
            self._jobs[self._current_job] = SmartSliceCloudVerificationJob(self)
            self._jobs[self._current_job]._id = self._current_job
            self._jobs[self._current_job].finished.connect(self._onJobFinished)
            self._jobs[self._current_job].start()

    """
      prepareOptimization()
        Convenience function for updating the cloud status outside of Validation/Optimization Jobs
    """
    def prepareOptimization(self):
        #  Check if status has changed form the change
        req_tool = SmartSliceRequirements.getInstance()
        if req_tool.maxDisplacement > self._proxy.resultMaximalDisplacement and (req_tool.targetSafetyFactor < self._proxy.resultSafetyFactor):
            self.status = SmartSliceCloudStatus.Overdimensioned
        elif req_tool.maxDisplacement <= self._proxy.resultMaximalDisplacement or (req_tool.targetSafetyFactor >= self._proxy.resultSafetyFactor):
            self.status = SmartSliceCloudStatus.Underdimensioned
        else:
            self.status = SmartSliceCloudStatus.Optimized
        self.updateSliceWidget()

    def doOptimization(self):
        self.status = SmartSliceCloudStatus.BusyOptimizing

        self.propertyHandler._cancelChanges = False
        self._current_job += 1
        self._jobs[self._current_job] = SmartSliceCloudOptimizeJob(self)
        self._jobs[self._current_job]._id = self._current_job
        self._jobs[self._current_job].finished.connect(self._onJobFinished)
        self._jobs[self._current_job].start()

    '''
      Primary Button Actions:
        * Validate
        * Optimize
        * Slice
    '''
    def onSliceButtonClicked(self):
        if not self._jobs[self._current_job]:
            if self.status is SmartSliceCloudStatus.ReadyToVerify:
                self.doVerfication()
            elif self.status in SmartSliceCloudStatus.optimizable():
                self.doOptimization()
            elif self.status is SmartSliceCloudStatus.Optimized:
                Application.getInstance().getController().setActiveStage("PreviewStage")
        else:
            self._jobs[self._current_job].cancel()
            self._jobs[self._current_job] = None

    '''
      Secondary Button Actions:
        * Cancel  (Validating / Optimizing)
        * Preview
    '''
    def onSecondaryButtonClicked(self):
        if self._jobs[self._current_job] is not None:
            if self.status is SmartSliceCloudStatus.BusyOptimizing:
                req_tool = SmartSliceRequirements.getInstance()
                #
                #  CANCEL SMART SLICE JOB HERE
                #    Any connection to AWS server should be severed here
                #
                self._jobs[self._current_job].canceled = True
                self._jobs[self._current_job] = None
                if req_tool.targetSafetyFactor < self._proxy.resultSafetyFactor and \
                   req_tool.maxDisplacement > self._proxy.resultMaximalDisplacement:
                    self.status = SmartSliceCloudStatus.Overdimensioned
                else:
                    self.status = SmartSliceCloudStatus.Underdimensioned
                Application.getInstance().activityChanged.emit()
            elif self.status is SmartSliceCloudStatus.BusyValidating:
                #
                #  CANCEL SMART SLICE JOB HERE
                #    Any connection to AWS server should be severed here
                #
                self._jobs[self._current_job].canceled = True
                self._jobs[self._current_job] = None
                self.status = SmartSliceCloudStatus.Cancelling
                self.smartSliceJobHandle.checkJob()
                self.cancelCurrentJob()
        else:
            Application.getInstance().getController().setActiveStage("PreviewStage")

    # Mainly taken from : {Cura}/cura/UI/PrintInformation.py@_calculateInformation
    def _calculateAdditionalMaterialInfo(self, _material_volume):
        global_stack = Application.getInstance().getGlobalContainerStack()
        if global_stack is None:
            return

        _material_lengths = []
        _material_weights = []
        _material_costs = []
        _material_names = []

        material_preference_values = json.loads(Application.getInstance().getPreferences().getValue("cura/material_settings"))

        Logger.log("d", "global_stack.extruderList: {}".format(global_stack.extruderList))

        for extruder_stack in global_stack.extruderList:
            position = extruder_stack.position
            if type(position) is not int:
                position = int(position)
            if position >= len(_material_volume):
                continue
            amount = _material_volume[position]
            # Find the right extruder stack. As the list isn't sorted because it's a annoying generator, we do some
            # list comprehension filtering to solve this for us.
            density = extruder_stack.getMetaDataEntry("properties", {}).get("density", 0)
            material = extruder_stack.material
            radius = extruder_stack.getProperty("material_diameter", "value") / 2

            weight = float(amount) * float(density) / 1000
            cost = 0.

            material_guid = material.getMetaDataEntry("GUID")
            material_name = material.getName()

            if material_guid in material_preference_values:
                material_values = material_preference_values[material_guid]

                if material_values and "spool_weight" in material_values:
                    weight_per_spool = float(material_values["spool_weight"])
                else:
                    weight_per_spool = float(extruder_stack.getMetaDataEntry("properties", {}).get("weight", 0))

                cost_per_spool = float(material_values["spool_cost"] if material_values and "spool_cost" in material_values else 0)

                if weight_per_spool != 0:
                    cost = cost_per_spool * weight / weight_per_spool
                else:
                    cost = 0

            # Material amount is sent as an amount of mm^3, so calculate length from that
            if radius != 0:
                length = round((amount / (math.pi * radius ** 2)) / 1000, 2)
            else:
                length = 0

            _material_weights.append(weight)
            _material_lengths.append(length)
            _material_costs.append(cost)
            _material_names.append(material_name)

        return _material_lengths, _material_weights, _material_costs, _material_names
