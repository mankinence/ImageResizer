try:
    from PyQt6 import QtCore, QtGui, QtWidgets
    from PyQt6.QtGui import QAction, QImage
    from PyQt6.QtCore import Qt, QMimeData
    from PyQt6.QtWidgets import (
        QMainWindow, QApplication,
        QLabel, QToolBar, QStatusBar, QWidget, QVBoxLayout, QMessageBox, QCheckBox, QPushButton, QComboBox, QHBoxLayout,
        QLineEdit
    )
except ImportError:
    from PyQt5 import QtGui
    from PyQt5.QtCore import Qt, QMimeData
    from PyQt5.QtWidgets import (
        QApplication,
        QLabel, QVBoxLayout, QMessageBox, QCheckBox, QPushButton, QComboBox, QHBoxLayout,
        QLineEdit
    )
