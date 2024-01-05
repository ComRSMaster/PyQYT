import sys
from pprint import pprint

import yt_dlp
from PyQt6.QtWidgets import QApplication, QMainWindow, QDialog, QTableWidgetItem, QListWidgetItem

from ui.app import Ui_MainWindow
from ui.historyitem import Ui_HistoryItem
from ui.settings import Ui_Dialog as Ui_Settings

import sqlite3


class MyWidget(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.settingsBtn.clicked.connect(self.settings_open)
        self.continueBtn.clicked.connect(self.parse_video_info)
        self.saveBtn.clicked.connect(self.download_video)

        self.load_history()

    def load_history(self):
        history = (
            ('ABOBA ABOBA ABOBA ABOBA', 'ABOBA', 'img.png'), ('ABOBA ABOBA ABOBA ABOBA', 'kaka', 'img_1.png'),
            ('ABOBA ABOBA ABOBA ABOBA', 'ABOBA', 'img.png'), ('ABOBA ABOBA ABOBA ABOBA', 'kaka1', 'img_1.png'),
            ('ABOBA ABOBA ABOBA ABOBA', 'ABOBA', 'img_2.png'), ('ABOBA ABOBA ABOBA ABOBA', 'kaka2', 'img_2.png'))
        for name, author, preview in history:
            item = QListWidgetItem(self.historyList)
            self.historyList.addItem(item)

            # Instanciate a custom widget
            row = Ui_HistoryItem(name, author, preview, '00:00:00')
            item.setSizeHint(row.minimumSizeHint())

            # Associate the custom widget to the list entry
            self.historyList.setItemWidget(item, row)

    def parse_video_info(self):
        self.load_qualities(self.urlInput.text())

    def load_qualities(self, url: str):
        self.downloadProgress.setValue(10)
        with yt_dlp.YoutubeDL() as ydl:
            info = ydl.extract_info(url, download=False)
            self.downloadProgress.setValue(90)
            pprint(info)
            formats = info['formats']
            columns = [
                'format_id', 'ext', 'resolution', 'fps', 'filesize', 'filesize_approx', 'tbr',
                'vcodec', 'vbr',
                'audio_channels', 'acodec', 'abr', 'asr',
                'format', 'format_note', 'dynamic_range', 'url'
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

    def download_video(self):
        self.downloadProgress.setValue(0)
        # with yt_dlp.YoutubeDL() as ydl:
        #     ydl.download()

    def settings_open(self):
        dialog = SettingsWidget()
        dialog.show()
        dialog.exec()


class SettingsWidget(QDialog, Ui_Settings):
    def __init__(self):
        super().__init__()
        self.setupUi(self)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MyWidget()
    ex.show()
    sys.exit(app.exec())
