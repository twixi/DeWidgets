import os
import re
import sys
import json
import base64
import traceback
from multiprocessing import Process, Manager
from mcstatus import MinecraftServer
from PyQt5.QtWidgets import QWidget, QListWidget, QListWidgetItem, QVBoxLayout
from PyQt5.QtWidgets import QMenu, QPushButton, QMessageBox, QHBoxLayout
from PyQt5.QtWidgets import QInputDialog, QSpinBox, QLabel
from PyQt5.QtGui import QIcon, QPixmap, QImage
from PyQt5.QtCore import Qt, QSize, QTimer
from core.manager import Widget
from core.gui.help import TextViewer
from core.paths import RES, RELOAD, SETTINGS, ERROR, DELETE, HELP


def get_description(desc) -> str:
    if desc['text']:
        return desc['text']
    result = ''
    for part in desc['extra']:
        result += part['text']
    return result


class Main(Widget, QWidget):
    def __init__(self, widget_manager):
        Widget.__init__(self, widget_manager)
        QWidget.__init__(self)
        self.servers = []
        self.timer_interval = 30000
        self.lang = widget_manager.lang['MINECRAFT']
        # setup widget
        self.NAME = 'Minecraft Servers Monitoring'
        self.DESCRIPTION = self.lang['description']
        self.HELP = self.lang['help']
        self.AUTHOR = 'InterVi'
        self.EMAIL = 'intervionly@gmail.com'
        self.URL = 'https://github.com/InterVi/DeWidgets'
        self.ICON = QIcon(os.path.join(sys.path[0], 'res', 'minecraft',
                                       'minecraft.png'))
        # setup stylesheet
        with open(os.path.join(RES, 'minecraft', 'style.css'), encoding='utf-8'
                  ) as file:
            style = file.read()
            self.setStyleSheet(style)
        # setup list
        self.list = QListWidget(self)
        self.list.setStyleSheet(style)
        self.list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._show_list_menu)
        self.list.itemDoubleClicked.connect(self._list_double_click)
        self.list.setIconSize(QSize(64, 64))
        self.list.setWordWrap(True)
        self.list.setSelectionMode(QListWidget.NoSelection)
        # setup list menu
        self.list_menu = QMenu(self)
        reload_action = self.list_menu.addAction(QIcon(RELOAD),
                                                 self.widget_manager.lang[
                                                     'MINECRAFT']['reload'])
        reload_action.triggered.connect(self._list_fill)
        # setup v box layout
        self.v_box = QVBoxLayout(self)
        self.v_box.addWidget(self.list)
        self.v_box.setContentsMargins(0, 0, 0, 0)
        # setup timer
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._list_fill)
        self.start_timer = QTimer(self)
        self.start_timer.timeout.connect(self._list_fill)
        # buffer
        self.__manager = Manager()
        self.list_buffer = self.__manager.dict()
        # other
        self.__procs = []

    def boot(self):
        self._fill_settings()
        self._list_fill()
        self.start_timer.setSingleShot(True)
        self.start_timer.start(1000)

    def place(self):
        self.start_timer.setSingleShot(True)
        self.start_timer.start(1)

    def remove(self):
        self.update_timer.stop()
        self._kill_procs()

    def purge(self):
        self.update_timer.stop()
        self._kill_procs()

    def show_settings(self):
        try:
            self.settings_win = Settings(self)
        except:
            print(traceback.format_exc())

    def _list_fill(self):
        self._pool_ping()
        self.list.clear()
        for addr in self.servers:
            item = QListWidgetItem(self.list)
            try:
                if addr not in self.list_buffer:
                    item.setText(addr)
                    continue
                text, favicon, tooltip = json.loads(self.list_buffer[addr])
                favicon = base64.b64decode(favicon)
                item.setIcon(QIcon(QPixmap.fromImage(QImage.fromData(favicon)))
                             )
                item.setText(text)
                font = item.font()
                font.setPixelSize(10)
                font.setBold(True)
                item.setFont(font)
                item.setToolTip(tooltip)
            except:
                item.setText(addr)
                print(traceback.format_exc())

    def _fill_settings(self):
        section = self.widget_manager.config.config[self.NAME]
        if 'servers' in section:
            self.servers = json.loads(section['servers'])
        if 'timer' in section:
            self.timer_interval = int(section['timer'])
            if self.timer_interval > 0:
                self.update_timer.start(self.timer_interval)

    def _show_list_menu(self, point):
        try:
            self.list_menu.exec(self.list.mapToGlobal(point))
        except:
            print(traceback.format_exc())

    def _list_double_click(self):
        try:
            self.show_more = ShowMore(self)
        except:
            print(traceback.format_exc())

    def _kill_procs(self):
        try:
            for p in self.__procs:
                if p and p.is_alive():
                    p.terminate()
            self.__procs.clear()
        except:
            print(traceback.format_exc())

    def _pool_ping(self):
        def ping(addr):
            status = MinecraftServer.lookup(addr).status()
            favicon = status.favicon[status.favicon.find(',') + 1:]
            tooltip = ''
            if status.players.sample:
                for player in status.players.sample:
                    tooltip += player.name + ', '
            text = '[' + str(status.players.online) + ' / ' + \
                   str(status.players.max) + '] ' + \
                   self.lang['ping'].format(
                       str(status.latency)) + \
                   '\n[' + status.version.name + ']\n' + \
                   re.sub('§+[a-zA-Z0-9]', '',
                          get_description(status.description))
            self.list_buffer[addr] = json.dumps((text, favicon, tooltip[:-2]))

        self._kill_procs()
        for addr in self.servers:
            proc = Process(target=ping, args=(addr,))
            proc.start()
            self.__procs.append(proc)


class ShowMore(TextViewer):
    def __init__(self, main):
        self.main = main
        self.lang = main.widget_manager.lang['MINECRAFT']
        title = main.list.item(main.list.currentRow()).text()
        for i in range(4):
            title = title[title.find(']\n'):]
        super().__init__(
            title[2:].strip(), self.lang['close_button'],
            self.lang['close_button_tt']
        )
        self.setWindowIcon(main.list.item(main.list.currentRow()).icon())
        self.exit_button.clicked.connect(self.close)
        self.text.setHtml(self.lang['wait'])
        self.__manager = Manager()
        self.__info_buffer = self.__manager.dict()
        self.__proc = None
        self._ping_server()
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.print_info)
        self.timer.start(100)
        self.show()

    def _ping_server(self):
        def ping():
            self.__info_buffer['online'] = ''
            self.__info_buffer['max'] = ''
            self.__info_buffer['version'] = ''
            self.__info_buffer['protocol'] = ''
            self.__info_buffer['players'] = ''
            self.__info_buffer['ping'] = ''
            self.__info_buffer['description'] = ''
            self.__info_buffer['map'] = ''
            self.__info_buffer['brand'] = ''
            self.__info_buffer['plugins'] = ''
            config = self.main.widget_manager.config.config
            if 'servers' not in config[self.main.NAME]:
                return
            servers = json.loads(config[self.main.NAME]['servers'])
            if not servers:
                return
            addr = servers[self.main.list.currentRow()]
            try:
                status = MinecraftServer.lookup(addr).status()
            except:
                print(traceback.format_exc())
                return
            self.__info_buffer['online'] = str(status.players.online)
            self.__info_buffer['max'] = str(status.players.max)
            self.__info_buffer['version'] = status.version.name
            self.__info_buffer['protocol'] = status.version.protocol
            self.__info_buffer['ping'] = str(status.latency)
            players = ''
            if status.players.sample:
                for p in status.players.sample:
                    players += p.name + '(' + p.id + ')' + ', <br/>'
            self.__info_buffer['players'] = players[:-7]
            self.__info_buffer['description'] = get_description(
                status.description)
            try:
                query = MinecraftServer.lookup(addr).query()
            except:
                print(traceback.format_exc())
                return
            self.__info_buffer['map'] = query.map
            self.__info_buffer['brand'] = query.software.brand
            plugins = ''
            for p in query.software.plugins:
                plugins += p + ', '
            self.__info_buffer['plugins'] = plugins[:-2]
            for p in query.players.names:
                if p not in players:
                    players += p + ', <br/>'
            self.__info_buffer['players'] = players[:-7]

        if self.__proc and self.__proc.is_alive():
            self.__proc.terminate()
        self.__proc = Process(target=ping)
        self.__proc.start()

    def print_info(self):
        self.text.setHtml(self.lang['info'].format(
            **self.__info_buffer))
        if self.__proc and self.__proc.is_alive():
            self.timer.start(100)

    def close(self):
        try:
            self.timer.stop()
            try:
                if self.__proc and self.__proc.is_alive():
                    self.__proc.terminate()
                    self.__proc = None
            except:
                print(traceback.format_exc())
            super().setHidden(True)  # app close bug -> call close or destroy
        except:
            print(traceback.format_exc())


class Settings(QWidget):
    def __init__(self, main):
        super().__init__()
        self.main = main
        self.lang = main.widget_manager.lang['MINECRAFT']
        # setup window
        self.setWindowTitle(self.lang['settings_title'])
        self.setWindowIcon(QIcon(SETTINGS))
        self.resize(400, 460)
        # setup list
        self.list = QListWidget(self)
        self.list.setIconSize(QSize(64, 64))
        self.list.setWordWrap(True)
        self._list_fill()
        # setup 'Update' label
        self.update_label = QLabel(self)
        self.update_label.setText(self.lang['time_label'])
        self.update_label.setAlignment(Qt.AlignCenter)
        # setup 'Time' spinbox
        self.time_edit = QSpinBox(self)
        self.time_edit.setMinimum(0)
        self.time_edit.setMaximum(1000000000)
        self.time_edit.setValue(int(self.main.timer_interval/1000))
        self.time_edit.setToolTip(self.lang['time_input_tt'])
        self.time_edit.setAlignment(Qt.AlignCenter)
        self.time_edit.valueChanged.connect(self._time_changed)
        # setup 'Up' button
        self.up_button = QPushButton(self.lang['up_button'], self)
        self.up_button.setToolTip(self.lang['up_button_tt'])
        self.up_button.clicked.connect(self._up)
        # setup 'Down' button
        self.down_button = QPushButton(self.lang['down_button'], self)
        self.down_button.setToolTip(self.lang['down_button_tt'])
        self.down_button.clicked.connect(self._down)
        # setup 'Delete' button
        self.delete_button = QPushButton(self.lang['delete_button'], self)
        self.delete_button.setToolTip(self.lang['delete_button_tt'])
        self.delete_button.clicked.connect(self._delete)
        # setup 'Add' button
        self.add_button = QPushButton(self.lang['add_button'], self)
        self.add_button.setToolTip(self.lang['add_button_tt'])
        self.add_button.clicked.connect(self._add)
        # setup 'Close' button
        self.close_button = QPushButton(
            self.lang['settings_close_button'], self
        )
        self.close_button.setToolTip(self.lang['settings_close_button_tt'])
        self.close_button.clicked.connect(self.hide)  # close, destroy - bugs
        # setup one h box layout
        self.h_box = QHBoxLayout()
        self.h_box.addWidget(self.update_label)
        self.h_box.addWidget(self.time_edit)
        # setup two h box layout
        self.h_box2 = QHBoxLayout()
        self.h_box2.addWidget(self.up_button)
        self.h_box2.addWidget(self.down_button)
        # setup v box layout
        self.v_box = QVBoxLayout(self)
        self.v_box.addWidget(self.list)
        self.v_box.addLayout(self.h_box)
        self.v_box.addLayout(self.h_box2)
        self.v_box.addWidget(self.delete_button)
        self.v_box.addWidget(self.add_button)
        self.v_box.addWidget(self.close_button)
        self.setLayout(self.v_box)
        # show
        self.show()

    def _list_fill(self):
        try:
            self.list.clear()
            for i in range(self.main.list.count()):
                m_item = self.main.list.item(i)
                item = QListWidgetItem(self.list)
                item.setText(m_item.text())
                item.setIcon(m_item.icon())
                self.list.addItem(item)
            self.list.setCurrentRow(0)
        except:
            print(traceback.format_exc())

    def _time_changed(self):
        try:
            self.main.update_timer.stop()
            if self.time_edit.value():
                value = self.time_edit.value()
            else:
                value = 0
            if value > 0:
                self.main.timer_interval = value*1000
                self.main.update_timer.start(self.main.timer_interval)
            else:
                self.main.timer_interval = 0
            self.main.widget_manager.config.config[self.main.NAME]['timer'] =\
                str(self.main.timer_interval)
            self.main.widget_manager.config.save()
        except:
            print(traceback.format_exc())

    def _move(self, up=True):
        try:
            row = self.list.currentRow()
            if up and row-1 >= 0:
                self.main.servers.insert(row-1, self.main.servers.pop(row))
                row -= 1
            elif not up and row+1 < self.list.count():
                self.main.servers.insert(row+1, self.main.servers.pop(row))
                row += 1
            else:
                return
            self.main.widget_manager.config.config[self.main.NAME][
                'servers'] = json.dumps(self.main.servers)
            self.main.widget_manager.config.save()
            self.main._list_fill()
            self._list_fill()
            self.list.setCurrentRow(row)
        except:
            print(traceback.format_exc())

    def _up(self):
        self._move()

    def _down(self):
        self._move(False)

    def _delete(self):
        try:
            if not self.list.count():
                return
            mbox = QMessageBox(self)
            mbox.setIcon(QMessageBox.Question)
            mbox.setWindowIcon(QIcon(DELETE))
            mbox.setWindowTitle(self.lang['confirm_title'])
            mbox.setText(self.lang['confirm_text'])
            mbox.setInformativeText(
                self.lang['confirm_inf'].format(
                    self.list.currentItem().text()))
            mbox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
            ok = mbox.button(QMessageBox.Ok)
            ok.setText(self.lang['confirm_ok_button'])
            ok.setToolTip(self.lang['confirm_ok_button_tt'])
            cancel = mbox.button(QMessageBox.Cancel)
            cancel.setText(self.lang['confirm_cancel_button'])
            cancel.setToolTip(self.lang
                              ['confirm_cancel_button_tt'])
            if mbox.exec() == QMessageBox.Ok:
                del self.main.servers[self.list.currentRow()]
                self.main.widget_manager.config.config[self.main.NAME][
                    'servers'] = json.dumps(self.main.servers)
                self.main.widget_manager.config.save()
                self.main._list_fill()
                self._list_fill()
        except:
            print(traceback.format_exc())

    def _add(self):
        try:
            id = QInputDialog(self)
            id.setWindowIcon(QIcon(HELP))
            id.setWindowTitle(self.lang['input_title'])
            id.setLabelText(self.lang['input_text'])
            id.setTextValue('s.vomine.ru:25565')
            id.setOkButtonText(self.lang['input_ok_button'])
            id.setCancelButtonText(
                self.lang['input_cancel_button'])
            if id.exec() == QInputDialog.Accepted:
                text = id.textValue()
                if not text or len(text.split(':')) != 2\
                        or not text.split(':')[1].isdigit():
                    self._show_error()
                else:
                    self.main.servers.append(text)
                    self.main.widget_manager.config.config[self.main.NAME][
                        'servers'] = json.dumps(self.main.servers)
                    self.main.widget_manager.config.save()
                    self.main._list_fill()
                    self._list_fill()
                    self.list.setCurrentRow(self.list.count()-1)
        except:
            print(traceback.format_exc())

    def _show_error(self):
        try:
            mbox = QMessageBox(self)
            mbox.setIcon(QMessageBox.Critical)
            mbox.setWindowIcon(QIcon(ERROR))
            mbox.setWindowTitle(self.lang['error_title'])
            mbox.setText(self.lang['error_text'])
            mbox.setStandardButtons(QMessageBox.Ok)
            ok = mbox.button(QMessageBox.Ok)
            ok.setText(self.lang['error_ok_button'])
            ok.setToolTip(self.lang['error_ok_button_tt'])
            mbox.exec()
        except:
            print(traceback.format_exc())
