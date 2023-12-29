import sys
from pprint import pprint

from PyQt5.QtWidgets import QApplication, QMainWindow, QDialog, QTableWidgetItem
import yt_dlp

from ui.app import Ui_MainWindow
from ui.settings import Ui_Dialog as Ui_Settings


class MyWidget(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.settingsBtn.clicked.connect(self.settings_open)
        self.continueBtn.clicked.connect(self.parse_video_info)

    def parse_video_info(self):
        self.load_qualities(self.urlInput.text())

    def load_qualities(self, url: str):
        ydl_opts = {}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            self.downloadProgress.setValue(10)
            info = ydl.extract_info(url, download=False)
            self.downloadProgress.setValue(90)
            pprint(info)
            formats = info['formats']
            columns = [
                'ext', 'resolution', 'fps', 'filesize', 'filesize_approx', 'tbr',
                'vcodec', 'vbr',
                'audio_channels', 'acodec', 'abr', 'asr',
                'format', 'format_note', 'dynamic_range'
            ]
            pprint(columns)

            self.qualityTable.setColumnCount(len(columns))
            self.qualityTable.setHorizontalHeaderLabels(columns)
            self.qualityTable.setRowCount(len(formats))
            for i, row in enumerate(formats):
                print(row)
                for j, column in enumerate(columns):
                    print(column)
                    self.qualityTable.setItem(i, j, QTableWidgetItem(str(row.get(column, 'aboba'))))
            self.downloadProgress.setValue(0)

        self.qualityTable.resizeColumnsToContents()

    def settings_open(self):
        dialog = SettingsWidget()
        dialog.show()
        dialog.exec_()


class SettingsWidget(QDialog, Ui_Settings):
    def __init__(self):
        super().__init__()
        self.setupUi(self)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MyWidget()
    ex.show()
    sys.exit(app.exec_())
