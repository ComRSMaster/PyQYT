import sys
import webbrowser
from dataclasses import dataclass
from threading import Thread
from typing import Optional, Any
from urllib.request import urlopen
from pprint import pprint

import yt_dlp
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QApplication, QMainWindow, QDialog, QTableWidgetItem, QListWidgetItem, QFileDialog

from ui.app import Ui_MainWindow
from ui.historyitem import Ui_HistoryItem
from ui.settings import Ui_Dialog as Ui_Settings
from pathlib import Path

import sqlite3

info_columns = [
    'format_id', 'ext', 'resolution', 'fps', 'filesize', 'filesize_approx', 'tbr',
    'vcodec', 'vbr',
    'audio_channels', 'acodec', 'abr', 'asr',
    'format', 'format_note', 'dynamic_range', 'url'
]


@dataclass
class Video:
    name: str
    channel: str
    duration: str
    url: str
    quality: Optional[Any] = None
    thumbnail: Optional[Any] = None


class MainWidget(QMainWindow, Ui_MainWindow):
    current_video: Video
    current_formats: list[dict]

    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.settingsBtn.clicked.connect(self.settings_open)
        self.continueBtn.clicked.connect(self.parse_video_info)
        self.saveBtn.clicked.connect(self.download_video)
        self.folderSelectBtn.clicked.connect(self.select_download_folder)
        self.savePath.setText(str(Path.home() / "Downloads"))
        self.urlInput.setFocus()
        self.urlInput.setText("https://youtu.be/Lfo29TGB8DQ")

        Path.mkdir(Path.cwd() / 'data' / 'previews', parents=True, exist_ok=True)
        self.conn = sqlite3.connect("data/main.db")
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS `history` (
            `id` INTEGER PRIMARY KEY AUTOINCREMENT,
            `name` TEXT NOT NULL,
            `channel` TEXT NOT NULL,
            `duration` TEXT NOT NULL,
            `url` TEXT NOT NULL,
            `path` TEXT NOT NULL,
            `quality` TEXT NOT NULL
            )""")
        self.conn.commit()

        self.load_history()

    def select_download_folder(self):
        self.savePath.setText(QFileDialog.getExistingDirectory(
            self, "Выберите папку для сохранения", self.savePath.text()) or self.savePath.text())

    def load_history(self):
        cur = self.conn.cursor()
        cur.execute("SELECT id, name, channel, duration, url, path, quality FROM history ORDER BY id DESC")
        history = cur.fetchall()

        for v_id, name, channel, duration, url, path, quality in history:
            item = QListWidgetItem(self.historyList)
            self.historyList.addItem(item)

            row = Ui_HistoryItem(name, channel, str(Path.cwd() / 'data' / 'previews' / f'{v_id}.webp'),
                                 duration, url, quality)
            item.setSizeHint(row.minimumSizeHint())

            self.historyList.setItemWidget(item, row)
            self.historyList.clicked.connect(lambda: self.open_downloaded_video(path))

    def parse_video_info(self):
        self.continueBtn.setDisabled(True)
        url = self.urlInput.text()

        self.downloadProgress.setValue(10)
        with yt_dlp.YoutubeDL() as ydl:
            info = ydl.extract_info(url, download=False)
        self.downloadProgress.setValue(90)
        pprint(info)

        self.current_video = Video(info['title'], info['channel'], info['duration_string'], url, f"{info['height']}p")

        self.savePath.setEnabled(True)
        self.folderSelectBtn.setEnabled(True)
        self.saveBtn.setEnabled(True)

        # parse table
        self.current_formats = info['formats']
        pprint(info_columns)

        self.qualityTable.setColumnCount(len(info_columns))
        self.qualityTable.setHorizontalHeaderLabels(info_columns)
        self.qualityTable.setRowCount(len(self.current_formats))
        for i, row in enumerate(self.current_formats):
            for j, column in enumerate(info_columns):
                self.qualityTable.setItem(i, j, QTableWidgetItem(str(row.get(column, '') or '')))
        self.qualityTable.resizeColumnsToContents()

        # parse main info
        preview_pixmap = QPixmap()
        with urlopen(info['thumbnail']) as picUrl:
            self.current_video.thumbnail = picUrl.read()
            preview_pixmap.loadFromData(self.current_video.thumbnail)
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
        qualities = list(set(
            i['format_note'] for i in self.current_formats if 'format_note' in i and i['format_note'][-1] == 'p'))
        qualities.sort(key=lambda x: int(x[0:-1]))
        self.qualityBox.clear()
        self.qualityBox.addItems(qualities)
        self.qualityBox.setCurrentIndex(len(qualities) - 1)

        self.downloadProgress.setValue(0)
        self.continueBtn.setEnabled(True)

    def open_downloaded_video(self, path: str):
        webbrowser.open(path)
        # subprocess.run(['open', path], check=True)

    def download_video(self):
        cur = self.conn.cursor()
        cur.execute("INSERT INTO history(name, channel, duration, url, path, quality) VALUES (?,?,?,?,?,?)",
                    (self.current_video.name, self.current_video.channel, self.current_video.duration,
                     self.current_video.url, self.savePath.text(), self.qualityBox.currentText()))
        self.conn.commit()
        with open(Path.cwd() / 'data' / 'previews' / f'{cur.lastrowid}.webp', 'wb') as thumb:
            thumb.write(self.current_video.thumbnail)
        self.load_history()

        Thread(target=self.download_video_thread).start()

    def download_video_thread(self):
        self.saveBtn.setEnabled(False)
        self.downloadProgress.setValue(0)

        options = {
            'ffmpeg_location': str(Path.cwd() / 'bin'),
            'progress_hooks': [self.download_progress],
            'outtmpl': self.savePath.text().removesuffix('/') + '/'
        }

        if self.tabWidget.currentIndex() == 0:
            if self.soundBox.currentIndex() == 0:
                options['format'] = f'bestvideo[height={self.qualityBox.currentText()[0:-1]}]+bestaudio/best'
            elif self.soundBox.currentIndex() == 1:
                options['format'] = 'bestaudio/best'
            else:
                options['format'] = f'bestvideo[height={self.qualityBox.currentText()[0:-1]}]/best'
        else:
            print(self.qualityTable.currentRow())
            options['format'] = self.current_formats[self.qualityTable.currentRow()]['format_id']

        if self.formatBox.currentIndex() != 0:
            options['postprocessors'] = [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': self.formatBox.currentText()
            }]

        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.download([self.current_video.url])

    def download_progress(self, d):
        # pprint(d)
        # print(d['status'])
        if d['status'] == 'finished':
            pprint(d)
            self.saveBtn.setEnabled(True)
            self.statusbar.clearMessage()
            self.downloadProgress.setValue(0)

        elif d['status'] == 'downloading':
            p = d['_percent_str']
            p = p.replace('%', '')
            self.downloadProgress.setValue(int(float(p)))
            self.downloadSpeed.setText(d['_speed_str'])
            self.statusbar.showMessage(f"Осталось {d['eta'] or ''} сек.")

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
    ex = MainWidget()
    ex.show()
    sys.exit(app.exec())
