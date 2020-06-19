import os
import json
from typing import Dict

from UM.i18n import i18nCatalog
from UM.Application import Application
from UM.Extension import Extension
from UM.Logger import Logger
from UM.PluginRegistry import PluginRegistry
from UM.Workspace.WorkspaceMetadataStorage import WorkspaceMetadataStorage

from .SmartSliceCloudConnector import SmartSliceCloudConnector

import pywim

i18n_catalog = i18nCatalog("smartslice")

class SmartSliceExtension(Extension):
    def __init__(self):
        super().__init__()

        # Separate module for cloud connection
        self.cloud = SmartSliceCloudConnector()

        #self.setMenuName(i18n_catalog.i18nc("@item:inmenu", "Smart Slice"))

        # About Dialog
        self._about_dialog = None
        self.addMenuItem(i18n_catalog.i18nc("@item:inmenu", "About"), self._openAboutDialog)

        # Login Window
        self._login_dialog = None
        #self.addMenuItem(i18n_catalog.i18n("Login"),
        #                 self._openLoginDialog)

        # Connection to the file writer on File->Save
        self._outputManager = PluginRegistry.getInstance().getPluginObject("LocalFileOutputDevice").getOutputDeviceManager()
        self._outputManager.writeStarted.connect(self._saveState)

        # Data storage location for workspaces - this is where we store our data for saving to the Cura project
        self._storage = Application.getInstance().getWorkspaceMetadataStorage()

        # We use the signal from the cloud connector to always update the plugin metadeta after results are generated
        # _saveState is also called when the user actually saves a project
        self.cloud.saveSmartSliceJob.connect(self._saveState)

    def _openLoginDialog(self):
        if not self._login_dialog:
            self._login_dialog = self._createQmlDialog("SmartSliceCloudLogin.qml")
        self._login_dialog.show()

    def _openAboutDialog(self):
        if not self._about_dialog:
            self._about_dialog = self._createQmlDialog("SmartSliceAbout.qml", vars={"aboutText": self._aboutText()})
        self._about_dialog.show()

    def _closeAboutDialog(self):
        if not self._about_dialog:
            self._about_dialog.close()

    def _createQmlDialog(self, dialog_qml, directory = None, vars = None):
        if directory is None:
            directory = PluginRegistry.getInstance().getPluginPath(self.getPluginId())

        mainApp = Application.getInstance()

        return mainApp.createQmlComponent(os.path.join(directory, dialog_qml), vars)

    def _aboutText(self):
        about = 'Smart Slice for Cura\n'

        plugin_info = self._getMetadata()

        if plugin_info:
            about += 'Version: {}'.format(plugin_info['version'])

        return about

    def _saveState(self, output_object=None):
        plugin_info = self._getMetadata()

        # Build the Smart Slice job. We want to always build in case something has changed
        job = self.cloud.smartSliceJobHandle.buildJobFor3mf()

        cloudJob = self.cloud.cloudJob
        if (cloudJob):
            job.type = cloudJob.job_type

        # Place the job in the metadata under our plugin ID
        self._storage.setEntryToStore(plugin_id = plugin_info['id'], key = 'job', data = job.to_dict())

        # Need to do some checks to see if we've stored the results for the active job
        if cloudJob and cloudJob.getResult() and not cloudJob.saved:
            self._storage.setEntryToStore(plugin_id = plugin_info['id'], key = 'results', data = cloudJob.getResult().to_dict())
            cloudJob.saved = True
        elif job.type == pywim.smartslice.job.JobType.validation and (not cloudJob or not cloudJob.getResult()):
            self._storage.setEntryToStore(plugin_id = plugin_info['id'], key = 'results', data = None)
        else:
            pass

        return True

    def _getMetadata(self) -> Dict[str, str]:
        try:
            plugin_json_path = os.path.dirname(os.path.abspath(__file__))
            plugin_json_path = os.path.join(plugin_json_path, 'plugin.json')
            with open(plugin_json_path, 'r') as f:
                plugin_info = json.load(f)
            return plugin_info
        except:
            return None


