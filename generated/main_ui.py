# Form implementation matching ui/main_ui.ui (hand-authored)
# PyQt6 UI code generator not available in this environment, so this file
# mirrors the .ui structure and objectNames to keep code compatibility.

from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1100, 750)
        self.centralwidget = QtWidgets.QWidget(parent=MainWindow)
        self.centralwidget.setObjectName("centralwidget")

        # Root vertical layout
        self.rootLayout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.rootLayout.setObjectName("rootLayout")

        # --- Top bar ---
        self.topBarLayout = QtWidgets.QHBoxLayout()
        self.topBarLayout.setObjectName("topBarLayout")
        self.PM_LB = QtWidgets.QLabel(parent=self.centralwidget)
        self.PM_LB.setObjectName("PM_LB")
        self.topBarLayout.addWidget(self.PM_LB)
        self.hvpmStatus_LB = QtWidgets.QLabel(parent=self.centralwidget)
        self.hvpmStatus_LB.setObjectName("hvpmStatus_LB")
        self.topBarLayout.addWidget(self.hvpmStatus_LB)
        self.hvpm_CB = QtWidgets.QComboBox(parent=self.centralwidget)
        self.hvpm_CB.setObjectName("hvpm_CB")
        self.topBarLayout.addWidget(self.hvpm_CB)
        self.comport_LB = QtWidgets.QLabel(parent=self.centralwidget)
        self.comport_LB.setObjectName("comport_LB")
        self.topBarLayout.addWidget(self.comport_LB)
        self.comport_CB = QtWidgets.QComboBox(parent=self.centralwidget)
        self.comport_CB.setObjectName("comport_CB")
        self.topBarLayout.addWidget(self.comport_CB)
        self.topBarLayout.addItem(QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum))
        self.port_PB = QtWidgets.QPushButton(parent=self.centralwidget)
        self.port_PB.setObjectName("port_PB")
        self.topBarLayout.addWidget(self.port_PB)
        self.rootLayout.addLayout(self.topBarLayout)

        # --- Content area: graphs (left) and controls (right) ---
        self.contentLayout = QtWidgets.QHBoxLayout()
        self.contentLayout.setObjectName("contentLayout")

        # Graphs group
        self.graphsGroupBox = QtWidgets.QGroupBox(parent=self.centralwidget)
        self.graphsGroupBox.setObjectName("graphsGroupBox")
        self.graphsBoxLayout = QtWidgets.QVBoxLayout(self.graphsGroupBox)
        self.graphsBoxLayout.setObjectName("graphsBoxLayout")
        # This layout is where the runtime will insert PlotWidgets
        self.graphLayout = QtWidgets.QVBoxLayout()
        self.graphLayout.setObjectName("graphLayout")
        self.graphsBoxLayout.addLayout(self.graphLayout)
        self.contentLayout.addWidget(self.graphsGroupBox)

        # Controls group
        self.controlGroupBox = QtWidgets.QGroupBox(parent=self.centralwidget)
        self.controlGroupBox.setObjectName("controlGroupBox")
        self.controlVBox = QtWidgets.QVBoxLayout(self.controlGroupBox)
        self.controlVBox.setObjectName("controlVBox")

        # Graph control buttons
        self.graphButtonsLayout = QtWidgets.QHBoxLayout()
        self.graphButtonsLayout.setObjectName("graphButtonsLayout")
        self.startGraph_PB = QtWidgets.QPushButton(parent=self.controlGroupBox)
        self.startGraph_PB.setObjectName("startGraph_PB")
        self.graphButtonsLayout.addWidget(self.startGraph_PB)
        self.stopGraph_PB = QtWidgets.QPushButton(parent=self.controlGroupBox)
        self.stopGraph_PB.setObjectName("stopGraph_PB")
        self.graphButtonsLayout.addWidget(self.stopGraph_PB)
        self.controlVBox.addLayout(self.graphButtonsLayout)

        # Divider
        self.line = QtWidgets.QFrame(parent=self.controlGroupBox)
        self.line.setObjectName("line")
        self.line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.controlVBox.addWidget(self.line)

        # Voltage form
        self.voltForm = QtWidgets.QFormLayout()
        self.voltForm.setObjectName("voltForm")
        self.targetVoltTitle = QtWidgets.QLabel(parent=self.controlGroupBox)
        self.targetVoltTitle.setObjectName("targetVoltTitle")
        self.voltForm.setWidget(0, QtWidgets.QFormLayout.ItemRole.LabelRole, self.targetVoltTitle)
        self.hvpmVolt_LE = QtWidgets.QLineEdit(parent=self.controlGroupBox)
        self.hvpmVolt_LE.setObjectName("hvpmVolt_LE")
        self.voltForm.setWidget(0, QtWidgets.QFormLayout.ItemRole.FieldRole, self.hvpmVolt_LE)
        self.readbackTitle = QtWidgets.QLabel(parent=self.controlGroupBox)
        self.readbackTitle.setObjectName("readbackTitle")
        self.voltForm.setWidget(1, QtWidgets.QFormLayout.ItemRole.LabelRole, self.readbackTitle)
        self.hvpmVolt_LB = QtWidgets.QLabel(parent=self.controlGroupBox)
        self.hvpmVolt_LB.setObjectName("hvpmVolt_LB")
        self.voltForm.setWidget(1, QtWidgets.QFormLayout.ItemRole.FieldRole, self.hvpmVolt_LB)
        self.controlVBox.addLayout(self.voltForm)

        # Voltage buttons
        self.voltButtonsLayout = QtWidgets.QHBoxLayout()
        self.voltButtonsLayout.setObjectName("voltButtonsLayout")
        self.setVolt_PB = QtWidgets.QPushButton(parent=self.controlGroupBox)
        self.setVolt_PB.setObjectName("setVolt_PB")
        self.voltButtonsLayout.addWidget(self.setVolt_PB)
        self.readVolt_PB = QtWidgets.QPushButton(parent=self.controlGroupBox)
        self.readVolt_PB.setObjectName("readVolt_PB")
        self.voltButtonsLayout.addWidget(self.readVolt_PB)
        self.controlVBox.addLayout(self.voltButtonsLayout)

        # Stretch to push controls up
        self.controlVBox.addItem(QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding))

        self.contentLayout.addWidget(self.controlGroupBox)
        self.rootLayout.addLayout(self.contentLayout)

        # --- Logs ---
        self.logsGroupBox = QtWidgets.QGroupBox(parent=self.centralwidget)
        self.logsGroupBox.setObjectName("logsGroupBox")
        self.logsVBox = QtWidgets.QVBoxLayout(self.logsGroupBox)
        self.logsVBox.setObjectName("logsVBox")
        self.log_LW = QtWidgets.QListWidget(parent=self.logsGroupBox)
        self.log_LW.setObjectName("log_LW")
        self.logsVBox.addWidget(self.log_LW)
        self.rootLayout.addWidget(self.logsGroupBox)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(parent=MainWindow)
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(parent=MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "HVPM Monitor"))
        self.PM_LB.setText(_translate("MainWindow", "Power monitor"))
        self.hvpmStatus_LB.setText(_translate("MainWindow", "-"))
        self.comport_LB.setText(_translate("MainWindow", "COM PORT"))
        self.port_PB.setText(_translate("MainWindow", "REFRESH"))
        self.graphsGroupBox.setTitle(_translate("MainWindow", "Live Graphs"))
        self.controlGroupBox.setTitle(_translate("MainWindow", "Controls"))
        self.startGraph_PB.setText(_translate("MainWindow", "Start graph"))
        self.stopGraph_PB.setText(_translate("MainWindow", "Stop graph"))
        self.targetVoltTitle.setText(_translate("MainWindow", "Target Volt (V)"))
        self.readbackTitle.setText(_translate("MainWindow", "Readback"))
        self.setVolt_PB.setText(_translate("MainWindow", "Set Volt"))
        self.readVolt_PB.setText(_translate("MainWindow", "Read CurVolt"))
        self.hvpmVolt_LB.setText(_translate("MainWindow", "__.__ V"))
        self.logsGroupBox.setTitle(_translate("MainWindow", "Logs"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec())
