#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    :  test.py
@Date    :  2022/03/28
@Author  :  Yaronzz
@Version :  1.0
@Contact :  yaronhuang@foxmail.com
@Desc    :
"""
import importlib
import sys
import traceback

from events import *
from printf import *


def enableGui():
    try:
        importlib.import_module('PyQt5')
        importlib.import_module('qt_material')
        return True
    except Exception as e:
        return False


if not enableGui():
    def startGui():
        Printf.err("Not support gui. Please type: `pip3 install PyQt5 qt_material`")
else:
    from PyQt5.QtCore import Qt, QObject, QRunnable, pyqtSignal, pyqtSlot, QThreadPool
    from PyQt5.QtGui import QTextCursor, QKeyEvent
    from PyQt5 import QtWidgets
    from qt_material import apply_stylesheet


    class WorkerSignals(QObject):
        """
        Defines the signals available from a running worker thread.

        Supported signals are:

        finished
            No data

        error
            tuple (exctype, value, traceback.format_exc() )

        result
            object data returned from processing, anything

        progress
            int indicating % progress
        """
        finished = pyqtSignal()
        error = pyqtSignal(tuple)
        result = pyqtSignal(object)
        progress = pyqtSignal(str)


    class Worker(QRunnable):
        """
        Worker thread

        Inherits from QRunnable to handler worker thread setup, signals and wrap-up.

        :param callback: The function callback to run on this worker thread. Supplied args and
                         kwargs will be passed through to the runner.
        :type callback: function
        :param args: Arguments to pass to the callback function
        :param kwargs: Keywords to pass to the callback function
        """

        def __init__(self, fn, *args, **kwargs):
            super(Worker, self).__init__()

            # Store constructor arguments (re-used for processing)
            self.fn = fn
            self.args = args
            self.kwargs = kwargs
            self.signals = WorkerSignals()

            # Add the callback to our kwargs
            # self.kwargs['progress_callback'] = self.signals.progress

        @pyqtSlot()
        def run(self):
            """
            Initialise the runner function with passed args, kwargs.
            """

            # Retrieve args/kwargs here; and fire processing using them
            try:
                result = self.fn(*self.args, **self.kwargs)
            except:
                traceback.print_exc()
                exctype, value = sys.exc_info()[:2]
                self.signals.error.emit((exctype, value, traceback.format_exc()))
            else:
                # Return the result of the processing
                self.signals.result.emit(result)
            finally:
                # Done
                self.signals.finished.emit()


    class SettingView(QtWidgets.QWidget):
        def __init__(self, ) -> None:
            super().__init__()
            self.initView()

        def initView(self):
            self.c_pathDownload = QtWidgets.QLineEdit()
            self.c_pathAlbumFormat = QtWidgets.QLineEdit()
            self.c_pathTrackFormat = QtWidgets.QLineEdit()
            self.c_pathVideoFormat = QtWidgets.QLineEdit()

            self.mainGrid = QtWidgets.QVBoxLayout(self)
            self.mainGrid.addWidget(self.c_pathDownload)
            self.mainGrid.addWidget(self.c_pathAlbumFormat)
            self.mainGrid.addWidget(self.c_pathTrackFormat)
            self.mainGrid.addWidget(self.c_pathVideoFormat)


    class EmittingStream(QObject):
        textWritten = pyqtSignal(str)

        def write(self, text):
            self.textWritten.emit(str(text))


    class MainView(QtWidgets.QWidget):
        s_downloadEnd = pyqtSignal(str, bool, str)

        def __init__(self, ) -> None:
            super().__init__()
            self.initView()
            self.setMinimumSize(800, 620)
            self.setWindowTitle("Tidal-dl")

            self.threadpool = QThreadPool()
            print("Multithreading with maximum %d threads" % self.threadpool.maxThreadCount())

        def __info__(self, msg):
            QtWidgets.QMessageBox.information(self, 'Info', msg, QtWidgets.QMessageBox.Yes)

        def __output__(self, text):
            cursor = self.c_printTextEdit.textCursor()
            cursor.movePosition(QTextCursor.End)
            cursor.insertText(text)
            self.c_printTextEdit.setTextCursor(cursor)
            self.c_printTextEdit.ensureCursorVisible()

        def initView(self):
            self.c_lineSearch = QtWidgets.QLineEdit()
            self.c_btnSearch = QtWidgets.QPushButton("Search")
            self.c_btnDownload = QtWidgets.QPushButton("Download")
            self.c_btnSetting = QtWidgets.QPushButton("Setting")
            self.c_combType = QtWidgets.QComboBox()
            self.c_combTQuality = QtWidgets.QComboBox()
            self.c_combVQuality = QtWidgets.QComboBox()
            self.c_widgetSetting = SettingView()
            self.c_widgetSetting.hide()

            # Supported types for search
            self.m_supportType = [Type.Album, Type.Playlist, Type.Track, Type.Video, Type.Artist]
            for item in self.m_supportType:
                self.c_combType.addItem(item.name, item)

            for item in AudioQuality:
                self.c_combTQuality.addItem(item.name, item)
            for item in VideoQuality:
                self.c_combVQuality.addItem(item.name, item)
            self.c_combTQuality.setCurrentText(SETTINGS.audioQuality.name)
            self.c_combVQuality.setCurrentText(SETTINGS.videoQuality.name)

            # init table
            columnNames = ['#', 'Title', 'Artists', 'Quality']
            self.c_tableInfo = QtWidgets.QTableWidget()
            self.c_tableInfo.setColumnCount(len(columnNames))
            self.c_tableInfo.setRowCount(0)
            self.c_tableInfo.setShowGrid(False)
            self.c_tableInfo.verticalHeader().setVisible(False)
            self.c_tableInfo.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
            self.c_tableInfo.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
            self.c_tableInfo.horizontalHeader().setStretchLastSection(True)
            self.c_tableInfo.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
            self.c_tableInfo.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
            self.c_tableInfo.setFocusPolicy(Qt.NoFocus)
            for index, name in enumerate(columnNames):
                item = QtWidgets.QTableWidgetItem(name)
                self.c_tableInfo.setHorizontalHeaderItem(index, item)

            # Create Tree View for playlists.
            self.tree_playlists = QtWidgets.QTreeWidget()
            self.tree_playlists.setAnimated(False)
            self.tree_playlists.setIndentation(20)
            self.tree_playlists.setSortingEnabled(True)
            self.tree_playlists.resize(200, 400)
            self.tree_playlists.setColumnCount(2)
            self.tree_playlists.setHeaderLabels(("Name", "# Tracks"))
            self.tree_playlists.setColumnWidth(0, 200)

            # print
            self.c_printTextEdit = QtWidgets.QTextEdit()
            self.c_printTextEdit.setReadOnly(True)
            self.c_printTextEdit.setFixedHeight(100)
            sys.stdout = EmittingStream(textWritten=self.__output__)
            sys.stderr = EmittingStream(textWritten=self.__output__)

            # layout
            self.lineGrid = QtWidgets.QHBoxLayout()
            self.lineGrid.addWidget(self.c_combType)
            self.lineGrid.addWidget(self.c_lineSearch)
            self.lineGrid.addWidget(self.c_btnSearch)

            self.line2Grid = QtWidgets.QHBoxLayout()
            self.line2Grid.addWidget(QtWidgets.QLabel("QUALITY:"))
            self.line2Grid.addWidget(self.c_combTQuality)
            self.line2Grid.addWidget(self.c_combVQuality)
            self.line2Grid.addStretch(4)
            # self.line2Grid.addWidget(self.c_btnSetting)
            self.line2Grid.addWidget(self.c_btnDownload)

            self.funcGrid = QtWidgets.QVBoxLayout()
            self.funcGrid.addLayout(self.lineGrid)
            self.funcGrid.addWidget(self.c_tableInfo)
            self.funcGrid.addLayout(self.line2Grid)
            self.funcGrid.addWidget(self.c_printTextEdit)

            self.mainGrid = QtWidgets.QGridLayout(self)
            self.mainGrid.addWidget(self.tree_playlists, 0, 0, 1, 2)
            self.mainGrid.addLayout(self.funcGrid, 0, 2, 1, 3)
            self.mainGrid.addWidget(self.c_widgetSetting, 0, 0)

            # connect
            self.c_btnSearch.clicked.connect(self.search)
            self.c_lineSearch.returnPressed.connect(self.search)
            self.c_btnDownload.clicked.connect(self.download_thread)
            self.s_downloadEnd.connect(self.downloadEnd)
            self.c_combTQuality.currentIndexChanged.connect(self.changeTQuality)
            self.c_combVQuality.currentIndexChanged.connect(self.changeVQuality)
            self.c_btnSetting.clicked.connect(self.showSettings)
            self.tree_playlists.itemClicked.connect(self.playlist_display_tracks)

            # Connect the contextmenu
            self.tree_playlists.setContextMenuPolicy(Qt.CustomContextMenu)
            self.tree_playlists.customContextMenuRequested.connect(self.menuContextTree)

        def keyPressEvent(self, event: QKeyEvent):
            key = event.key()

            if event.modifiers() & Qt.MetaModifier and key == Qt.Key_A:
                self.c_tableInfo.selectAll()

        def addItem(self, rowIdx: int, colIdx: int, text):
            if isinstance(text, str):
                item = QtWidgets.QTableWidgetItem(text)
                self.c_tableInfo.setItem(rowIdx, colIdx, item)

        def search(self):
            self.c_tableInfo.setRowCount(0)
            self.s_type = self.c_combType.currentData()
            self.s_text = self.c_lineSearch.text()

            if self.s_text.startswith('http'):
                tmpType, tmpId = TIDAL_API.parseUrl(self.s_text)
                if tmpType == Type.Null:
                    self.__info__('Url not support！')
                    return
                elif tmpType not in self.m_supportType:
                    self.__info__(f'Type[{tmpType.name}] not support！')
                    return

                tmpData = TIDAL_API.getTypeData(tmpId, tmpType)
                if tmpData is None:
                    self.__info__('Url is wrong!')
                    return
                self.s_type = tmpType
                self.s_array = [tmpData]
                self.s_result = None
                self.c_combType.setCurrentText(tmpType.name)
            else:
                self.s_result = TIDAL_API.search(self.s_text, self.s_type)
                self.s_array = TIDAL_API.getSearchResultItems(self.s_result, self.s_type)

            if len(self.s_array) <= 0:
                self.__info__('No result！')
                return

            self.set_table_search_results(self.s_array, self.s_type)

        def set_table_search_results(self, s_array, s_type):
            self.c_tableInfo.clearSelection()
            self.c_tableInfo.setRowCount(len(s_array))

            for index, item in enumerate(s_array):
                self.addItem(index, 0, str(index + 1))
                if s_type in [Type.Album, Type.Track]:
                    self.addItem(index, 1, item.title)
                    self.addItem(index, 2, TIDAL_API.getArtistsName(item.artists))
                    self.addItem(index, 3, item.audioQuality)
                elif s_type in [Type.Video]:
                    self.addItem(index, 1, item.title)
                    self.addItem(index, 2, TIDAL_API.getArtistsName(item.artists))
                    self.addItem(index, 3, item.quality)
                elif s_type in [Type.Playlist]:
                    self.addItem(index, 1, item.title)
                    self.addItem(index, 2, '')
                    self.addItem(index, 3, '')
                elif s_type in [Type.Artist]:
                    self.addItem(index, 1, item.name)
                    self.addItem(index, 2, '')
                    self.addItem(index, 3, '')
            self.c_tableInfo.viewport().update()

        def progress_fn(self, msg):
            Printf.info(msg)

        def print_output(self, s):
            Printf.info(s)

        def thread_complete(self):
            self.c_btnDownload.setEnabled(True)
            self.c_btnDownload.setText(f"Download")
            Printf.info("THREAD COMPLETE!")

        def download_thread(self):
            # Pass the function to execute
            # Any other args, kwargs are passed to the run function
            worker = Worker(self.download)
            # worker.signals.result.connect(self.print_output)
            worker.signals.finished.connect(self.thread_complete)
            # worker.signals.progress.connect(self.progress_fn)

            # Execute
            self.threadpool.start(worker)

        def download(self):
            self.c_btnDownload.setEnabled(False)
            self.c_btnDownload.setText(f"DOWNLOADING...")

            index = self.c_tableInfo.currentIndex().row()
            selection = self.c_tableInfo.selectionModel()
            has_selection = selection.hasSelection()

            if has_selection == False:
                self.__info__('Please select a row first.')
                return

            rows = self.c_tableInfo.selectionModel().selectedRows()

            for row in rows:
                index = row.row()
                item = self.s_array[index]
                item_type = self.s_type

                self.download_item(item, item_type)

        def download_item(self, item, item_type):
            item_to_download = ""
            if isinstance(item, Artist):
                item_to_download = item.name
            else:
                item_to_download = item.title

            self.download_(item, item_type)

        # Not race condition safe. Needs refactoring.
        def download_(self, item, s_type):
            downloading_item = ""
            try:
                item_type = s_type

                start_type(item_type, item)

                if isinstance(item, Artist):
                    downloading_item = item.name
                else:
                    downloading_item = item.title

                self.s_downloadEnd.emit(downloading_item, True, '')
            except Exception as e:
                self.s_downloadEnd.emit(downloading_item, False, str(e))

        def downloadEnd(self, title, result, msg):

            if result:
                Printf.info(f"Download '{title}' finished.")
            else:
                Printf.err(f"Download '{title}' failed:{msg}")

        def checkLogin(self):
            if not loginByConfig():
                self.__info__('Login failed. Please log in using the command line first.')

        def changeTQuality(self, index):
            SETTINGS.audioQuality = self.c_combTQuality.itemData(index)
            SETTINGS.save()

        def changeVQuality(self, index):
            SETTINGS.videoQuality = self.c_combVQuality.itemData(index)
            SETTINGS.save()

        def showSettings(self):
            self.c_widgetSetting.show()

        def tree_items_playlists(self):
            playlists = TIDAL_API.get_playlists()

            for playlist in playlists:
                item = QtWidgets.QTreeWidgetItem(self.tree_playlists)
                item.setText(0, playlist.name)
                item.setText(1, str(playlist.num_tracks))
                item.setText(2, playlist.id)

        def playlist_display_tracks(self, item, column):
            tracks = TIDAL_API.get_playlist_items(item.text(2))
            self.s_array = tracks
            self.s_type = Type.Track

            self.set_table_search_results(tracks, Type.Track)

        def menuContextTree(self, point):
            # Infos about the node selected.
            index = self.tree_playlists.indexAt(point)

            if not index.isValid():
                return

            # We build the menu.
            menu = QtWidgets.QMenu()
            action = menu.addAction("Dowload Playlist", lambda: self.download_playlist_thread(point))

            menu.exec_(self.tree_playlists.mapToGlobal(point))

        def download_playlist_thread(self, point):
            # Any other args, kwargs are passed to the run function
            worker = Worker(self.download_playlist, point)
            worker.signals.finished.connect(self.thread_complete)

            # Execute
            self.threadpool.start(worker)

        def download_playlist(self, point):
            item = self.tree_playlists.itemAt(point)
            playlist = Playlist()
            playlist.title = item.text(0)
            playlist.uuid = item.text(2)

            self.c_btnDownload.setEnabled(False)
            self.c_btnDownload.setText(f"DOWNLOADING...")

            self.download_item(playlist, Type.Playlist)


    def startGui():
        aigpy.cmd.enableColor(False)

        app = QtWidgets.QApplication(sys.argv)
        apply_stylesheet(app, theme='dark_blue.xml')

        window = MainView()
        window.show()
        window.checkLogin()
        window.tree_items_playlists()

        app.exec_()

if __name__ == '__main__':
    SETTINGS.read(getProfilePath())
    TOKEN.read(getTokenPath())
    startGui()
