import datetime
import sys
from urllib.request import urlopen
from pprint import pprint

import yt_dlp
from PyQt6.QtGui import QPixmap
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
        self.urlInput.setFocus()

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

        # parse table
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
                self.qualityTable.setItem(i, j, QTableWidgetItem(str(row.get(column, '') or '')))
        self.qualityTable.resizeColumnsToContents()

        # parse main info
        preview_pixmap = QPixmap()
        with urlopen(info['thumbnail']) as picUrl:
            preview_pixmap.loadFromData(picUrl.read())
        self.previewPic.setPixmap(preview_pixmap)
        self.videoName.setText(info['title'])
        self.videoName.setToolTip(info['description'])
        self.channelText.setText(f'<a href="{info["uploader_url"]}">{info["channel"]}</a>')
        self.subscribersText.setText(str(info['channel_follower_count']) + ' подписчиков')
        self.verifiedTick.setVisible(info['channel_is_verified'])
        self.commentsText.setText(str(info['comment_count']))
        self.durationText.setText(info['duration_string'])
        self.dateText.setText(info['upload_date'])
        self.viewsText.setText(str(info['view_count']))
        qualities = list(set(i['format_note'] for i in formats if 'format_note' in i and i['format_note'][-1] == 'p'))
        qualities.sort(key=lambda x: int(x[0:-1]))
        self.qualityBox.clear()
        self.qualityBox.addItems(qualities)

        self.downloadProgress.setValue(0)

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
