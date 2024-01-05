from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_HistoryItem(QtWidgets.QWidget):
    def __init__(self, name, author, preview_path, duration):
        super().__init__()
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setContentsMargins(4, 4, 4, 4)
        self.horizontalLayout.setSpacing(16)

        self.image = QtWidgets.QLabel()
        self.image.setFixedSize(80, 80)
        self.image.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.image.setPixmap(QtGui.QPixmap(preview_path).scaled(80, 80, QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                                                                QtCore.Qt.TransformationMode.SmoothTransformation))
        self.horizontalLayout.addWidget(self.image)
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setSpacing(0)

        self.video_name = QtWidgets.QLabel()
        self.video_name.setFont(QtGui.QFont(self.video_name.font().family(), 11, QtGui.QFont.Weight.Bold))
        self.video_name.setText(name)

        self.video_author = QtWidgets.QLabel()
        self.video_author.setText(author)

        self.video_duration = QtWidgets.QLabel()
        self.video_duration.setText(duration)

        self.verticalLayout.addWidget(self.video_name)
        self.verticalLayout.addWidget(self.video_author)
        self.verticalLayout.addWidget(self.video_duration)
        self.horizontalLayout.addLayout(self.verticalLayout)

        self.setLayout(self.horizontalLayout)
