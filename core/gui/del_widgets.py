"""Delete widgets GUI."""
import os
import sys
import json
from configparser import RawConfigParser
from PyQt5.QtWidgets import QWidget, QListWidget, QLabel, QPushButton
from PyQt5.QtWidgets import QMessageBox, QListWidgetItem
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QRect, Qt
from core.gui.help import TextViewer
from core.paths import CONF_INSTALL, DELETE, ZIP, DEL_WIDGETS, DEL_ARCHIVES
from core.utils import try_except, print_stack_trace, STDOUT


def del_in_conf(path, sections):
    """Delete data from config.

    :param path: path to file
    :param sections: dict, "{"TEST": {"name": "lol"}}"
    """
    conf = RawConfigParser()
    conf.read(path, 'utf-8')
    for sec in sections:
        for key in sections[sec]:
            del conf[sec][key]
            STDOUT.debug('remove ' + key + ' key from section ' + sec)
        if not conf[sec]:
            del conf[sec]
            STDOUT.debug('remove section ' + sec)
    with open(path, 'w', encoding='utf-8') as file:
        conf.write(file)
    STDOUT.debug('rewrite ' + path)


class Delete(QWidget):
    def __init__(self, locale, manager):
        """

        :param locale: dict, current locale
        :param manager: WidgetManager object
        """
        # init
        QWidget.__init__(self)
        self.locale = locale
        self.manager = manager
        self.lang = locale['DEL_WIDGETS']
        self.arch_del_win = None
        # setup window
        self.setWindowTitle(self.lang['title'])
        self.setFixedSize(410, 330)
        self.setWindowIcon(QIcon(DEL_WIDGETS))
        # setup widgets list
        self.w_list = QListWidget(self)
        self.w_list.setGeometry(QRect(0, 0, 280, 300))
        self.w_list.setSpacing(2)
        self.w_list.itemClicked.connect(self._list_click)
        self.w_list.itemDoubleClicked.connect(self._list_double_click)
        self._list_fill()
        # setup label
        self.h_label = QLabel(self.lang['label'], self)
        self.h_label.setGeometry(QRect(0, 305, 410, 17))
        self.h_label.setAlignment(Qt.AlignCenter)
        # setup delete button
        self.del_button = QPushButton(self.lang['del_button'], self)
        self.del_button.setGeometry(QRect(300, 10, 94, 29))
        self.del_button.setToolTip(self.lang['del_button_tt'])
        self.del_button.clicked.connect(self._delete)
        # setup archives button
        self.arch_button = QPushButton(self.lang['arch_button'], self)
        self.arch_button.setGeometry(QRect(300, 50, 94, 29))
        self.arch_button.setToolTip(self.lang['arch_button_tt'])
        self.arch_button.clicked.connect(self._arch_delete)
        # setup close button
        self.close_button = QPushButton(self.lang['close_button'], self)
        self.close_button.setGeometry(QRect(300, 270, 94, 29))
        self.close_button.setToolTip(self.lang['close_button_tt'])
        self.close_button.clicked.connect(self.close)
        # show
        self._change_enabled()
        self.show()

    def _change_enabled(self):
        if self.w_list.currentItem():
            self.del_button.setEnabled(True)
        else:
            self.del_button.setEnabled(False)

    @try_except()
    def _list_fill(self):
        self.w_list.clear()
        for name in self.manager.custom_widgets:
            try:
                if name not in self.manager.info:
                    continue
                info = self.manager.info[name]
                item = QListWidgetItem(self.w_list)
                item.setIcon(info.ICON)
                item.setText(info.NAME)
                item.setToolTip(info.DESCRIPTION)
                if self.manager.config.is_placed(info.NAME):
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                self.w_list.addItem(item)
            except:
                print_stack_trace()()

    @try_except()
    def _list_click(self, item):
        self._change_enabled()
        self.h_label.setText(self.manager.info[item.text()].DESCRIPTION)

    @try_except()
    def _list_double_click(self, item):
        self.item_info = sys.modules['core.gui.gui'].ItemInfo(item.text())

    @try_except()
    def _delete(self, checked):
        # check item
        item = self.w_list.currentItem()
        # create message box
        mbox = QMessageBox(QMessageBox.Question, self.lang['del_mbox_title'],
                           self.lang['del_mbox_text'].format(item.text()),
                           QMessageBox.Yes | QMessageBox.No, self)
        mbox.setWindowIcon(QIcon(DELETE))
        yes = mbox.button(QMessageBox.Yes)
        yes.setText(self.lang['del_mbox_yes_button'])
        yes.setToolTip(self.lang['del_mbox_yes_button_tt'])
        no = mbox.button(QMessageBox.No)
        no.setText(self.lang['del_mbox_no_button'])
        no.setToolTip(self.lang['del_mbox_no_button_tt'])
        # process
        if mbox.exec() == QMessageBox.Yes:
            self.del_widget(self.manager.paths[item.text()], item.text())
            self._list_fill()
            self._change_enabled()

    @try_except()
    def _arch_delete(self, checked):
        self.arch_del_win = ArchDelete(self, self.locale, self.manager)

    def del_widget(self, module, name=None):
        """Delete widget.

        :param module: str, path or name module
        :param name: str, widget name (if None - find in manager.paths)
        """
        module_name = os.path.basename(module)[:-3]
        if not name:
            for w_name in self.manager.paths:
                if os.path.basename(self.manager.paths[w_name])[:-3] == \
                        module_name:
                    name = w_name
                    break
        if name and name in self.manager.widgets:
            self.manager.del_widget(name)
            STDOUT.debug('delete widget: ' + name)
        else:
            r = self.manager.call_delete_widget(module_name)
            STDOUT.debug(
                'call delete widget "' + module_name + '", result: ' +
                str(r) + ', deleting...')
            os.remove(module)
            if name:
                self.manager.del_from_dicts(name)
                self.manager.config.remove(name)
                STDOUT.debug('full unload and del info from config: ' + name)
            elif module_name in sys.modules:
                del sys.modules[module_name]
                STDOUT.debug('delete module from sys.modules: ' + module_name)


class ArchDelete(QWidget):
    def __init__(self, main, locale, manager):
        """

        :param main: Delete object
        :param locale: dict, current locale
        :param manager: WidgetManager object
        """
        # init
        QWidget.__init__(self)
        self.main = main
        self.manager = manager
        self.locale = locale
        self.lang = locale['ARCH_DELETE']
        self.setWindowTitle(self.lang['title'])
        self.setFixedSize(410, 330)
        self.setWindowIcon(QIcon(DEL_ARCHIVES))
        self.archives = {}
        # setup widgets list
        self.w_list = QListWidget(self)
        self.w_list.setGeometry(QRect(0, 0, 280, 300))
        self.w_list.setSpacing(2)
        self.w_list.itemClicked.connect(self._list_click)
        self.w_list.itemDoubleClicked.connect(self._list_double_click)
        self._list_fill()
        # setup label
        self.h_label = QLabel(self.lang['label'], self)
        self.h_label.setGeometry(QRect(0, 305, 410, 17))
        self.h_label.setAlignment(Qt.AlignCenter)
        # setup delete button
        self.del_button = QPushButton(self.lang['del_button'], self)
        self.del_button.setGeometry(QRect(300, 10, 94, 29))
        self.del_button.setToolTip(self.lang['del_button_tt'])
        self.del_button.clicked.connect(self._delete)
        # setup close button
        self.close_button = QPushButton(self.lang['close_button'], self)
        self.close_button.setGeometry(QRect(300, 270, 94, 29))
        self.close_button.setToolTip(self.lang['close_button_tt'])
        self.close_button.clicked.connect(self.close)
        # show
        self.__change_enabled()
        self.show()

    def __change_enabled(self):
        if self.w_list.currentItem():
            self.del_button.setEnabled(True)
        else:
            self.del_button.setEnabled(False)

    @try_except()
    def _list_fill(self):
        if not os.path.isfile(CONF_INSTALL):
            return
        with open(CONF_INSTALL, encoding='utf-8') as file:
            self.archives = json.loads(file.read())
        self.w_list.clear()
        for arch in self.archives:
            item = QListWidgetItem(self.w_list)
            item.setIcon(QIcon(ZIP))
            item.setText(os.path.basename(arch))
            item.setToolTip(arch)
            self.w_list.addItem(item)

    @try_except()
    def _list_click(self, item):
        self.__change_enabled()
        self.h_label.setText(item.toolTip())

    @try_except()
    def _list_double_click(self, item):
        self.arch_info = ArchInfo(self.locale, item.toolTip(),
                                  self.archives[item.toolTip()])

    @try_except()
    def _delete(self, checked):
        item = self.w_list.currentItem()
        # create message box
        mbox = QMessageBox(QMessageBox.Question, self.lang['del_mbox_title'],
                           self.lang['del_mbox_text'].format(item.text()),
                           QMessageBox.Yes | QMessageBox.No, self)
        mbox.setWindowIcon(QIcon(DELETE))
        yes = mbox.button(QMessageBox.Yes)
        yes.setText(self.lang['del_mbox_yes_button'])
        yes.setToolTip(self.lang['del_mbox_yes_button_tt'])
        no = mbox.button(QMessageBox.No)
        no.setText(self.lang['del_mbox_no_button'])
        no.setToolTip(self.lang['del_mbox_no_button_tt'])
        # process
        if mbox.exec() == QMessageBox.Yes:
            for py in self.archives[item.toolTip()]['py']:
                if os.path.isfile(py):
                    self.main.del_widget(py)
            for res in self.archives[item.toolTip()]['res']:
                if os.path.isfile(res):
                    os.remove(res)
                    STDOUT.debug('remove ' + res)
            for res in self.archives[item.toolTip()]['res']:
                d = os.path.dirname(res)
                if os.path.isdir(d):
                    os.rmdir(d)
                    STDOUT.debug('remove dir ' + d)
            for lang in self.archives[item.toolTip()]['langs']:
                del_in_conf(lang[0], lang[1])
            del self.archives[item.toolTip()]
            with open(CONF_INSTALL, 'w') as file:
                file.write(json.dumps(self.archives))
            self._list_fill()
            self.main._list_fill()
            self.__change_enabled()
            self.main._change_enabled()


class ArchInfo(TextViewer):
    def __init__(self, locale, name, data):
        """

        :param locale: dict, current locale
        :param name: archive name
        :param data: archive info dict
        """
        # init
        self.lang = locale['ARCH_INFO']
        super().__init__(self.lang['title'].format(os.path.basename(name)),
                         self.lang['exit_button'],
                         self.lang['exit_button_tt'])
        self.setWindowIcon(QIcon(ZIP))
        # setup
        kwargs = {'name': os.path.basename(name), 'path': name}
        py_list = ''
        res_list = ''
        lang_list = ''
        for py in data['py']:
            py_list += self.lang['py_item'].format(os.path.basename(py))
        for res in data['res']:
            res_list += self.lang['res_item'].format(res)
        for lang in data['langs']:
            lang_list += self.lang['lang_item'].format(lang[0])
        kwargs['py_list'] = py_list
        kwargs['res_list'] = res_list
        kwargs['lang_list'] = lang_list
        self.text.setHtml(self.lang['html'].format(**kwargs))
        # show
        self.show()
