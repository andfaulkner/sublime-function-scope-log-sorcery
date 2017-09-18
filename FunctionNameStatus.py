import sublime
import sublime_plugin

import re
import sys
from time import time

def get_function_regions(view):
    """
    Get all function regions
    """
    # Example: class Klass { matchesThisName() { ... } }
    method_region = view.find_by_selector('meta.class meta.method.declaration meta.definition.method entity.name.function')
    # Example: class Klass { matchesThisName = () => { ... } }
    bound_method_region = view.find_by_selector('meta.class meta.field.declaration meta.definition.property entity.name.function')
    # Example: function asdf { }
    standard_func_region = view.find_by_selector('(source meta.function meta.definition.function entity.name.function) - meta.funciton.inline')
    # Example: const func = (resMsg) => "ok"
    named_arrow_func_region = view.find_by_selector('(meta.var.expr meta.var-single-variable.expr meta.definition.variable entity.name.function) - meta.arrow')
    # Example: class Klass { events: matchesThisFunctionName = () => '...' }
    obj_lit_func = view.find_by_selector(
        '(meta.class meta.field.declaration meta.objectliteral meta.object.member meta.object-literal entity.name.function) - meta.class meta.arrow')
    function_regions = named_arrow_func_region + standard_func_region + obj_lit_func + bound_method_region + method_region # + named_arrow_in_arrow
    for r in function_regions:
        print('r:', r)
    return function_regions

def generate_class_name_text(view, region_row):
    """
    Generate class name text
    """
    class_name_maybe = ""
    class_regions = view.find_by_selector('entity.name.type.class')
    print('class regions:', class_regions)
    for r in reversed(class_regions):
        row, col = view.rowcol(r.begin())
        if row <= region_row:
            class_name_maybe = view.substr(r)
            print('class name:', view.substr(r))
            found = True
            break

    return class_name_maybe

def generate_function_scope_text(view, region_row):
    """
    Generate text for immediately surrounding function (or method)
    """
    out = ""
    # List of regions (containing start & end points for all functions
    function_regions = get_function_regions(view)

    if function_regions:
        for r in reversed(function_regions):
            row, col = view.rowcol(r.begin())
            if row <= region_row:
                print("row:", row)
                if Pref.display_class and out:
                    out += "::"
                lines = view.substr(r).splitlines()
                name = clean_name.sub('', lines[0])
                print("func name:", name)
                if Pref.display_arguments:
                    out += name.strip()
                else:
                    if 'C++' in view.settings().get('syntax'):
                        if Pref.display_class or len(name.split('(')[0].split('::'))<2:
                            out += name.split('(')[0].strip()
                        else:
                            out += name.split('(')[0].split('::')[1].strip()
                    else:
                        out += name.split('(')[0].split(':')[0].strip()
                found = True
                break
    return out

def clean_class_and_function_str(s):
    re.sub(r' *= *$', '', s)

# Ideas taken from C0D312, nizur & tito in
# http://www.sublimetext.com/forum/viewtopic.php?f=2&t=4589
# Also, from https://github.com/SublimeText/WordHighlight/blob/master/word_highlight.py

def plugin_loaded():
    global Pref

    class Pref:
        def load(self):
            Pref.display_file      = settings.get('display_file', False)
            Pref.display_class     = settings.get('display_class', False)
            Pref.display_function  = settings.get('display_function', True)
            Pref.display_arguments = settings.get('display_arguments', False)
            Pref.wait_time         = 0.12
            Pref.time              = time()
    
    settings = sublime.load_settings('Function Name Display.sublime-settings')
    Pref = Pref()
    Pref.load()
    settings.add_on_change('reload', lambda:Pref.load())

if sys.version_info[0] == 2:
    plugin_loaded()

clean_name = re.compile('^\s*(public\s+|private\s+|protected\s+|static\s+|function\s+|def\s+)+', re.I)

class FunctionNameStatusEventHandler(sublime_plugin.EventListener):
    # on_activated_async seems to not fire on startup
    def on_activated(self, view):
        Pref.time = time()
        view.settings().set('function_name_status_row', -1)
        sublime.set_timeout(lambda:self.display_current_class_and_function(view, 'activated'), 0)

    # why is it here?
    def on_modified(self, view):
        Pref.time = time()

    # could be async, but ST2 does not support that
    def on_selection_modified(self, view):
        now = time()
        if now - Pref.time > Pref.wait_time:
            sublime.set_timeout(lambda:self.display_current_class_and_function(view, 'selection_modified'), 0)
        else:
            sublime.set_timeout(lambda:self.display_current_class_and_function_delayed(view), int(1000*Pref.wait_time))
        Pref.time = now

    def display_current_class_and_function_delayed(self, view):
        now = time()
        if (now - Pref.time >= Pref.wait_time):
            self.display_current_class_and_function(view, 'selection_modified:delayed')

    # display the current class and function name
    def display_current_class_and_function(self, view, where):
        # print("display_current_class_and_function running from " + where)
        view_settings = view.settings()
        if view_settings.get('is_widget'):
            return

        for region in view.sel():
            region_row, region_col = view.rowcol(region.begin())

            print('region:', region)
            print('region row & col:', view.rowcol(region.begin()))

            if region_row != view_settings.get('function_name_status_row', -1):
                view_settings.set('function_name_status_row', region_row)
            else:
                return

            s = ""
            found = False

            fname = view.file_name()
            if Pref.display_file and None != fname:
                 s = fname + " "

            # Look for any classes
            if Pref.display_class:
                s += generate_class_name_text(view, region_row)

            # Look for any functions
            if Pref.display_function:
                s += generate_function_scope_text(view, region_row)

            s = clean_class_and_function_str(s)

            if not found:
                view.erase_status('function')
                fname = view.file_name()
                if Pref.display_file and None != fname:
                    view.set_status('function', fname)
            else:
                # Set the status in the bottom bar
                view.set_status('function', s)

            print("function name:", s)
            return

        view.erase_status('function')

class TestNewCmdCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        """
        Create a log with the scope in it
        """
        print("RAN!")
    
