import tkinter as tk # linestart lineend current wordend wordstart
import pathlib
import re
import keyword
from collections import deque

# Create more declaration regexs, for class definition (name), loops (no-name) and condition (no-name)

S = r"(?:\s*)"
FUNCTION_DECLARATION_PATTERN = rf"""
    ^
    {S}
    (?P<raw>
        def
        {S}
        (?P<function_name>
            \w+
        )
        {S}
        \(
        {S}
        (?P<params>
            [(\w+),{S}]*
        )
        {S}
        \):
        {S}
    )
    {S}
    $
"""
    
FUNCTION_DECLARATION_REGEX = re.compile(FUNCTION_DECLARATION_PATTERN, re.VERBOSE)

KEYWORDS = keyword.kwlist

OPERATORS = ['\\' + char for char in [
    "+",
    "-",
    "*",
    "/",
    "//",
    "%",
    "**",
    "|",
    "&",
    "<<",
    ">>",
    "==",
    "!=",
    "<",
    "<=",
    ">",
    ">="
    ]]
    
BUILTINS = dir(__builtins__)
    
class HighlightTag:
    
    def __init__(self, tagname, pattern, **property_dict):
        self.pattern = re.compile(pattern) # re.MULTILINE
        self.tagname = tagname
        self.property_dict = property_dict
        
    def add_to_widget(self, text_widget):
        text_widget.tag_configure(self.tagname, **self.property_dict)
        
def spaces_around(pattern): #(?<!\S) same as (?<=\s|^)
    # return rf"(?:(?<=[\s\(])|(?<=^))(?:{pattern})(?:(?=[\s\)])|(?=$))"
    return rf"(?<![\w\.])(?:{pattern})(?![\w\.\(])"

TAGS = [
    # Tags sorted in increasing order of importance, comment is the last to be applied and overwrites everything
    # Matching the char before becaue not look behind avaible in tcl (Lookahead (?=foo), lookbehind (?<=foo)) replace = by !
        HighlightTag("keyword", spaces_around('|'.join(KEYWORDS)), foreground="#FFA500"),
        HighlightTag("function", r"(?<![\w\)])\w+(?=\()", foreground="#0000FF"),
        HighlightTag("builtins",rf"(?<![\w\)])(?:{'|'.join(BUILTINS)})(?![\w\.])", foreground="#00A5A5"),
        HighlightTag("operators",rf"(?:{'|'.join(OPERATORS)})", foreground="#00FF00"),
        HighlightTag("number", spaces_around(r"\d+\.?\d*"), foreground="#FF0000"),
        HighlightTag("quotes", r'[FfrRuU]?".*"', foreground="#B0B000"),
        HighlightTag("comments", r"#.+$", foreground="#808080")
    ]

class Application(tk.Tk):
    
    def __init__(self, filename: str, width: int = 800, height: int = 500, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # creating empty variables
        self.last_line_edited = 0
        self.widgets_to_pack = set()
        self.content = None
        
        # The file
        file = pathlib.Path(filename)
        if file.exists():
            self.filename = filename
            self.read_file_content()
        else:
            raise ValueError("File doesn't exist")
        
        # tk.Tk property
        self.geometry(f"{width}x{height}")
        self.width = width
        self.height = height
        
        # The mainframe
        self.mainframe = tk.Frame(self, width=300, height=150)
        self.mainframe.grid_propagate(False)
        self.mainframe.grid_rowconfigure(0, weight=1)
        self.mainframe.grid_columnconfigure(0, weight=1)
        
        # Other widgets
        self.setup_widgets()
        self.set_text_widget_content()
        
        # Key presses
        self.key_functions = {
            "colon": self.key_colon,
            "Return": self.key_return,
            "BackSpace": None,
            "Tab": None
        }
        
        # Syntax highlighting
        self.tags = TAGS
        self.define_text_tag()
        self.text_widget.bind("<KeyRelease>", self.key_pressed)
        self.highlight_whole_text()
        
        # Identation
        self.deepness_tree = deque()
        self.identation_level = 0
        # Should be incremented each time you add a semi colon.
        # Maybe I should keep a mapping of every line and its identation level so every time the user presses Return, we can just
        # I should make my editor smarter actually, to understand when I enter loops, condition, functions, class (everytime colon is pressed)
        
        self.display_widgets()
        
        
    # Direct GUI Handling :
    
    def quit(self, *args):
        """
        Overwriting the super().quit to close the file when exited
        """
        self.close_file()
        super().quit()
        
    def key_pressed(self, key_event):
        
        key_function = self.key_functions.get(key_event.keysym, None)
        if key_function:
            key_function()
        
        print(key_event.keysym)
        self.update_highlights()
        
    def key_colon(self):
        pass
    
    def key_return(self):
        
        # Find out inside of which we are
        last_line = self.text_widget.get(*self.get_previous_line()).strip()
        print(last_line)
        
        regex_to_check = [
            FUNCTION_DECLARATION_REGEX,
            ]
        
        if last_line:
            for regex in regex_to_check:
                m = regex.match(last_line)
            # Try to see if the lines matches with any of the regex
            last_char = last_line[-1]
            last_line = last_line[:-1]
            
            keyword = last_line.split()[0]
            if last_char == ":" and keyword in [
                "class",
                "def",
                "for", "while",
                "if", "elif", "else"
                ]:
                
                self.deepness_tree.append(keyword) # Should only happen if the user presses Return after that
                self.identation_level += 1
                print(self.identation_level, self.deepness_tree)
        self.text_widget.insert(tk.INSERT, "\t"*self.identation_level)
    
    def key_backspace(self):
        pass
    
    def key_tab(self):
        pass
        
    # -------------------------------------------------- #
        
    def read_file_content(self):
        with open(self.filename, 'r') as file:
            self.content = file.read()
            
    def set_text_widget_content(self):
        self.text_widget.insert(tk.END, self.content)
        
    def sync_content_to_input(self):
        self.content = self.text_widget.get("1.0", "end-1c")
        
    def save(self, *args):
        self.sync_content_to_input()
        with open(self.filename, "w") as file:
            file.write(self.content)
            
    # Syntax Highlighting
    
    def update_highlights(self, event=None):
        start, end = self.get_current_line()
        self.remove_all_tags(start, end)
        self.highlight_span(start, end)
        
    def get_current_line(self):
        cur_line = self.text_widget.index(tk.INSERT)
        start = self.text_widget.index(f"{cur_line} linestart")
        end = self.text_widget.index(f"{cur_line} lineend")
        return (start, end)
        
    def get_previous_line(self):
        cur_line = self.text_widget.index(tk.INSERT)
        start = self.text_widget.index(f"{cur_line} - 1l linestart")
        end = self.text_widget.index(f"{cur_line} - 1l lineend")
        return (start, end)
        
    def remove_all_tags(self, start, end):
        for tag in self.text_widget.tag_names():
            self.text_widget.tag_remove(tag, start, end)
            
    @staticmethod
    def find_matches(pattern, string):
        """
        Return a list of tuples (start, end) of occurences of the pattern
        """
        matches = list(map(re.Match.span, pattern.finditer(string)))
        return matches
        
    def highlight_span(self, start, end):
        # print(f"highlighting from {start} to {end}")
        content_to_highlight = self.text_widget.get(start, end)
        for tag in self.tags:
            for span_start, span_end in self.find_matches(tag.pattern, content_to_highlight):
                abs_start_str = f"{start}+{span_start}c"
                abs_end_str = f"{start}+{span_end}c"
                abs_start, abs_end = self.text_widget.index(abs_start_str), self.text_widget.index(abs_end_str)
                # print(abs_start_str, '->', abs_start, abs_end_str, '->', abs_end)
                self.text_widget.tag_add(tag.tagname, abs_start, abs_end)
            
    def highlight_whole_text(self):
        nb_lines = int(self.text_widget.index("end").split('.')[0])
        for line in range(nb_lines):
            start = f"{line}.0"
            end = start + 'lineend'
            true_start, true_end = self.text_widget.index(start), self.text_widget.index(end)
            self.highlight_span(true_start, true_end)
    
    # Widgets
    
    def define_text_tag(self):
        for tag in self.tags:
            tag.add_to_widget(self.text_widget)
        
    def setup_menu(self):
        """
        Create the menu
        """
        
        def donothing(*_):
            print("HELLO")
        
        self.menu = tk.Menu(self)
        
        # Just add the filename to the menu bar
        self.menu.add_cascade(label=self.filename)
        
        # File Menu
        self.file_menu = tk.Menu(self.menu, tearoff=0)
        self.file_menu.add_command(label="New", command=donothing)
        self.file_menu.add_command(label="Open", command=donothing)
        self.file_menu.add_command(label="Save", command=self.save, accelerator="Ctrl+S")
        self.bind_all("<Control-s>", self.save)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.quit)
        self.menu.add_cascade(label="File", menu=self.file_menu)
        
        # Help Menu
        self.help_menu = tk.Menu(self.menu, tearoff=0)
        self.help_menu.add_command(label="Compute keywords", command=self.test)
        self.help_menu.add_command(label="About...", command=donothing)
        self.menu.add_cascade(label="Help", menu=self.help_menu)
        
        self.config(menu=self.menu)
        
    def setup_widgets(self):
        """
        Create all the widgets
        """
        
        self.setup_menu()
        
        self.text_widget = tk.Text(self.mainframe)
        self.scrollbar = tk.Scrollbar(self.mainframe, command=self.text_widget.yview)
        self.text_widget["yscrollcommand"] = self.scrollbar.set
        
    def display_widgets(self):
        """
        Display alle the widgets
        """
        
        for widget in self.widgets_to_pack:
            widget.pack()
            
        self.text_widget.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        self.scrollbar.grid(row=0, column=1, sticky='nsew')
            
        self.mainframe.pack(fill="both", expand=True)
        
    def test(self):
        pass
    
def test():
    pass

if __name__ == "__main__":
    app = Application("draft.py")
    app.mainloop()
    
"""
TO-DO:
Pass the path to the file in script argument, so the user doesn't need to edit the file
Possibility to open another file, that would open maybe another window (Application) in another thread
Separate in multiple files (config, syntax-rules, Application class, main function with args parsing...)
"""
