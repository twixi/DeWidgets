"""Manage widgets."""
import os
import sys
import inspect
from distutils.util import strtobool
from configparser import RawConfigParser
from importlib.machinery import SourceFileLoader
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt
import widgets as w
from core.paths import CONF_WIDGETS, C_WIDGETS
from core.utils import try_except, print_stack_trace, STDOUT
from core.api import WidgetInfo, Widget
from core.gui.drag import mouse_enter

sys.path.append(C_WIDGETS)
CUSTOM_WIDGETS = SourceFileLoader('__init__',
                                  os.path.join(C_WIDGETS, '__init__.py')
                                  ).load_module()
"""Custom widgets module for *use get_widgets(path)* function."""


class WidgetManager:
    """manage widgets"""
    def __init__(self, lang, c_lang, main):
        """

        :param lang: ConfigParser locale dict
        :param c_lang: ConfigParser locale dict for custom widgets
        :param main: gui module
        """
        self.lang = lang
        """RawConfigParser dict, current locale."""
        self.c_lang = c_lang
        """RawConfigParser dict, current locale for custom widgets"""
        self.widgets = {}
        """Widgets dict, key - name, value - widget object (Main object)."""
        self.info = {}
        """WidgetInfo dict, key - name, value - WidgetInfo object"""
        self.custom_widgets = []
        """Custom widgets names list."""
        self.paths = {}
        """Paths to widget files. Keys - names, values - paths to files."""
        self.config = ConfigManager(self)
        """ConfigManager object"""
        self.main_gui = main
        """core.gui.gui module"""
        self.logger = STDOUT
        """stdout logger"""

    def load_all(self):
        """Loading all widgets."""
        for name in w.get_widgets():
            self.load(name)
        for name in CUSTOM_WIDGETS.get_widgets():
            self.load(name)

    def load_placed(self, placed=True):
        """Loading placed widgets.

        :param placed: bool, True - only placed, False - only hidden
        """
        if not placed:
            for name in w.get_widgets():
                if name not in sys.modules:
                    self.load(name)
            for name in CUSTOM_WIDGETS.get_widgets():
                if name not in sys.modules:
                    self.load(name)
            return
        for name in self.config.config:
            if name == 'DEFAULT' or name in self.widgets:
                continue
            if self.config.is_placed(name):
                self.load(self.config.config[name]['file'])

    def load_new(self):
        """Loading only new widgets (not loaded before)."""
        for name in w.get_widgets():
            if name not in sys.modules:
                self.load(name)
        for name in CUSTOM_WIDGETS.get_widgets():
            if name not in sys.modules:
                self.load(name)

    def load(self, module_name, only_info=True) -> bool:
        """Load widget from module.

        :param module_name: str, module name
        :param only_info: bool, if True - load only WidgetInfo classes
        :return: bool, True if load correctly
        """
        @try_except(lambda: False)
        def return_false():
            if module_name in sys.modules:
                del sys.modules[module_name]
            return False

        try:
            if module_name in sys.modules:  # get module
                mod = sys.modules[module_name]
            else:  # import module
                mod = __import__(module_name)
            # validate module
            if not self.validate_widget_module(mod):
                self.logger.info(module_name + ' fail validation module')
                return return_false()
            if self.is_loading_skip(mod):
                self.logger.debug(module_name + ' skipped')
                return return_false()
            # init and validate WidgetInfo
            info = mod.Info(self.lang)
            if not self.validate_widget_info(info):
                self.logger.info(module_name + ' fail validation WidgetInfo')
                return return_false()
            # check exists
            if only_info:
                if info.NAME in self.info:
                    self.logger.info(module_name + ', name "' + info.NAME +
                                     '" is exists')
                    return return_false()
            elif info.NAME in self.widgets:
                self.logger.info(module_name + ', name "' + info.NAME +
                                 '" is exists')
                return return_false()
            # fill data
            if os.path.dirname(mod.__file__) == C_WIDGETS:
                if info.NAME in self.custom_widgets:  # check exists
                    self.logger.info(module_name + ', name "' + info.NAME +
                                     '" is exists')
                    return return_false()
                else:
                    self.custom_widgets.append(info.NAME)
            self.info[info.NAME] = info
            self.paths[info.NAME] = mod.__file__
            if only_info and not self.config.is_placed(info.NAME):
                return True
            # init and validate Main class
            widget = mod.Main(self, info)
            if not self.validate_widget_main(widget):
                self.logger.info(module_name + ' fail validation Main')
                return return_false()
            # setup Main class
            self.setup_widget(widget, info)
            self.widgets[info.NAME] = widget
            self.config.load(info.NAME)
            self.call_load_other(info.NAME)
            return True
        except:
            print_stack_trace()()
            self.logger.error(module_name + ' fail loading')
            return return_false()

    @staticmethod
    def is_loading_skip(mod):
        """Check not_loading option in module.

        :param mod: module object
        :return: True if not_loading == True
        """
        if 'not_loading' in mod.__dict__ and mod.__dict__['not_loading']:
            return True
        return False

    @staticmethod
    def validate_widget_module(mod) -> bool:
        """Check widget module.

        :param mod: module object
        :return: bool, True if module is correct
        """
        if 'not_loading' in mod.__dict__ and \
                type(mod.__dict__['not_loading']) != bool:
            return False
        if 'Main' not in mod.__dict__ or not callable(mod.Main):
            return False
        if 'Info' not in mod.__dict__ or not callable(mod.WidgetInfo):
            return False
        return True

    @staticmethod
    def validate_widget_info(info) -> bool:
        """Check WidgetInfo class.

        :param info: WidgetInfo object
        :return: bool, True if WidgetInfo is correct
        """
        if not isinstance(info, WidgetInfo):
            return False
        return True

    @staticmethod
    def validate_widget_main(widget) -> bool:
        """Check widget Main object.

        :param widget: Widget object
        :return: bool, True if Widget is correct
        """
        if not isinstance(widget, Widget) or not isinstance(widget, QWidget):
            return False
        return True

    def setup_widget(self, widget, info):
        """Setup widget Main object (set window flags and other).

        :param widget: Widget object
        :param info: WidgetInfo object
        """
        widget.load()
        widget.setWindowFlags(Qt.CustomizeWindowHint |
                              Qt.WindowStaysOnBottomHint | Qt.Tool)
        widget.setWindowTitle(info.NAME)
        widget.setAccessibleName(info.NAME)
        widget.setWindowIcon(info.ICON)
        widget.enterEvent = mouse_enter(self, widget)(widget.enterEvent)

    @try_except()
    def remove_from_desktop(self, name, reminconf=False):
        """Remove widget from desktop.

        :param name: str, widget name
        :param reminconf: bool, True - remove widget all data from config
        """
        self.call_purge_other(name, reminconf)
        if reminconf:
            try:
                self.widgets[name].purge()
            except:
                print_stack_trace()()
        else:
            try:
                self.widgets[name].remove()
            except:
                print_stack_trace()()
            self.config.add(name)
        try:
            self.widgets[name].close()
        except:
            print_stack_trace()()
        self.unload(name)
        self.config.set_placed(name, False)
        if reminconf:
            self.config.remove(name)
        self.config.save()

    @try_except()
    def delete_widget(self, name):
        """Remove widget file (after remove widget data from config
        and unload). For only placed widgets.

        :param name: str, widget name
        """
        self.call_delete_other_widget(name)
        path = self.paths[name]
        try:
            self.widgets[name].delete_widget()
        except:
            print_stack_trace()()
        self.remove_from_desktop(name, True)
        try:
            self.widgets[name].unload()
        except:
            print_stack_trace()()
        self.unload(name)
        self.config.remove(name)  # warranty
        self.del_from_dicts(name)
        os.remove(path)

    @try_except(lambda: False)
    def call_delete_widget(self, module_name) -> bool:
        """Call widget API (delete_widget and unload). Load -> call -> unload.

        :param module_name: str, module name
        :return: bool, True if success, False if bad validation or except
        """
        if module_name not in sys.modules:
            return False
        mod = sys.modules[module_name]
        # validate module
        if not self.validate_widget_module(mod):
            return False
        # init and validate info
        info = mod.Info(self.lang)
        if not self.validate_widget_info(info):
            return False
        # init and validate widget
        widget = mod.Main(self, info)
        if not self.validate_widget_main(widget):
            return False
        # call
        self.call_delete_other_widget(info.NAME)
        widget.delete_widget()
        return True

    @try_except()
    def del_from_dicts(self, name, module_name=None):
        """Remove data from info, paths dict, custom_widgets and sys.modules.
        Call unload and this - fully unload widget from runtime.

        :param name: str, widget name
        :param module_name: str, module name (if None - using self.paths)
        """
        if not module_name:
            module_name = os.path.basename(self.paths[name])[:-3]
        del self.info[name]
        del self.paths[name]
        if name in self.custom_widgets:
            self.custom_widgets.remove(name)
        del sys.modules[module_name]

    @try_except()
    def unload(self, name):
        """Unload Widget object (only Main class) from runtime. Destroy.

        :param name: str, widget name
        """
        self.call_unload_other(name)
        try:
            self.widgets[name].unload()
            self.widgets[name].close()
            self.widgets[name].deleteLater()
        except:
            print_stack_trace()()
        del self.widgets[name]

    @try_except()
    def unload_all(self, del_from_dicts=True):
        """Unload all loaded widgets.

        :param del_from_dicts: bool, if True - like del_from_dicts"""
        for name in list(self.widgets.keys()):
            self.unload(name)
            if del_from_dicts:
                self.del_from_dicts(name)

    def del_data_no_placed(self):
        """Remove data (from info, paths and sys.modules) only not placed
        widgets."""
        for name in list(self.info.keys()):
            if name not in self.widgets:
                self.del_from_dicts(name)

    def is_placed(self) -> bool:
        """Check the presence of widgets on the desktop.

        :return: bool, True if at least one placed
        """
        for widget in self.widgets.values():
            if widget.isVisible():
                return True
        return False

    def get_config(self, name) -> dict:
        """Get config section for widget.

        :param name: str, widget name
        :return: dict, config section for widget in ConfigParser
        """
        return self.config.config[name]

    def call_end_loading(self):
        """Call end_loading event at all widgets."""
        for widget in self.widgets.values():
            try:
                widget.end_loading()
            except:
                print_stack_trace()()

    def call_load_other(self, name):
        """Call load_other event at all widgets.

        :param name: str, widget name
        """
        for widget in self.widgets.values():
            try:
                widget.load_other(name)
            except:
                print_stack_trace()()

    def call_unload_other(self, name):
        """Call unload_other event at all widgets.

        :param name: str, widget name
        """
        for widget in self.widgets.values():
            try:
                widget.unload_other(name)
            except:
                print_stack_trace()()

    def call_delete_other_widget(self, name):
        """Call delete_other_widget event at all widgets.

        :param name: str, widget name
        """
        for widget in self.widgets:
            try:
                widget.delete_other_widget(name)
            except:
                print_stack_trace()()

    def call_purge_other(self, name, reminconf):
        """Call purge_other event at all widgets.

        :param name: str, widget name
        :param reminconf: bool, True - remove widget all data from config
        """
        for widget in self.widgets.values():
            try:
                widget.purge_other(name, reminconf)
            except:
                print_stack_trace()()

    def edit_mode(self, mode, name=None) -> bool:
        """Call widget event and save config.
        
        :param mode: bool, True - edit on
        :param name: str, widget name (no call other widgets)
        :return: bool, True - success call and save config
        """
        def save(widget):
            try:
                widget.edit_mode(mode)
                if not mode:
                    self.config.add(widget.info.NAME)
            except:
                print_stack_trace()()

        if name and name in self.widgets:
            save(self.widgets[name])
            self.config.save()
            return True
        elif not name:
            for w_object in self.widgets.values():
                save(w_object)
            self.config.save()
            return True
        else:
            return False


class ConfigManager:
    """manage config"""
    def __init__(self, widget_manager):
        self.wm = widget_manager
        """WidgetManager object"""
        self.config = RawConfigParser()
        """RawConfigParser object"""
        try:
            if os.path.isfile(CONF_WIDGETS):
                self.config.read(CONF_WIDGETS, 'UTF-8')
        except:
            print_stack_trace()()

    def load_all(self):
        """Load (setup) only configured widgets."""
        for name in self.config:
            if name not in self.wm.widgets:
                continue
            self.load(name)

    @try_except()
    def load(self, name):
        """Setup widget (set size, position, opacity, call boot and show.

        :param name: str, widget name
        """
        if name not in self.config or name not in self.wm.widgets:
            return
        prop = self.config[name]
        if not prop:
            return
        widget = self.wm.widgets[name]
        widget.resize(int(prop['width']), int(prop['height']))
        widget.move(int(prop['x']), int(prop['y']))
        widget.setWindowOpacity(float(prop['opacity']))
        if self.is_placed(name):
            # if placed, show window
            widget.boot()
            widget.show()

    @try_except()
    def save(self):
        """Save config to file."""
        with open(CONF_WIDGETS, 'w', encoding='UTF-8') as config:
            self.config.write(config)

    @try_except()
    def add(self, name):
        """Add or update widget data in config (not call save).
        Size, position, opacity, placed, file (module name).

        :param name: str, widget name
        """
        widget = self.wm.widgets[name]
        if name in self.config:
            sec = self.config[name]
            sec['width'] = str(widget.width())
            sec['height'] = str(widget.height())
            sec['x'] = str(widget.x())
            sec['y'] = str(widget.y())
            sec['opacity'] = str(widget.windowOpacity())
            sec['placed'] = str(not widget.isHidden())
            sec['file'] = os.path.basename(inspect.getfile(widget.__class__
                                                           ))[:-3]
        else:
            self.config[name] = {
                'width': str(widget.width()),
                'height': str(widget.height()),
                'x': str(widget.x()),
                'y': str(widget.y()),
                'opacity': str(widget.windowOpacity()),
                'placed': str(not widget.isHidden()),
                'file': os.path.basename(inspect.getfile(widget.__class__)
                                         )[:-3]
            }

    @try_except()
    def remove(self, name):
        """Remove widget data from config (not call save).

        :param name: str, widget name
        """
        if name in self.config:
            del self.config[name]

    @try_except()
    def set_placed(self, name, value):
        """Set placed status.

        :param name: str, widget name
        :param value: bool, True - if placed to desktop
        """
        self.config[name]['placed'] = str(value)

    def is_placed(self, name) -> bool:
        """Check widget placed.

        :param name: str, widget name
        :return: bool, True - if widget placed to desktop
        """
        if name in self.config and 'placed' in self.config[name]:
            return bool(strtobool(self.config[name]['placed']))
        else:
            return False

    @try_except()
    def create(self, name):
        """Create section (empty dict) in config for widget.

        :param name: str, widget name
        """
        if name not in self.config:
            self.config[name] = {}

    @try_except()
    def save_positions(self):
        """Save widget positions to config file."""
        for name in self.wm.widgets:
            self.add(name)
        self.save()
