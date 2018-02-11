"""Edit gui settings app."""
import os
import sys
import logging
from enum import IntEnum
from distutils.util import strtobool
from configparser import RawConfigParser
from PyQt5.QtWidgets import QWidget, QPushButton, QCheckBox, QComboBox, QLabel
from PyQt5.QtWidgets import QMessageBox, QGridLayout, QHBoxLayout
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
from core.gui.del_widgets import Delete
from core.paths import SETTINGS, SUCCESS, LANGS, CONF_SETTINGS
from core.utils import try_except, print_stack_trace


class LogLevel(IntEnum):
    """logging levels"""
    NOTSET = logging.NOTSET
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL

    @staticmethod
    def from_string(s) -> int:
        """Get int level from string key.

        :param s: str, key
        :return: int, level (not enum) (raise NameError if not found)
        """
        if s in LogLevel._member_names_:
            return int(LogLevel._member_map_[s])
        raise NameError(str(s) + ' not found')

    @staticmethod
    def from_int(num) -> str:
        """Get string key from int level.

        :param num: int, level
        :return: str, key (raise ValueError if not found)
        """
        if num == logging.NOTSET:
            return 'NOTSET'
        elif num == logging.DEBUG:
            return 'DEBUG'
        elif num == logging.INFO:
            return 'INFO'
        elif num == logging.WARNING:
            return 'WARNING'
        elif num == logging.ERROR:
            return 'ERROR'
        elif num == logging.CRITICAL:
            return 'CRITICAL'
        else:
            raise ValueError(str(num) + ' not found')

    @staticmethod
    def get_keys() -> tuple:
        """Get all string keys.

        :return: tuple, str keys
        """
        return tuple(LogLevel._member_names_)


class Settings(QWidget):
    """settings window"""
    def __init__(self, lang, main, settings):
        """

        :param lang: dict, current locale
        :param main: core.gui.gui.Main object
        :param settings: dict, current settings
        """
        super().__init__()
        self.lang = lang['SETTINGS']
        self.orig_lang = lang
        self.main = main
        self.settings = settings
        self._items = {}
        self._changed = False
        self.del_widgets_win = None
        # setup window
        self.setWindowTitle(self.lang['title'])
        self.setWindowIcon(QIcon(SETTINGS))
        self.resize(290, 200)
        self.setWindowFlags(Qt.WindowMinimizeButtonHint |
                            Qt.WindowCloseButtonHint)
        # setup 'Languages' lebel
        self.label_loc = QLabel(self.lang['label_loc'], self)
        self.label_loc.setAlignment(Qt.AlignCenter)
        # setup languages list
        self.language = QComboBox(self)
        self.language.setToolTip(self.lang['language_tt'])
        self.language.activated.connect(self._change_settings)
        self._langs_box_fill()
        # setup log level label
        self.label_log = QLabel(self.lang['label_log'])
        self.label_log.setAlignment(Qt.AlignCenter)
        # setup levels list
        self.log_levels = QComboBox(self)
        self.log_levels.setToolTip(self.lang['levels_tt'])
        self.log_levels.activated.connect(self._change_settings)
        self._logs_box_fill()
        # setup 'Load placed' checkbox
        self.load_placed = QCheckBox(self.lang['load_placed'], self)
        self.load_placed.setToolTip(self.lang['load_placed_tt'])
        if strtobool(settings['MAIN']['load_placed']):
            self.load_placed.setChecked(True)
        self.load_placed.stateChanged.connect(self._change_settings)
        # setup widgets delete button
        self.del_button = QPushButton(self.lang['del_button'], self)
        self.del_button.setToolTip(self.lang['del_button_tt'])
        self.del_button.clicked.connect(self._show_del_widgets)
        # setup 'Save' button
        self.save_button = QPushButton(self.lang['save_button'], self)
        self.save_button.setToolTip(self.lang['save_button_tt'])
        self.save_button.clicked.connect(self._save)
        # setup 'Cancel' button
        self.cancel_button = QPushButton(self.lang['cancel_button'], self)
        self.cancel_button.setToolTip(self.lang['cancel_button_tt'])
        self.cancel_button.clicked.connect(self._cancel)
        # setup h box layout
        self.h_box = QHBoxLayout()
        self.h_box.addWidget(self.save_button)
        self.h_box.addWidget(self.cancel_button)
        # setup grid layout
        self.grid = QGridLayout(self)
        self.grid.addWidget(self.label_loc, 0, 0)
        self.grid.addWidget(self.language, 0, 1)
        self.grid.addWidget(self.label_log, 1, 0)
        self.grid.addWidget(self.log_levels, 1, 1)
        self.grid.addWidget(self.load_placed, 2, 0, 1, 2)
        self.grid.addWidget(self.del_button, 3, 0, 1, 2)
        self.grid.addLayout(self.h_box, 4, 0, 1, 2)
        self.setLayout(self.grid)
        # show
        self.show()

    def _change_settings(self):
        self._changed = True

    def _langs_box_fill(self):
        for name in os.listdir(LANGS):
            try:
                file = os.path.join(LANGS, name)
                conf = RawConfigParser()
                conf.read(file)
                # checks
                if 'LANG' not in conf:
                    continue
                cont = False
                for key in ('name', 'description', 'language', 'country'):
                    if key not in conf['LANG']:
                        cont = True
                        break
                if cont:
                    continue
                # fill
                item = conf['LANG']['name'] + ' ('
                item += conf['LANG']['description'] + ')'
                self.language.addItem(item)
                if name[:-5] == self.settings['MAIN']['locale']:
                    self.language.setCurrentText(item)
                self._items[item] = name[:-5]
            except:
                print_stack_trace()()

    @try_except()
    def _logs_box_fill(self):
        for key in LogLevel.get_keys():
            try:
                self.log_levels.addItem(key)
            except:
                print_stack_trace()()
        self.log_levels.setCurrentText(LogLevel.from_int(
            int(self.settings['LOGS']['log_level'])))

    @try_except()
    def _save(self, checked):
        self.settings['MAIN']['locale'] = \
            self._items[self.language.currentText()]
        self.settings['MAIN']['load_placed'] = \
            str(self.load_placed.isChecked())
        self.settings['LOGS']['log_level'] = \
            str(LogLevel.from_string(self.log_levels.currentText()))
        with open(CONF_SETTINGS, 'w') as file:
            self.settings.write(file)
        if self._changed:
            self._show_warn()
        self.main._list_fill()
        # strange bug: open from tray (main win hide),
        # call self.close() -> exit app
        self.destroy()

    @try_except()
    def _cancel(self, checked):
        self.main._list_fill()
        self.destroy()

    def _show_warn(self):
        mbox = QMessageBox(QMessageBox.Warning, self.lang['warn_title'],
                           self.lang['warn_text'], QMessageBox.Ok, self)
        mbox.setWindowIcon(QIcon(SUCCESS))
        ok = mbox.button(QMessageBox.Ok)
        ok.setText(self.lang['warn_ok_button'])
        ok.setToolTip(self.lang['warn_ok_button_tt'])
        mbox.exec()

    @try_except()
    def _show_del_widgets(self, checked):
        self.del_widgets_win = Delete(self.orig_lang,
                                      sys.modules['core.gui.gui'].manager)
