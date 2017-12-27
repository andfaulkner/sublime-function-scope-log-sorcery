import sublime
import sublime_plugin

import re
import sys
from time import time


#**************************************** UTLITY FUNCTIONS ****************************************#
def get_function_regions(view):
    """Get all function regions. They're numeric (start, end) coordinate pairs """
    # Example: class Klass { matchesThisName() { ... } }
    # method_region = view.find_by_selector('meta.class meta.method.declaration ((meta.definition.method entity.name.function) | storage.type)')
    method_region = view.find_by_selector('meta.class meta.method.declaration')
    # print('method_region:', method_region)

    # Example: class Klass { matchesThisName = () => { ... } }
    bound_method_region = view.find_by_selector('meta.class meta.field.declaration meta.definition.property entity.name.function')
    # Example: function asdf { }
    standard_func_region = view.find_by_selector('(source meta.function meta.definition.function entity.name.function) - meta.funciton.inline')
    # Example: const func = (resMsg) => "ok"
    named_arrow_func_region = view.find_by_selector('(meta.var.expr meta.var-single-variable.expr meta.definition.variable entity.name.function) - meta.arrow')
    # Example: class Klass { events: matchesThisFunctionName = () => '...' }
    obj_lit_func = view.find_by_selector(
        '(meta.class meta.field.declaration meta.objectliteral meta.object.member meta.object-literal entity.name.function) - meta.class meta.arrow')

    wrapped_bound_method_region = view.find_by_selector('source meta.class meta.field.declaration meta.definition.property variable.object.property')
    # source.tsx meta.class.tsx meta.field.declaration.tsx meta.definition.property.tsx variable.object.property.tsx

    function_regions = named_arrow_func_region + standard_func_region + obj_lit_func + method_region + bound_method_region + wrapped_bound_method_region # + named_arrow_in_arrow
    # for r in function_regions: print('get_function_regions :: Current region: value:', r)
    return function_regions

def generate_class_name_text(view, region_row):
    """Generate class name text"""
    class_regions = view.find_by_selector('entity.name.type.class')
    # print("generate_class_name_text :: class regions:', class_regions)
    for r in reversed(class_regions):
        row, col = view.rowcol(r.begin())
        if row <= region_row:
            return view.substr(r), True
    return "", False

def generate_function_name_text(view, region_row, had_class):
    """Generate text for immediately surrounding function (or method)"""
    out = ""
    # List of regions (containing start & end points for all functions
    function_regions = get_function_regions(view)
    function_regions.sort()
    div_space = Pref.space_around_class_and_func_divider
    # print('function_regions:', function_regions)

    if function_regions:
        for r in reversed(function_regions):
            row, col = view.rowcol(r.begin())
            # print('r:', r, 'r.begin():', r.begin(), 'r.end():', r.end(), 'row:', row, ', col:', col, ' region_row:', region_row, 'view.substr(r):', view.substr(r))

            if row <= region_row:
                # print("generate_function_name_text :: current row:", row)
                if Pref.display_class and had_class:
                    if div_space: out += " # "
                    else: out += "#"
                lines = view.substr(r).splitlines()
                name = clean_name.sub('', lines[0])
                # print('name:', name)
                # print('Pref.display_class:', Pref.display_class)
                # print("generate_function_name_text :: func name after clean:", name)
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
                break
    return out, True if out != "" else False

def clean_class_and_function_str(s):
    return re.sub(r' *= *$', '', s)

def generate_class_and_function_string(view, region_row):
    """Build the full class & function scope as a string"""
    s = ""
    found = False
    had_class = False
    had_func = False

    # Handle file name
    fname = view.file_name()
    if Pref.display_file and None != fname:
        s += fname + " "
        # print("generate_class_and_function_string :: display_file  :: s:", s)

    # Look for any classes
    if Pref.display_class:
        class_name_text, had_class = generate_class_name_text(view, region_row)
        found = found or had_func
        s += class_name_text
        # print("generate_class_and_function_string :: display_class  :: s:", s)

    # Look for any functions
    if Pref.display_function:
        func_name_text, had_func = generate_function_name_text(view, region_row, had_class)
        found = found or had_func
        s += func_name_text
        # print("generate_class_and_function_string :: display_function  :: s:", s)

    # Clean result
    s = clean_class_and_function_str(s)
    # print ("generate_class_and_function_string :: final :: s ::", s)
    return s


#****************************************** MAIN PLUGIN *******************************************#
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
            Pref.log_function      = settings.get('log_function', 'console.log')
            Pref.func_data_div     = settings.get('func_data_div', ' :: ')

            Pref.wait_time         = 0.12
            Pref.time              = time()
            Pref.space_around_class_and_func_divider = settings.get(
                'space_around_class_and_func_divider', True)

    settings = sublime.load_settings('scoped-log-inject.sublime-settings')
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
        # print('FunctionNameStatusEventHandler # on_selection_modified ran!')
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
            # print('region:', region, ';;  region row & col:', view.rowcol(region.begin()))

            if region_row != view_settings.get('function_name_status_row', -1):
                view_settings.set('function_name_status_row', region_row)
            else:
                return

            s = generate_class_and_function_string(view, region_row)
            # print("raw generated s (by generate_class_and_function_string):", s)

            # Handle condition where we failed to generate output string
            if s == '':
                view.erase_status('function')
                fname = view.file_name()
                if Pref.display_file and None != fname:
                    view.set_status('function', fname)
            else:
                # print('status being set, to:', s)
                # Set the status in the bottom bar
                view.set_status('function', s)

            # print("display_current_class_and_function :: file (?) + function + class name:", s)
            return

        # view.erase_status('function')

#**************************************** HANDLE INSERTION ****************************************#
class LogWithScopeInfoCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        """Create a log with the scope in it"""
        # print("LogWithScopeInfoCommand # run :: ran!")
        self.edit = edit
        self.create_log_with_function_class(self.view)

    def create_log_with_function_class(self, view):
        view_settings = view.settings()
        if view_settings.get('is_widget'):
            return

        for region in view.sel():
            region_row, region_col = view.rowcol(region.begin())
            # print('region:', region, ';;  region row & col:', view.rowcol(region.begin()))

            s = generate_class_and_function_string(view, region_row)
            # print("s: name generated by generate_class_and_function_string:", s)

            # Handle condition where we failed to generate output string
            if s == '':
                # print("create_log_with_function_class :: function name to insert:", s)
                self.view.insert(self.edit, self.view.sel()[0].begin(), Pref.log_function + "(``);".format(s))
            else:
                # print("create_log_with_function_class :: function name to insert:", s)
                self.view.insert(self.edit, self.view.sel()[0].begin(), Pref.log_function + "(`{0}{1}`);".format(s, Pref.func_data_div))

        for _ in range(1, 4):
            self.view.run_command("move", {"by": "characters", "forward": False})

