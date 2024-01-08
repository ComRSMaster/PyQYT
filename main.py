import subprocess
import sys
from dataclasses import dataclass
from http.client import IncompleteRead
from typing import Optional, Any
from urllib.request import urlopen
from pprint import pprint

import yt_dlp
from PyQt6.QtCore import QObject, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QApplication, QMainWindow, QTableWidgetItem, QListWidgetItem, QFileDialog, \
    QMessageBox

from ui.app import Ui_MainWindow
from ui.historyitem import Ui_HistoryItem
from pathlib import Path

import sqlite3

info_columns = [
    'format_id', 'ext', 'resolution', 'fps', 'filesize', 'filesize_approx', 'tbr',
    'vcodec', 'vbr', 'audio_channels', 'acodec', 'abr', 'asr',
    'format', 'format_note', 'dynamic_range', 'url'
]


@dataclass
class Video:
    name: str
    channel: str
    duration: str
    url: str
    quality: Optional[str] = None
    thumbnail: Optional[Any] = None
    path: Optional[str] = None


class DownloadWorker(QObject):
    progress = pyqtSignal(dict)
    load_info_finished = pyqtSignal(dict)
    download_finished = pyqtSignal()

    @pyqtSlot(str)
    def load_info(self, url):
        with yt_dlp.YoutubeDL() as ydl:
            try:
                info = ydl.extract_info(url, download=False)
            except yt_dlp.utils.DownloadError as e:
                QMessageBox.critical(ex.previewPic, "Ошибка", e.msg)
        self.load_info_finished.emit(info)

    @pyqtSlot(dict, str)
    def download(self, options, url):
        options['progress_hooks'] = [lambda d: self.progress.emit(d)]
        options['postprocessor_hooks'] = [lambda d: self.progress.emit(d)]
        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.download([url])
        self.download_finished.emit()


def open_downloaded_video(path: str):
    subprocess.run(['open', path], check=True)


class MainWidget(QMainWindow, Ui_MainWindow):
    current_video: Video
    current_formats: list[dict]
    download_requested = pyqtSignal(dict, str)
    load_info_requested = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.continueBtn.clicked.connect(self.parse_video_info)
        self.saveBtn.clicked.connect(self.download_video)
        self.folderSelectBtn.clicked.connect(self.select_download_folder)
        self.savePath.setText(str(Path.home() / "Downloads"))
        self.urlInput.setFocus()
        self.soundBox.currentIndexChanged.connect(self.sound_formats_changed)

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

        self.worker_thread = QThread()
        self.worker = DownloadWorker()
        self.worker.progress.connect(self.download_progress)
        self.worker.load_info_finished.connect(self.parse_video_info_finished)
        self.worker.download_finished.connect(self.download_finished)
        self.worker.moveToThread(self.worker_thread)
        self.download_requested.connect(self.worker.download)
        self.load_info_requested.connect(self.worker.load_info)
        self.worker_thread.start()

    def select_download_folder(self):
        self.savePath.setText(QFileDialog.getExistingDirectory(
            self, "Выберите папку для сохранения", self.savePath.text()) or self.savePath.text())

    def load_history(self):
        cur = self.conn.cursor()
        cur.execute("SELECT id, name, channel, duration, url, path, quality FROM history ORDER BY id DESC")
        history = cur.fetchall()

        self.historyList.clear()
        for v_id, name, channel, duration, url, path, quality in history:
            item = QListWidgetItem(self.historyList)
            item.setToolTip(path)
            self.historyList.addItem(item)

            row = Ui_HistoryItem(name, channel, str(Path.cwd() / 'data' / 'previews' / f'{v_id}.webp'),
                                 duration, url, quality)
            item.setSizeHint(row.minimumSizeHint())

            self.historyList.setItemWidget(item, row)
            self.historyList.itemClicked.connect(lambda x: open_downloaded_video(x.toolTip()))

    def parse_video_info(self):
        self.continueBtn.setDisabled(True)
        self.downloadProgress.setValue(10)

        self.load_info_requested.emit(self.urlInput.text())

    def parse_video_info_finished(self, info):
        url = self.urlInput.text()
        pprint(info)

        self.current_video = Video(info['title'], info.get('uploader'),
                                   info.get('duration_string'), url, f"{info.get('height', 0)}p")

        self.savePath.setEnabled(True)
        self.saveBtn.setEnabled(True)
        self.folderSelectBtn.setEnabled(True)

        # parse main info
        preview_pixmap = QPixmap()
        with urlopen(info['thumbnail']) as picUrl:
            for i in range(3):
                try:
                    self.current_video.thumbnail = picUrl.read()
                    break
                except IncompleteRead:
                    # try again 3 attempts
                    print('retrying', i)
            preview_pixmap.loadFromData(self.current_video.thumbnail)
        self.previewPic.setPixmap(preview_pixmap)
        self.videoName.setText(info['title'])
        self.videoName.setToolTip(info.get('description'))
        self.widget_5.setVisible('uploader' in info)
        if 'uploader_url' in info:
            self.channelText.setText(f'<a href="{info["uploader_url"]}">{info["uploader"]}</a>')
        else:
            self.channelText.setText(info.get('uploader'))

        self.subscribersText.setVisible('channel_follower_count' in info)
        self.subscribersText.setText(str(info.get('channel_follower_count')) + ' подписчиков')
        self.verifiedTick.setVisible(info.get('channel_is_verified', False))
        self.widget_4.setVisible('comment_count' in info)
        self.commentsText.setText(str(info.get('comment_count')))
        self.widget_6.setVisible('duration_string' in info)
        self.durationText.setText(info.get('duration_string'))
        self.widget_3.setVisible('upload_date' in info)
        self.dateText.setText(info.get('upload_date'))
        self.widget_2.setVisible('like_count' in info)
        self.likeText.setText(str(info.get('like_count')))
        self.widget_1.setVisible(info.get('view_count') is not None)
        self.viewsText.setText(str(info.get('view_count')))

        # parse table
        self.current_formats = info['formats']

        self.qualityTable.setColumnCount(len(info_columns))
        self.qualityTable.setHorizontalHeaderLabels(info_columns)
        self.qualityTable.setRowCount(len(self.current_formats))
        for i, row in enumerate(self.current_formats):
            for j, column in enumerate(info_columns):
                self.qualityTable.setItem(i, j, QTableWidgetItem(str(row.get(column, '') or '')))
        self.qualityTable.resizeColumnsToContents()

        qualities = list(set(
            i['format_note'] for i in self.current_formats if 'format_note' in i and i['format_note'][-1] == 'p'))
        if len(qualities) == 0:
            qualities = list(set(
                f"{i['height']}p" for i in self.current_formats if 'height' in i and i['height'] is not None))
        qualities.sort(key=lambda x: int(x[0:-1]))
        self.qualityBox.clear()
        self.qualityBox.addItems(qualities)
        self.qualityBox.setCurrentIndex(len(qualities) - 1)

        self.continueBtn.setEnabled(True)
        self.downloadProgress.setValue(0)

    def download_video(self):
        self.saveBtn.setEnabled(False)
        self.downloadProgress.setValue(0)

        options = {
            'ffmpeg_location': str(Path.cwd() / 'bin'),
            'outtmpl': str(Path(self.savePath.text()) / '%(title)s - %(height)sp.%(ext)s'),
            'default_search': 'ytsearch',
            'noplaylist': True
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
            options['merge_output_format'] = self.formatBox.currentText()
            options['postprocessors'] = [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': self.formatBox.currentText()
            }]

        self.download_requested.emit(options, self.current_video.url)

    def download_finished(self):
        print('download_finished')
        self.saveBtn.setEnabled(True)
        self.statusbar.showMessage('Скачано', 0)
        self.downloadProgress.setValue(0)

        cur = self.conn.cursor()
        cur.execute("INSERT INTO history(name, channel, duration, url, path, quality) VALUES (?,?,?,?,?,?)",
                    (self.current_video.name, self.current_video.channel, self.current_video.duration,
                     self.current_video.url, self.current_video.path,
                     self.qualityBox.currentText()))
        self.conn.commit()
        with open(Path.cwd() / 'data' / 'previews' / f'{cur.lastrowid}.webp', 'wb') as thumb:
            thumb.write(self.current_video.thumbnail)
        self.load_history()


    def download_progress(self, d):
        # pprint(d)
        print(d['status'])
        if d['status'] == 'finished':
            self.current_video.path = d['info_dict'].get('filepath') or d['info_dict']['filename']
            pprint(d)
            print('finished download_progress')

        elif d['status'] == 'downloading' or d['status'] == 'processing':
            p = d['_percent_str']
            p = p.replace('%', '')
            self.downloadProgress.setValue(int(float(p)))
            self.downloadSpeed.setText(d['_speed_str'])
            self.statusbar.showMessage(f"Осталось {d['eta'] or ''} сек.")

    def sound_formats_changed(self, ind):
        if ind == 1:
            items = 'Исходный', 'mp3', 'flac', 'opus', 'wav', 'webm'
        else:
            items = 'Исходный', 'mp4', 'webm'
        self.formatBox.clear()
        self.formatBox.addItems(items)
        self.formatBox.setCurrentIndex(1)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MainWidget()
    ex.show()
    sys.exit(app.exec())
