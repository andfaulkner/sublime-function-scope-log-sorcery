# Sublime Scoped Log Inject

Allows insertion of a function & class name-containing log:
    If current line is inside a method, constructor, or class-property-bound function, outputs:

        console.log("$CLASS_NAME :: $FUNCTION_NAME :: $END_CARET_HERE");

    If only a function is present: 
        
        console.log("$FUNCTION_NAME :: $END_CARET_HERE"); 

Also displays the current file, class and function name on the status bar in Sublime Text 2 and 3.

# Keymap:
*   alt-shift-l :: insert console.log with the current sope

## Why The Fork?

At the time of the fork, class name display did not work for .py files in ST3. It fixes that.

## Installation

### Linux or Mac OS / OSX

    cd ~/.config/sublime-text-3/Packages/
    git clone https://github.com/andfaulkner/sublime-function-scope-log-sorcery.git

# NOTE: WIP
All aforementioned features work, but it has a number of limitations that limit its usefulness.
These will be fixed in the extremely near future.
