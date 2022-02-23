import os
import unittest
import logging
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin

#
# LanguageTools
#

class LanguageTools(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Language Tools"
    self.parent.categories = ["Utilities"]
    self.parent.dependencies = []
    self.parent.contributors = ["Andras Lasso (PerkLab)"]
    self.parent.helpText = """
This module can build translation files and install them locally. It is useful for creating and testing translations.
See more information in the <a href="https://github.com/Slicer/SlicerLanguagePacks">extension's documentation</a>.
"""
    self.parent.acknowledgementText = """
Developed of this module was partially funded by <a href="https://chanzuckerberg.com/eoss/proposals/3d-slicer-in-my-language-internationalization-and-usability-improvements/">CZI EOSS grant</a>.
"""

#
# LanguageToolsWidget
#

class LanguageToolsWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent=None):
    """
    Called when the user opens the module the first time and the widget is initialized.
    """
    ScriptedLoadableModuleWidget.__init__(self, parent)
    VTKObservationMixin.__init__(self)  # needed for parameter node observation
    self.logic = None
    self._parameterNode = None
    self._updatingGUIFromParameterNode = False

  def setup(self):
    """
    Called when the user opens the module the first time and the widget is initialized.
    """
    ScriptedLoadableModuleWidget.setup(self)

    # Load widget from .ui file (created by Qt Designer).
    # Additional widgets can be instantiated manually and added to self.layout.
    uiWidget = slicer.util.loadUI(self.resourcePath('UI/LanguageTools.ui'))
    self.layout.addWidget(uiWidget)
    self.ui = slicer.util.childWidgetVariables(uiWidget)

    # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
    # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
    # "setMRMLScene(vtkMRMLScene*)" slot.
    uiWidget.setMRMLScene(slicer.mrmlScene)

    # Create logic class. Logic implements all computations that should be possible to run
    # in batch mode, without a graphical user interface.
    self.logic = LanguageToolsLogic()
    self.logic.logCallback = self.log

    # Connections

    # These connections ensure that whenever user changes some settings on the GUI, that is saved in the MRML scene
    # (in the selected parameter node).
    self.ui.weblateSourceRadioButton.connect("toggled(bool)", lambda toggled, source="weblate": self.setTranslationSource(source, toggled))
    self.ui.githubSourceRadioButton.connect("toggled(bool)", lambda toggled, source="github": self.setTranslationSource(source, toggled))
    self.ui.localTsFolderRadioButton.connect("toggled(bool)", lambda toggled, source="localTsFolder": self.setTranslationSource(source, toggled))

    # Buttons
    self.ui.updateButton.connect('clicked(bool)', self.onUpdateButton)
    self.ui.restartButton.connect('clicked(bool)', self.onRestartButton)

    # Make sure parameter node is initialized (needed for module reload)
    self.updateGUIFromSettings()

  def cleanup(self):
    """
    Called when the application closes and the module widget is destroyed.
    """
    pass

  def enter(self):
    """
    Called each time the user opens this module.
    """
    pass

  def exit(self):
    """
    Called each time the user opens a different module.
    """
    pass

  def setTranslationSource(self, translationSource, toggled=True):
    if not toggled:
      # ignore when radiobutton is untoggled, we just process the toggled event
      return
    self.ui.localTsFolderLabel.enabled = (translationSource == "localTsFolder")
    self.ui.localTsFolderPathLineEdit.enabled = (translationSource == "localTsFolder")
    self.ui.latestTsFileOnlyLabel.enabled = (translationSource == "localTsFolder")
    self.ui.latestTsFileOnlyCheckBox.enabled = (translationSource == "localTsFolder")
    self.ui.languagesLabel.enabled = (translationSource == "weblate")
    self.ui.languagesComboBox.enabled = (translationSource == "weblate")

  def updateGUIFromSettings(self):
    settings = slicer.app.userSettings()
    try:
      settings.beginGroup("Internationalization/LanguageTools")

      translationSource = settings.value("TranslationSource", "localTsFolder")
      self.ui.weblateSourceRadioButton.checked = (translationSource == "weblate")
      self.ui.githubSourceRadioButton.checked = (translationSource == "github")
      self.ui.localTsFolderRadioButton.checked = (translationSource == "localTsFolder")
      self.setTranslationSource(translationSource)

      languages = settings.value("UpdateLanguages", "fr-FR").split(",")
      for languageIndex in range(self.ui.languagesComboBox.count):
        selected = self.ui.languagesComboBox.itemText(languageIndex) in languages
        modelIndex = self.ui.languagesComboBox.model().index(languageIndex,0)
        self.ui.languagesComboBox.setCheckState(modelIndex, qt.Qt.Checked if selected else qt.Qt.Unchecked)

      self.ui.localTsFolderPathLineEdit.currentPath = settings.value("localTsFolderPath", "")
      self.ui.latestTsFileOnlyCheckBox.checked = settings.value("UseLatestTsFile", True)

      self.ui.lreleasePathLineEdit.currentPath = settings.value("LreleaseFilePath", "")
      self.ui.slicerVersionEdit.text = settings.value("SlicerVersion", "master")
      self.ui.weblateDownloadUrlEdit.text = settings.value("WeblateDownloadUrl", "https://hosted.weblate.org/download/3d-slicer")
      self.ui.githubRepositoryUrlEdit.text = settings.value("GitRepository", "https://github.com/Slicer/SlicerLanguageTranslations")
      
    finally:
      settings.endGroup()

    if not os.path.exists(self.ui.lreleasePathLineEdit.currentPath):
      self.ui.settingsCollapsibleButton.collapsed = False

  def updatedLanguagesListFromGUI(self):
    languages = []
    for modelIndex in self.ui.languagesComboBox.checkedIndexes():
      languages.append(self.ui.languagesComboBox.model().data(modelIndex))
    return languages

  def updateSettingsFromGUI(self):
    settings = slicer.app.userSettings()
    try:
      settings.beginGroup("Internationalization/LanguageTools")
      if self.ui.localTsFolderRadioButton.checked:
        source = "localTsFolder"
      elif self.ui.weblateSourceRadioButton.checked:
        source = "weblate"
      else:
        source = "github"
      settings.setValue("TranslationSource", source)
      settings.setValue("GithubRepository", self.ui.githubRepositoryUrlEdit.text)
      settings.setValue("SlicerVersion", self.ui.slicerVersionEdit.text)
      settings.setValue("localTsFolderPath", self.ui.localTsFolderPathLineEdit.currentPath)
      settings.setValue("UseLatestTsFile", self.ui.latestTsFileOnlyCheckBox.checked)
      settings.setValue("WeblateDownloadUrl", self.ui.weblateDownloadUrlEdit.text)
      settings.setValue("LreleaseFilePath", self.ui.lreleasePathLineEdit.currentPath)

      languages = self.updatedLanguagesListFromGUI()
      settings.setValue("UpdateLanguages", ','.join(languages))

    finally:
      settings.endGroup()

    self.ui.localTsFolderPathLineEdit.addCurrentPathToHistory()

  def onUpdateButton(self):
    """
    Run processing when user clicks "Apply" button.
    """
    with slicer.util.tryWithErrorDisplay("Update failed.", waitCursor=True):
      self.ui.statusTextEdit.clear()
      self.updateSettingsFromGUI()

      self.logic.slicerVersion = self.ui.slicerVersionEdit.text
      self.logic.lreleasePath = self.ui.lreleasePathLineEdit.currentPath

      self.logic.removeTemporaryFolder()

      if self.ui.localTsFolderRadioButton.checked:
        self.logic.copyTsFilesFromFolder(self.ui.localTsFolderPathLineEdit.currentPath, self.ui.latestTsFileOnlyCheckBox.checked)
      elif self.ui.weblateSourceRadioButton.checked:
        self.logic.downloadTsFilesFromWeblate(self.ui.weblateDownloadUrlEdit.text, self.updatedLanguagesListFromGUI())
      else:
        self.logic.downloadTsFilesFromGithub(self.ui.githubRepositoryUrlEdit.text)

      self.logic.convertTsFilesToQmFiles()
      self.logic.installQmFiles()

  def onRestartButton(self):
    slicer.util.restart()

  def log(self, message):
    self.ui.statusTextEdit.append(message)
    slicer.app.processEvents()

#
# LanguageToolsLogic
#

class LanguageToolsLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self):
    """
    Called when the logic class is instantiated. Can be used for initializing member variables.
    """
    ScriptedLoadableModuleLogic.__init__(self)
    self.slicerVersion = "master"
    self.lreleasePath = None
    self._temporaryFolder = None
    self.translationFilesFolder = None
    self.weblateComponents = [("3d-slicer", "Slicer")]
    self.gitRepositoryName = "SlicerLanguageTranslations"
    self.gitBranchName = "main"  # we store translations for all Slicer versions in the main branch
    self.logCallback = None

  def log(self, message):
    if self.logCallback:
      self.logCallback(message)

  def temporaryFolder(self):
    if not self._temporaryFolder:
      self._temporaryFolder = slicer.util.tempDirectory()
    return self._temporaryFolder

  def removeTemporaryFolder(self):
    if not self._temporaryFolder:
      return
    import shutil
    shutil.rmtree(self._temporaryFolder)
    self._temporaryFolder = None
    self.translationFilesFolder = None

  def copyTsFilesFromFolder(self, tsFolder, latestTsFileOnly):
    """Use .ts files in a local folder.
    This method requires a temporary folder that does not contain previous downloaded or extracted files.
    """

    tempFolder = self.temporaryFolder()
    self.translationFilesFolder = tempFolder

    import glob
    tsFiles = sorted(glob.glob(f"{tsFolder}/*.ts"), key=os.path.getmtime)

    if not tsFiles:
      raise ValueError("No .ts files were found in the specified location.")

    if latestTsFileOnly:
      tsFiles = [tsFiles[-1]]
      self.log(f"Use translation file: {tsFiles[0]}")

    import shutil
    import xml.etree.cElementTree as ET
    for file in tsFiles:
      tree = ET.ElementTree(file=file)
      locale = tree.getroot().attrib['language']  # such as 'zh-CN'
      baseName = os.path.basename(file).split('_')[0]
      shutil.copy(file, f"{self.translationFilesFolder}/{baseName}_{locale}.ts")

  def downloadTsFilesFromWeblate(self, downloadUrl, languages):
    """Download .ts files from Weblate.
    This method requires a temporary folder that does not contain previous downloaded or extracted files.
    """

    tempFolder = self.temporaryFolder()
    self.translationFilesFolder = tempFolder

    # Download file
    import SampleData
    dataLogic = SampleData.SampleDataLogic()

    for (component, filename) in self.weblateComponents:
      for language in languages:
        self.log(f'Download translations for {language}...')
        tsFile = dataLogic.downloadFile(f'{downloadUrl}/{component}/{language}', self.temporaryFolder(), f'{filename}_{language}.ts')

  def downloadTsFilesFromGithub(self, githubRepositoryUrl):
    """Download .ts files from a Github repository.
    This method requires a temporary folder that does not contain previous downloaded or extracted files.
    """

    tempFolder = self.temporaryFolder()

    # Download file
    import SampleData
    dataLogic = SampleData.SampleDataLogic()
    translationZipFilePath = dataLogic.downloadFile(f'{githubRepositoryUrl}/archive/refs/heads/{self.gitBranchName}.zip', self.temporaryFolder(), 'GitHubTranslations.zip')

    # Unzip file
    slicer.util.extractArchive(translationZipFilePath, tempFolder)

    # /temp.../SlicerLanguageTranslations-main/translated/master
    self.translationFilesFolder = f'{tempFolder}/{self.gitRepositoryName}-{self.gitBranchName}/translated/{self.slicerVersion}'

  def convertTsFilesToQmFiles(self):
    if not self.translationFilesFolder:
      raise ValueError("Translation files folder is not specified.")

    if (not self.lreleasePath) or (not os.path.exists(self.lreleasePath)):
      raise ValueError("lrelease tool path is not specified.")

    logging.info(f"Processing translation files in folder {self.translationFilesFolder}")
    import glob
    tsFiles = sorted(glob.glob(f"{self.translationFilesFolder}/*.ts"), key=os.path.getmtime)

    for file in tsFiles:
        lreleaseProcess = slicer.util.launchConsoleProcess([self.lreleasePath, str(file)])
        slicer.util.logProcessOutput(lreleaseProcess)

  def installQmFiles(self):
    if not self.translationFilesFolder:
      raise ValueError("Translation files folder is not specified.")

    import shutil
    from pathlib import Path
    tsFiles = Path(self.translationFilesFolder).glob('*.qm')

    applicationTranslationFolder = slicer.app.translationFolders()[0]

    # Make sure the translations folder exists
    os.makedirs(applicationTranslationFolder, exist_ok=True)

    numberOfInstalledFiles = 0
    for file in tsFiles:
      logging.debug(f"Installing translation file: {file} in {applicationTranslationFolder}")
      shutil.copy(file, applicationTranslationFolder)
      numberOfInstalledFiles += 1

    if numberOfInstalledFiles == 0:
      raise ValueError(f"No translation (qm) files were found at {self.translationFilesFolder}")
    
    self.log(f"Update successfully completed.\nInstalled {numberOfInstalledFiles} translation files in {applicationTranslationFolder}.")

#
# LanguageToolsTest
#

class LanguageToolsTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear()

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_LanguageTools1()

  def test_LanguageTools1(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests should exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """

    self.delayDisplay("Starting the test")

    logic = LanguageToolsLogic()

    import shutil
    logic.lreleasePath = shutil.which('lrelease')

    # Fallback for local testing on Windows in the install tree
    if not logic.lreleasePath:
      logic.lreleasePath = "c:/Qt/5.15.0/msvc2019_64/bin/lrelease.exe"

    logic.downloadTsFilesFromGithub("https://github.com/Slicer/SlicerLanguageTranslations")
    logic.convertTsFilesToQmFiles()
    logic.installQmFiles()

    logic.removeTemporaryFolder()

    self.delayDisplay('Test passed')
