#!/usr/bin/env python
# -*- coding: utf-8 -*-

import copy
import pickle
import platform
import shutil
from inspect import signature

import requests
from anki.hooks import wrap
from anki.lang import _
from aqt import mw
from aqt.editor import Editor, EditorWebView
from aqt.qt import *
from bs4 import BeautifulSoup
from aqt import gui_hooks
from aqt.qt import (
    QApplication,
    QVBoxLayout,
    QLineEdit,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QWidget,
    QComboBox,
    QGuiApplication,
    Qt,
)
addon_id = '1214357311'

# Get log file
# 1214357311 is ImageResizer's addon ID
irFolder = os.path.join(mw.pm.addonFolder(), addon_id, 'user_files')

# if ImageResizer's folder doesn't exist, create one
if not os.path.exists(irFolder):
    os.makedirs(irFolder)


# settings main window, Qt won't show the window if
# we don't assign a global variable to Settings()


def will_process_mime_handler(mime: QMimeData, editor_web_view: EditorWebView, internal: bool, extended: bool, drop_event: bool):
    if Setup.config['auto'] is False:
        return mime

    if containsImage(mime):
        # Resize the image, then pass to Anki
        return checkAndResize(mime)

    return mime


class Setup(object):
    """Do all the necessary initialization when anki
       loads the addon
    """

    config = dict(
        isUpScalingDisabled=False,
        auto=True,
        keys=dict(Ctrl=True, Alt=False,
                  Shift=True, Extra='F'),
        width='400',
        height='400',
        ratioKeep='height',
        scalingMode='smooth'
    )

    defaultConfig = copy.deepcopy(config)

    settingsMw = None
    addonDir = mw.pm.addonFolder()

    irFolder = os.path.join(addonDir, addon_id, 'user_files')
    pickleFile = os.path.join(irFolder, 'config.pickle')

    def __init__(self, imageResizer):
        self.checkConfigAndLoad()
        self.setupMenu()
        self.setupFunctions(imageResizer)

    def checkConfigAndLoad(self):
        """Check if the ImageResizer folder exists
           Create one if not, then load the configuration
        """
        if not os.path.exists(Setup.irFolder):
            os.makedirs(Setup.irFolder)
        if not os.path.exists(Setup.pickleFile):
            # dump the default config if config.pickle doesn't exist
            with open(Setup.pickleFile, 'wb') as f:
                pickle.dump(Setup.config, f)

        # load config.pickle
        with open(self.pickleFile, 'rb') as f:
            Setup.config = pickle.load(f)

    def setupMenu(self):
        """
        setup menu in anki
        """
        action = QAction("Image Resizer", mw)
        action.triggered.connect(self._settings)
        mw.form.menuTools.addAction(action)

        # Setup config button
        mw.addonManager.setConfigAction(addon_id, self._settings)

    def setupFunctions(self, imageResizer):
        """Replace functions in anki
        """
        # setup button
        Editor.setupWeb = wrap(Editor.setupWeb, ImageResizerButton, 'after')
        Editor.imageResizer = imageResizer

        try:
            gui_hooks.editor_will_process_mime.append(will_process_mime_handler)
        except AttributeError:
            # Probably the hook doesn't exist, we fall back to the old way
            if len((signature(EditorWebView._processMime)).parameters) == 2:
                EditorWebView._processMime = wrap(EditorWebView._processMime, _processMime_around, 'around')
            elif len((signature(EditorWebView._processMime)).parameters) == 3:
                # From Anki 2.1.36, _processMime has one more parameter
                EditorWebView._processMime = wrap(EditorWebView._processMime, _processMime_around_with_extended, 'around')
            else:
                # From Anki 2.1.50beta, _processMime has four parameters
                EditorWebView._processMime = wrap(EditorWebView._processMime, _processMime_around_with_extended_and_drop_event, 'around')

    def _settings(self):
        """
        Show the settings dialog if the user clicked on the menu
        """
        self.settingsMw = Settings(self, Setup.config)

        self.settingsMw.showNormal()
        self.settingsMw.raise_()
        self.settingsMw.activateWindow()


def resize(im):
    """Resize the image
    :im: QImage to be resized
    :returns: resized QImage
    """

    option = Setup.config['ratioKeep']
    isUpScalingDisabled = Setup.config['isUpScalingDisabled']
    heightInConfig = int(Setup.config['height'])
    widthInConfig = int(Setup.config['width'])
    transformationMode = Qt.TransformationMode.FastTransformation if (Setup.config['scalingMode'] == 'fast') else Qt.TransformationMode.SmoothTransformation

    if option == 'height' or option == 'either' and im.width() <= im.height():
        if im.height() <= heightInConfig and not isUpScalingDisabled or im.height() > heightInConfig:
            im = im.scaledToHeight(heightInConfig, transformationMode)
    elif option == 'width' or option == 'either' and im.height() < im.width():
        if im.width() <= widthInConfig and not isUpScalingDisabled or im.width() > widthInConfig:
            im = im.scaledToWidth(widthInConfig, transformationMode)

    return im


def isLocalImageFile(url):
    pic = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".gif", ".svg", ".webp")
    if not url.startswith("file://"):
        return False
    filename, fileExt = os.path.splitext(url)
    return fileExt in pic


def isWebImageFile(url):
    return url.startswith("http") or url.startswith("https")


def containsImage(qMimeData):
    return containsImageInImageData(qMimeData) or containsImageInUrl(qMimeData) or (
                tryGettingImageSrcFromHtml(qMimeData) is not None)


def containsImageInImageData(qMimeData):
    return qMimeData.hasImage() and qMimeData.imageData() is not None


def containsImageInUrl(qMimeData):
    return containsLocalFileImageInUrl(qMimeData) or containsWebImageInUrl(qMimeData)


def containsLocalFileImageInUrl(qMimeData):
    return qMimeData.hasUrls() and qMimeData.urls() and isLocalImageFile(qMimeData.urls()[0].toString())


def containsWebImageInUrl(qMimeData):
    return qMimeData.hasImage() and qMimeData.hasUrls() and qMimeData.urls() and isWebImageFile(
        qMimeData.urls()[0].toString())


def tryGettingImageSrcFromHtml(qMimeData):
    if not (qMimeData.hasImage() and qMimeData.hasHtml() and qMimeData.html()):
        return None
    soup = BeautifulSoup(qMimeData.html(), features="html.parser")
    imgs = soup.findAll("img")
    if not imgs:
        return None
    return QUrl.fromUserInput(imgs[0]["src"]).toString()


def isWin():
    return platform.system() == "Windows"


def extractLocalPathFromFileUrl(fileUrl):
    if isWin():
        return fileUrl[len("file:///"):]
    else:
        return fileUrl[len("file://"):]


def imageResizer(self, paste=True, mime=None):
    """resize the image contained in the clipboard
       paste: paste the resized image in the currently focused widget if the parameter is set True
       returns: QMimeData"""

    if mime == None:
        mime = mw.app.clipboard().mimeData()
    # check if mime contains any image related urls, and put the image data in the clipboard if it contains it
    mime = checkAndResize(mime)

    # check if mime contains images or any image file urls
    if containsImageInImageData(mime):

        if paste:
            # paste it in the currently focused widget
            clip = self.mw.app.clipboard()
            clip.setMimeData(mime, mode=QClipboard.Mode.Clipboard)

            focusedWidget = QApplication.focusWidget()
            # focusedWidget.paste()
            self.onPaste()

    return mime


def ImageResizerButton(self):
    shortcut = '+'.join([k for k, v in list(Setup.config['keys'].items()) if v == True])
    shortcut += '+' + Setup.config['keys']['Extra']
    self.addButton(func=lambda s=self: imageResizer(self),
                   icon=None, label="Image Resizer", cmd='imageResizer(self)', keys=_(shortcut))


def _processMime_around(self, mime, _old):
    """I found that anki dealt with html, urls, text first before dealing with image,
    I didn't find any advantages of it. If the user wants to copy an image from the web broweser,
    it will make anki fetch the image again, which is a waste of time. the function will try to deal with image data first if mime contains it.contains

    This function is always called when pasting!"""

    # "Paste when resizing"
    if Setup.config['auto'] is False:
        return _old(self, mime)

    if containsImage(mime):
        # Resize the image, then pass to Anki
        mime = self.editor.imageResizer(paste=False, mime=mime)

        return _old(self, mime)
        # return self._processImage(mime)

    return _old(self, mime)


def _processMime_around_with_extended(self, mime, extended, _old):
    return _processMime_around(self, mime, _old)

def _processMime_around_with_extended_and_drop_event(self, mime, extended, drop_event, _old):
    return _processMime_around(self, mime, _old)


def checkAndResize(mime):
    """check if mime contains url and if the url represents a picture file path, fetch the url and put the image in the clipboard if the url represents an image file
    the function will resize the image if it finds that mime contains it

    :mime: QMimeData to be checked
    :editor: an instance of Editor

    :returns: image filled QMimeData if the contained url represents an image file, the original QMimeData otherwise
    """

    if containsImageInImageData(mime):
        im = resize(mime.imageData())
        mime = QMimeData()
        mime.setImageData(im)
        return mime

    if containsImageInUrl(mime):
        url = mime.urls()[0].toString()

        # fetch the image
        if containsWebImageInUrl(mime):
            im = QImage()
            filecontents = requests.get(url)
            im.loadFromData(filecontents.content)
        elif containsLocalFileImageInUrl(mime):
            im = QImage(extractLocalPathFromFileUrl(url))

        # resize it
        im = resize(im)
        mime = QMimeData()
        mime.setImageData(im)
        return mime

    imgLink = tryGettingImageSrcFromHtml(mime)
    if imgLink is not None:
        im = QImage()
        im.loadFromData(requests.get(imgLink).content)
        im = resize(im)
        mime = QMimeData()
        mime.setImageData(im)
        return mime

    return mime


class GrabKey(QWidget):
    """
    Grab the key combination to paste the resized image
    """

    def __init__(self, parent):
        super(GrabKey, self).__init__()
        self.parent = parent
        self.setupUI()

        # self.active is used to trace whether there's any key held now
        self.active = 0

        self.ctrl = False
        self.alt = False
        self.shift = False
        self.extra = None

    def setupUI(self):
        mainLayout = QVBoxLayout()
        self.setLayout(mainLayout)

        label = QLabel('Please press the new key combination')
        mainLayout.addWidget(label)

        self.setWindowTitle('Grab key combination')
        self.show()

    def keyPressEvent(self, evt):
        self.active += 1
        if evt.key() > 0 and evt.key() < 127:
            self.extra = chr(evt.key())
        elif evt.key() == Qt.Key.Key_Control:
            self.ctrl = True
        elif evt.key() == Qt.Key.Key_Alt:
            self.alt = True
        elif evt.key() == Qt.Key.Key_Shift:
            self.shift = True

    def keyReleaseEvent(self, evt):
        self.active -= 1
        if self.active == 0:
            if not (self.ctrl or self.alt or self.shift):
                msg = QMessageBox()
                msg.setText('Please press at least one of these keys: Ctrl/Alt/Shift')
                msg.exec_()
                return
            Setup.config['keys'] = dict(Ctrl=self.ctrl, Alt=self.alt,
                                        Shift=self.shift, Extra=self.extra)
            self.parent.updateKeyCombinations()
            self.close()


class Settings(QWidget):
    """
    Image Resizer Settings Window
    """

    def __init__(self, setup, config, parent=None):
        super(Settings, self).__init__(parent=parent)

        self.parent = parent
        self.setup = setup
        self.pickleFile = Setup.pickleFile

        self.setupUI()
        self.checkPickle()

    def checkPickle(self):
        """if the config file exists, load it,
           or continue to use the default setting if the config file
           doesn't exist
        """
        if os.path.exists(self.pickleFile):
            self.loadFromDisk()

    def saveToDisk(self):
        """save settings to the current directory where the plugin lies,
           then close the settings window
        """
        Setup.config['isUpScalingDisabled'] = self.disableUpScalingCb.isChecked()
        Setup.config['auto'] = self.enableCb.isChecked()
        Setup.config['width'] = self.widthEdit.text()
        Setup.config['height'] = self.heightEdit.text()
        if self.ratioCb.currentIndex() == 0:
            Setup.config['ratioKeep'] = 'height'
        elif self.ratioCb.currentIndex() == 1:
            Setup.config['ratioKeep'] = 'width'
        elif self.ratioCb.currentIndex() == 2:
            Setup.config['ratioKeep'] = 'either'
        if self.scalingCb.currentIndex() == 0:
            Setup.config['scalingMode'] = 'fast'
        elif self.scalingCb.currentIndex() == 1:
            Setup.config['scalingMode'] = 'smooth'
        with open(self.pickleFile, 'wb') as f:
            pickle.dump(Setup.config, f)

        self.close()

    def fillInMissedKeys(self, previousConfig, newConfig):
        for key in previousConfig:
            if key not in newConfig:
                newConfig[key] = previousConfig[key]

    def loadFromDisk(self):
        """Load settings from disk
        """
        with open(self.pickleFile, 'rb') as f:
            Setup.config = pickle.load(f)

        self.fillInMissedKeys(Setup.defaultConfig, Setup.config)

        # reflect the settings on the window
        self.enableCb.setChecked(Setup.config['auto'])
        self.disableUpScalingCb.setChecked(Setup.config['isUpScalingDisabled'])
        self.updateKeyCombinations()
        self.widthEdit.setText(Setup.config['width'])
        self.heightEdit.setText(Setup.config['height'])
        if Setup.config['ratioKeep'] == 'height':
            self.ratioCb.setCurrentIndex(0)
        elif Setup.config['ratioKeep'] == 'width':
            self.ratioCb.setCurrentIndex(1)
        elif Setup.config['ratioKeep'] == 'either':
            self.ratioCb.setCurrentIndex(2)
        self.setLineEditState()
        if Setup.config['scalingMode'] == 'fast':
            self.scalingCb.setCurrentIndex(0)
        elif Setup.config['scalingMode'] == 'smooth':
            self.scalingCb.setCurrentIndex(1)

    def reset(self):
        """reset all configurations to default"""
        if os.path.exists(Setup.irFolder):
            shutil.rmtree(Setup.irFolder)
        Setup.config = copy.deepcopy(Setup.defaultConfig)
        self.setup.checkConfigAndLoad()
        self.checkPickle()

    def updateKeyCombinations(self):
        """
        update the key combination label
        in the settings window according to Setup.config
        """
        label = self.grabKeyLabel
        label.setText('Shortcut to paste the resized image: ')

        # add ctrl/shift/alt
        [label.setText(label.text() + k + '+')
         for k, v in list(Setup.config['keys'].items())
         if k != 'Extra' and v == True]

        # add the extra key
        if Setup.config['keys'].get('Extra'):
            label.setText(label.text() +
                          Setup.config['keys'].get('Extra'))

    def showGrabKey(self):
        self.GrabKeyWindow = GrabKey(self)

    def setupUI(self):
        # main layout
        mainLayout = QVBoxLayout()
        self.setLayout(mainLayout)

        # add widgets to set shortcut
        self.enableCb = QCheckBox('Resize on pasting', self)
        self.disableUpScalingCb = QCheckBox('Disable upscaling', self)
        self.grabKeyLabel = QLabel('Shortcut to paste the resized image: Ctrl+Shift+F')
        grabKeyBtn = QPushButton('Grab the shortcut', self)
        grabKeyBtn.clicked.connect(self.showGrabKey)
        self.scalingCb = QComboBox(self)
        self.scalingCb.addItem('use fast resizing')
        self.scalingCb.addItem('use smooth resizing')
        keyHBox = QHBoxLayout()
        keyHBox.addWidget(self.grabKeyLabel)
        keyHBox.addWidget(grabKeyBtn)
        mainLayout.addWidget(self.enableCb)
        mainLayout.addWidget(self.disableUpScalingCb)
        mainLayout.addWidget(self.scalingCb)
        mainLayout.addLayout(keyHBox)

        # add widgets to set height and width
        widthLable = QLabel('width')
        heightLable = QLabel('height')
        self.widthEdit = QLineEdit(self)
        self.heightEdit = QLineEdit(self)
        self.ratioCb = QComboBox(self)
        self.ratioCb.addItem('scale to height and keep ratio')
        self.ratioCb.addItem('scale to width and keep ratio')
        self.ratioCb.addItem('scale to the maximum dimension and keep ratio')
        # QObject.connect(self.ratioCb, SIGNAL("currentIndexChanged(int)"), self.setLineEditState)
        self.ratioCb.currentIndexChanged.connect(self.setLineEditState)

        sizeLayout = QHBoxLayout()
        sizeLayout.addWidget(widthLable)
        sizeLayout.addWidget(self.widthEdit)
        sizeLayout.addWidget(heightLable)
        sizeLayout.addWidget(self.heightEdit)
        sizeLayout.addWidget(self.ratioCb)
        mainLayout.addLayout(sizeLayout)

        # add an horizontal line
        mainLayout.addWidget(self.hLine())

        # add OK and Cancel buttons
        okButton = QPushButton("OK")
        okButton.clicked.connect(self.saveToDisk)
        cancelButton = QPushButton("Cancel")
        cancelButton.clicked.connect(self.close)
        resetButton = QPushButton("Reset")
        resetButton.clicked.connect(self.reset)
        btnLayout = QHBoxLayout()
        btnLayout.addStretch(1)
        btnLayout.addWidget(okButton)
        btnLayout.addWidget(cancelButton)
        btnLayout.addWidget(resetButton)
        mainLayout.addLayout(btnLayout)

        # center the window
        self.move(QGuiApplication.primaryScreen().availableGeometry().center() - self.frameGeometry().center())
        self.setWindowTitle('Image Resizer Settings')
        self.show()
        self.raise_()
        self.activateWindow()

    def disableLineEdit(self, lineEdit):
        lineEdit.setReadOnly(True)

        # change color
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Base, QColorConstants.Svg.gray)
        palette.setColor(QPalette.ColorRole.Text, QColorConstants.Svg.white)
        lineEdit.setPalette(palette)

    def enableLineEdit(self, lineEdit):
        lineEdit.setReadOnly(False)

        # change color
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Base, QColorConstants.Svg.white)
        palette.setColor(QPalette.ColorRole.Text, QColorConstants.Svg.black)
        lineEdit.setPalette(palette)

    def setLineEditState(self):
        if self.ratioCb.currentIndex() == 0:
            self.disableLineEdit(self.widthEdit)
            self.enableLineEdit(self.heightEdit)
        elif self.ratioCb.currentIndex() == 1:
            self.disableLineEdit(self.heightEdit)
            self.enableLineEdit(self.widthEdit)
        elif self.ratioCb.currentIndex() == 2:
            self.enableLineEdit(self.heightEdit)
            self.enableLineEdit(self.widthEdit)

    def hLine(self):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        return line


s = Setup(imageResizer)