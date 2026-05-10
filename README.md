# Rubus

A tree-walking interpreter for the Rubus programming language, bundled with **rubed** — a lightweight, terminal-based text editor built specifically for writing and running `.rub` files.

## Overview

The Rubus ecosystem consists of a Python-like, indentation-based programming language and a dedicated command-line environment. The interpreter processes raw source code through a lexer and parser to build an Abstract Syntax Tree (AST), which is then directly executed without an intermediate compilation step or bytecode generation.

## Installation

```bash
pip install rubus-b1
```

On Linux/macOS, no extra dependencies are needed. On Windows, `windows-curses` is installed automatically.

After installing, the `rubed` command is available globally:

```bash
rubed                          # open the editor with an empty buffer
rubed path/to/script.rub       # open a file in the editor
rubed path/to/script.rub --run # run a script headlessly
```

## Features

### The Rubus Language

- Control flow: `if` / `elif` / `else`, `for`, `while`
- Types: integers, floats, booleans, strings, and f-strings
- Built-in collections: lists, dictionaries, sets, and tuples
- List and dictionary comprehensions
- Custom struct definitions
- Function definitions (`def`) and variable declarations (`let`)
- Lexical scoping and environment management
- Try / except / finally error handling
- Tuple unpacking: `a, b = 1, 2`
- Default parameters and keyword arguments

### The Rubus Editor (rubed)

- **Terminal-native**: built with curses for a seamless command-line workflow
- **Syntax highlighting**: real-time colorization for keywords, types, strings, numbers, comments, and operators
- **Integrated execution**: run `.rub` scripts directly from within the editor

#### Keybindings

| Key | Action |
|-----|--------|
| `Ctrl+S` | Save file |
| `Ctrl+R` | Run the current file |
| `Ctrl+N` | New buffer |
| `Ctrl+O` | Open an existing file |
| `Ctrl+Q` | Quit (prompts if unsaved) |

## Usage

```bash
# Open editor with empty buffer
rubed

# Open a specific file
rubed path/to/script.rub

# Run a script without opening the editor
rubed path/to/script.rub --run
```

## Example

```
def greet(name: str) -> str:
    return f"Hello, {name}!"

let names: list = ["Alice", "Bob", "Carol"]
for n in names:
    print(greet(n))
```

## Requirements

- Python 3.10+
- `windows-curses` (Windows only, installed automatically)