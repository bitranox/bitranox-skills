# DataTable

A widget to display text in a table.  This includes the ability to update data, use a cursor to navigate data, respond to mouse clicks, delete rows or columns, and individually render each cell as a Rich Text renderable.  DataTable provides an efficiently displayed and updated table capable for most applications.

Applications may have custom rules for formatting, numbers, repopulating tables after searching or filtering, and responding to selections.  The widget emits events to interface with custom logic.

- [x] Focusable
- [ ] Container

## Guide

### Adding data

The following example shows how to fill a table with data.
First, we use `add_columns` to include the `lane`, `swimmer`, `country`, and `time` columns in the table.
After that, we use the `add_rows` method to insert the rows into the table.

**data_table.py**


```python
from textual.app import App, ComposeResult
from textual.widgets import DataTable

ROWS = [
    ("lane", "swimmer", "country", "time"),
    (4, "Joseph Schooling", "Singapore", 50.39),
    (2, "Michael Phelps", "United States", 51.14),
    (5, "Chad le Clos", "South Africa", 51.14),
    (6, "László Cseh", "Hungary", 51.14),
    (3, "Li Zhuhao", "China", 51.26),
    (8, "Mehdy Metella", "France", 51.58),
    (7, "Tom Shields", "United States", 51.73),
    (1, "Aleksandr Sadovnikov", "Russia", 51.84),
    (10, "Darren Burns", "Scotland", 51.84),
]


class TableApp(App):
    def compose(self) -> ComposeResult:
        yield DataTable()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns(*ROWS[0])
        table.add_rows(ROWS[1:])


app = TableApp()
if __name__ == "__main__":
    app.run()
```
To add a single row or column use `add_row` and `add_column`, respectively.

#### Styling and justifying cells

Cells can contain more than just plain strings - [Rich](https://rich.readthedocs.io/en/stable/introduction.html) renderables such as [`Text`](https://rich.readthedocs.io/en/stable/text.html?highlight=Text#rich-text) are also supported.
`Text` objects provide an easy way to style and justify cell content:

**data_table_renderables.py**


```python
from rich.text import Text

from textual.app import App, ComposeResult
from textual.widgets import DataTable

ROWS = [
    ("lane", "swimmer", "country", "time"),
    (4, "Joseph Schooling", "Singapore", 50.39),
    (2, "Michael Phelps", "United States", 51.14),
    (5, "Chad le Clos", "South Africa", 51.14),
    (6, "László Cseh", "Hungary", 51.14),
    (3, "Li Zhuhao", "China", 51.26),
    (8, "Mehdy Metella", "France", 51.58),
    (7, "Tom Shields", "United States", 51.73),
    (1, "Aleksandr Sadovnikov", "Russia", 51.84),
    (10, "Darren Burns", "Scotland", 51.84),
]


class TableApp(App):
    def compose(self) -> ComposeResult:
        yield DataTable()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns(*ROWS[0])
        for row in ROWS[1:]:
            # Adding styled and justified `Text` objects instead of plain strings.
            styled_row = [
                Text(str(cell), style="italic #03AC13", justify="right") for cell in row
            ]
            table.add_row(*styled_row)


app = TableApp()
if __name__ == "__main__":
    app.run()
```
### Keys

When adding a row to the table, you can supply a _key_ to `add_row`.
A key is a unique identifier for that row.
If you don't supply a key, Textual will generate one for you and return it from `add_row`.
This key can later be used to reference the row, regardless of its current position in the table.

When working with data from a database, for example, you may wish to set the row `key` to the primary key of the data to ensure uniqueness.
The method `add_column` also accepts a `key` argument and works similarly.

Keys are important because cells in a data table can change location due to factors like row deletion and sorting.
Thus, using keys instead of coordinates allows us to refer to data without worrying about its current location in the table.

If you want to change the table based solely on coordinates, you may need to convert that coordinate to a cell key first using the `coordinate_to_cell_key` method.

### Cursors

A cursor allows navigating within a table with the keyboard or mouse. There are four cursor types: `"cell"` (the default), `"row"`, `"column"`, and `"none"`.

 Change the cursor type by assigning to
the ``cursor_type`` reactive attribute.
The coordinate of the cursor is exposed via the ``cursor_coordinate`` reactive attribute.

Using the keyboard, arrow keys, `Page Up`, `Page Down`, `Home` and `End` move the cursor highlight, emitting a ``CellHighlighted``
message, then enter selects the cell, emitting a ``CellSelected`` message.  If the
`cursor_type` is row, then ``RowHighlighted`` and ``RowSelected``
are emitted, similarly for  ``ColumnHighlighted`` and ``ColumnSelected``.

When moving the mouse over the table, a ``MouseMove`` event is emitted, the cell hovered over is styled,
and the ``hover_coordinate`` reactive attribute is updated.  Clicking the mouse
then emits the ``CellHighlighted`` and  ``CellSelected``
events.

**data_table_cursors.py**


```python
from itertools import cycle

from textual.app import App, ComposeResult
from textual.widgets import DataTable

ROWS = [
    ("lane", "swimmer", "country", "time"),
    (4, "Joseph Schooling", "Singapore", 50.39),
    (2, "Michael Phelps", "United States", 51.14),
    (5, "Chad le Clos", "South Africa", 51.14),
    (6, "László Cseh", "Hungary", 51.14),
    (3, "Li Zhuhao", "China", 51.26),
    (8, "Mehdy Metella", "France", 51.58),
    (7, "Tom Shields", "United States", 51.73),
    (1, "Aleksandr Sadovnikov", "Russia", 51.84),
    (10, "Darren Burns", "Scotland", 51.84),
]

cursors = cycle(["column", "row", "cell", "none"])


class TableApp(App):
    def compose(self) -> ComposeResult:
        yield DataTable()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.cursor_type = next(cursors)
        table.zebra_stripes = True
        table.add_columns(*ROWS[0])
        table.add_rows(ROWS[1:])

    def key_c(self):
        table = self.query_one(DataTable)
        table.cursor_type = next(cursors)


app = TableApp()
if __name__ == "__main__":
    app.run()
```
### Updating data

Cells can be updated using the `update_cell` and `update_cell_at` methods.

### Removing data

To remove all data in the table, use the `clear` method.
To remove individual rows, use `remove_row`.
The `remove_row` method accepts a `key` argument, which identifies the row to be removed.

If you wish to remove the row below the cursor in the `DataTable`, use `coordinate_to_cell_key` to get the row key of
the row under the current `cursor_coordinate`, then supply this key to `remove_row`:

```python
# Get the keys for the row and column under the cursor.
row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
# Supply the row key to `remove_row` to delete the row.
table.remove_row(row_key)
```

### Removing columns

To remove individual columns, use `remove_column`.
The `remove_column` method accepts a `key` argument, which identifies the column to be removed.

You can remove the column below the cursor using the same `coordinate_to_cell_key` method described above:

```python
# Get the keys for the row and column under the cursor.
_, column_key = table.coordinate_to_cell_key(table.cursor_coordinate)
# Supply the column key to `column_row` to delete the column.
table.remove_column(column_key)
```

### Fixed data

You can fix a number of rows and columns in place, keeping them pinned to the top and left of the table respectively.
To do this, assign an integer to the `fixed_rows` or `fixed_columns` reactive attributes of the `DataTable`.

**data_table_fixed.py**


```python
from textual.app import App, ComposeResult
from textual.widgets import DataTable


class TableApp(App):
    CSS = "DataTable {height: 1fr}"

    def compose(self) -> ComposeResult:
        yield DataTable()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.focus()
        table.add_columns("A", "B", "C")
        for number in range(1, 100):
            table.add_row(str(number), str(number * 2), str(number * 3))
        table.fixed_rows = 2
        table.fixed_columns = 1
        table.cursor_type = "row"
        table.zebra_stripes = True


app = TableApp()
if __name__ == "__main__":
    app.run()
```
In the example above, we set `fixed_rows` to `2`, and `fixed_columns` to `1`,
meaning the first two rows and the leftmost column do not scroll - they always remain
visible as you scroll through the data table.

### Sorting

The DataTable rows can be sorted using the  ``sort``  method.

There are three methods of using ``sort``:

* By Column.  Pass columns in as parameters to sort by the natural order of one or more columns.  Specify a column using either a ``ColumnKey`` instance or the `key` you supplied to ``add_column``.  For example, `sort("country", "region")` would sort by country, and, when the country values are equal, by region.
* By Key function.  Pass a function as the `key` parameter to sort, similar to the [key function parameter](https://docs.python.org/3/howto/sorting.html#key-functions)  of Python's [`sorted`](https://docs.python.org/3/library/functions.html#sorted) built-in.   The function will be called once per row with a tuple of all row values.
* By both Column and Key function.   You can specify which columns to include as parameters to your key function.  For example, `sort("hours", "rate", key=lambda h, r: h*r)` passes two values to the key function for each row.

The `reverse` argument reverses the order of your sort.  Note that correct sorting may require your key function to undo your formatting.

**data_table_sort.py**


```python
from rich.text import Text

from textual.app import App, ComposeResult
from textual.widgets import DataTable, Footer

ROWS = [
    ("lane", "swimmer", "country", "time 1", "time 2"),
    (4, "Joseph Schooling", Text("Singapore", style="italic"), 50.39, 51.84),
    (2, "Michael Phelps", Text("United States", style="italic"), 50.39, 51.84),
    (5, "Chad le Clos", Text("South Africa", style="italic"), 51.14, 51.73),
    (6, "László Cseh", Text("Hungary", style="italic"), 51.14, 51.58),
    (3, "Li Zhuhao", Text("China", style="italic"), 51.26, 51.26),
    (8, "Mehdy Metella", Text("France", style="italic"), 51.58, 52.15),
    (7, "Tom Shields", Text("United States", style="italic"), 51.73, 51.12),
    (1, "Aleksandr Sadovnikov", Text("Russia", style="italic"), 51.84, 50.85),
    (10, "Darren Burns", Text("Scotland", style="italic"), 51.84, 51.55),
]


class TableApp(App):
    BINDINGS = [
        ("a", "sort_by_average_time", "Sort By Average Time"),
        ("n", "sort_by_last_name", "Sort By Last Name"),
        ("c", "sort_by_country", "Sort By Country"),
        ("d", "sort_by_columns", "Sort By Columns (Only)"),
    ]

    current_sorts: set = set()

    def compose(self) -> ComposeResult:
        yield DataTable()
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        for col in ROWS[0]:
            table.add_column(col, key=col)
        table.add_rows(ROWS[1:])

    def sort_reverse(self, sort_type: str):
        """Determine if `sort_type` is ascending or descending."""
        reverse = sort_type in self.current_sorts
        if reverse:
            self.current_sorts.remove(sort_type)
        else:
            self.current_sorts.add(sort_type)
        return reverse

    def action_sort_by_average_time(self) -> None:
        """Sort DataTable by average of times (via a function) and
        passing of column data through positional arguments."""

        def sort_by_average_time_then_last_name(row_data):
            name, *scores = row_data
            return (sum(scores) / len(scores), name.split()[-1])

        table = self.query_one(DataTable)
        table.sort(
            "swimmer",
            "time 1",
            "time 2",
            key=sort_by_average_time_then_last_name,
            reverse=self.sort_reverse("time"),
        )

    def action_sort_by_last_name(self) -> None:
        """Sort DataTable by last name of swimmer (via a lambda)."""
        table = self.query_one(DataTable)
        table.sort(
            "swimmer",
            key=lambda swimmer: swimmer.split()[-1],
            reverse=self.sort_reverse("swimmer"),
        )

    def action_sort_by_country(self) -> None:
        """Sort DataTable by country which is a `Rich.Text` object."""
        table = self.query_one(DataTable)
        table.sort(
            "country",
            key=lambda country: country.plain,
            reverse=self.sort_reverse("country"),
        )

    def action_sort_by_columns(self) -> None:
        """Sort DataTable without a key."""
        table = self.query_one(DataTable)
        table.sort("swimmer", "lane", reverse=self.sort_reverse("columns"))


app = TableApp()
if __name__ == "__main__":
    app.run()
```
### Labeled rows

A "label" can be attached to a row using the `add_row` method.
This will add an extra column to the left of the table which the cursor cannot interact with.
This column is similar to the leftmost column in a spreadsheet containing the row numbers.
The example below shows how to attach simple numbered labels to rows.

**data_table_labels.py**


```python
from rich.text import Text

from textual.app import App, ComposeResult
from textual.widgets import DataTable

ROWS = [
    ("lane", "swimmer", "country", "time"),
    (4, "Joseph Schooling", "Singapore", 50.39),
    (2, "Michael Phelps", "United States", 51.14),
    (5, "Chad le Clos", "South Africa", 51.14),
    (6, "László Cseh", "Hungary", 51.14),
    (3, "Li Zhuhao", "China", 51.26),
    (8, "Mehdy Metella", "France", 51.58),
    (7, "Tom Shields", "United States", 51.73),
    (1, "Aleksandr Sadovnikov", "Russia", 51.84),
    (10, "Darren Burns", "Scotland", 51.84),
]


class TableApp(App):
    def compose(self) -> ComposeResult:
        yield DataTable()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns(*ROWS[0])
        for number, row in enumerate(ROWS[1:], start=1):
            label = Text(str(number), style="#B0FC38 italic")
            table.add_row(*row, label=label)


app = TableApp()
if __name__ == "__main__":
    app.run()
```
## Reactive Attributes

| Name                | Type         | Default            | Description                                           |
|---------------------|--------------|--------------------|-------------------------------------------------------|
| `show_header`       | `bool`       | `True`             | Show the table header                                 |
| `show_row_labels`   | `bool`       | `True`             | Show the row labels (if applicable)                   |
| `fixed_rows`        | `int`        | `0`                | Number of fixed rows (rows which do not scroll)       |
| `fixed_columns`     | `int`        | `0`                | Number of fixed columns (columns which do not scroll) |
| `zebra_stripes`     | `bool`       | `False`            | Style with alternating colors on rows                 |
| `header_height`     | `int`        | `1`                | Height of header row                                  |
| `show_cursor`       | `bool`       | `True`             | Show the cursor                                       |
| `cursor_type`       | `str`        | `"cell"`           | One of `"cell"`, `"row"`, `"column"`, or `"none"`     |
| `cursor_coordinate` | `Coordinate` | `Coordinate(0, 0)` | The current coordinate of the cursor                  |
| `hover_coordinate`  | `Coordinate` | `Coordinate(0, 0)` | The coordinate the _mouse_ cursor is above            |

## Messages

- `DataTable.CellHighlighted`
- `DataTable.CellSelected`
- `DataTable.RowHighlighted`
- `DataTable.RowSelected`
- `DataTable.ColumnHighlighted`
- `DataTable.ColumnSelected`
- `DataTable.HeaderSelected`
- `DataTable.RowLabelSelected`

## Bindings

The data table widget defines the following bindings:

*API reference: `textual.widgets.DataTable.BINDINGS`*


## Component Classes

The data table widget provides the following component classes:

*API reference: `textual.widgets.DataTable.COMPONENT_CLASSES`*


## See also

- [ListView](./list_view.md) - A simpler vertical list widget
- [OptionList](./option_list.md) - A vertical list of selectable options
- [Widgets guide](../guide/widgets.md) - How to build and use widgets

---


*API reference: `textual.widgets.DataTable`*


*API reference: `textual.widgets.data_table`*
