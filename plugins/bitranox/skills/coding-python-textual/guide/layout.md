# Layout

In Textual, the *layout* defines how widgets will be arranged (or *laid out*) inside a container.
Textual supports a number of layouts which can be set either via a widget's `styles` object or via CSS.
Layouts can be used for both high-level positioning of widgets on screen, and for positioning of nested widgets.

## Vertical

The `vertical` layout arranges child widgets vertically, from top to bottom.

![Vertical layout](../images/layout/vertical.excalidraw.svg)

The example below demonstrates how children are arranged inside a container with the `vertical` layout.

**vertical_layout.py**


```python
from textual.app import App, ComposeResult
from textual.widgets import Static


class VerticalLayoutExample(App):
    CSS_PATH = "vertical_layout.tcss"

    def compose(self) -> ComposeResult:
        yield Static("One", classes="box")
        yield Static("Two", classes="box")
        yield Static("Three", classes="box")


if __name__ == "__main__":
    app = VerticalLayoutExample()
    app.run()
```

**vertical_layout.tcss**


```css
Screen {
    layout: vertical;
}

.box {
    height: 1fr;
    border: solid green;
}
```
Notice that the first widget yielded from the `compose` method appears at the top of the display,
the second widget appears below it, and so on.
Inside `vertical_layout.tcss`, we've assigned `layout: vertical` to `Screen`.
`Screen` is the parent container of the widgets yielded from the `App.compose` method, and can be thought of as the terminal window itself.

> **Note**
>
>
> The `layout: vertical` CSS isn't *strictly* necessary in this case, since Screens use a `vertical` layout by default.


We've assigned each child `.box` a height of `1fr`, which ensures they're each allocated an equal portion of the available height.

You might also have noticed that the child widgets are the same width as the screen, despite nothing in our CSS file suggesting this.
This is because widgets expand to the width of their parent container (in this case, the `Screen`).

Just like other styles, `layout` can be adjusted at runtime by modifying the `styles` of a `Widget` instance:

```python
widget.styles.layout = "vertical"
```

Using `fr` units guarantees that the children fill the available height of the parent.
However, if the total height of the children exceeds the available space, then Textual will automatically add
a scrollbar to the parent `Screen`.

> **Note**
>
>
> A scrollbar is added automatically because `Screen` contains the declaration `overflow-y: auto;`.


For example, if we swap out `height: 1fr;` for `height: 10;` in the example above, the child widgets become a fixed height of 10, and a scrollbar appears (assuming our terminal window is sufficiently small):



With the parent container in focus, we can use our mouse wheel, trackpad, or keyboard to scroll it.

## Horizontal

The `horizontal` layout arranges child widgets horizontally, from left to right.

![Horizontal layout](../images/layout/horizontal.excalidraw.svg)

The example below shows how we can arrange widgets horizontally, with minimal changes to the vertical layout example above.


**horizontal_layout.py**


```python
from textual.app import App, ComposeResult
from textual.widgets import Static


class HorizontalLayoutExample(App):
    CSS_PATH = "horizontal_layout.tcss"

    def compose(self) -> ComposeResult:
        yield Static("One", classes="box")
        yield Static("Two", classes="box")
        yield Static("Three", classes="box")


if __name__ == "__main__":
    app = HorizontalLayoutExample()
    app.run()
```

**horizontal_layout.tcss**


```css
Screen {
    layout: horizontal;
}

.box {
    height: 100%;
    width: 1fr;
    border: solid green;
}
```
We've changed the `layout` to `horizontal` inside our CSS file.
As a result, the widgets are now arranged from left to right instead of top to bottom.

We also adjusted the height of the child `.box` widgets to `100%`.
As mentioned earlier, widgets expand to fill the _width_ of their parent container.
They do not, however, expand to fill the container's height.
Thus, we need explicitly assign `height: 100%` to achieve this.

A consequence of this "horizontal growth" behavior is that if we remove the width restriction from the above example (by deleting `width: 1fr;`), each child widget will grow to fit the width of the screen,
and only the first widget will be visible.
The other two widgets in our layout are offscreen, to the right-hand side of the screen.
In the case of `horizontal` layout, Textual will _not_ automatically add a scrollbar.

To enable horizontal scrolling, we can use the `overflow-x: auto;` declaration:

**horizontal_layout_overflow.py**


```python
from textual.app import App, ComposeResult
from textual.widgets import Static


class HorizontalLayoutExample(App):
    CSS_PATH = "horizontal_layout_overflow.tcss"

    def compose(self) -> ComposeResult:
        yield Static("One", classes="box")
        yield Static("Two", classes="box")
        yield Static("Three", classes="box")


if __name__ == "__main__":
    app = HorizontalLayoutExample()
    app.run()
```

**horizontal_layout_overflow.tcss**


```css
Screen {
    layout: horizontal;
    overflow-x: auto;
}

.box {
    height: 100%;
    border: solid green;
}
```
With `overflow-x: auto;`, Textual automatically adds a horizontal scrollbar since the width of the children
exceeds the available horizontal space in the parent container.

## Utility containers

Textual comes with `several "container" widgets`.
Among them, we have `Vertical`, `Horizontal`, and `Grid` which have the corresponding layout.

The example below shows how we can combine these containers to create a simple 2x2 grid.
Inside a single `Horizontal` container, we place two `Vertical` containers.
In other words, we have a single row containing two columns.

**utility_containers.py**


```python
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Static


class UtilityContainersExample(App):
    CSS_PATH = "utility_containers.tcss"

    def compose(self) -> ComposeResult:
        yield Horizontal(
            Vertical(
                Static("One"),
                Static("Two"),
                classes="column",
            ),
            Vertical(
                Static("Three"),
                Static("Four"),
                classes="column",
            ),
        )


if __name__ == "__main__":
    app = UtilityContainersExample()
    app.run()
```

**utility_containers.tcss**


```css
Static {
    content-align: center middle;
    background: crimson;
    border: solid darkred;
    height: 1fr;
}

.column {
    width: 1fr;
}
```
You may be tempted to use many levels of nested utility containers in order to build advanced, grid-like layouts.
However, Textual comes with a more powerful mechanism for achieving this known as _grid layout_, which we'll discuss below.

## Composing with context managers

In the previous section, we've shown how you add children to a container (such as `Horizontal` and `Vertical`) using positional arguments.
It's fine to do it this way, but Textual offers a simplified syntax using [context managers](https://docs.python.org/3/reference/datamodel.html#context-managers), which is generally easier to write and edit.

When composing a widget, you can introduce a container using Python's `with` statement.
Any widgets yielded within that block are added as a child of the container.

Let's update the [utility containers](#utility-containers) example to use the context manager approach.

**utility_containers_using_with.py**


> **Note**
>
>
> This code uses context managers to compose widgets.


```python
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Static


class UtilityContainersExample(App):
    CSS_PATH = "utility_containers.tcss"

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical(classes="column"):
                yield Static("One")
                yield Static("Two")
            with Vertical(classes="column"):
                yield Static("Three")
                yield Static("Four")


if __name__ == "__main__":
    app = UtilityContainersExample()
    app.run()
```

**utility_containers.py**


> **Note**
>
>
> This is the original code using positional arguments.


```python
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Static


class UtilityContainersExample(App):
    CSS_PATH = "utility_containers.tcss"

    def compose(self) -> ComposeResult:
        yield Horizontal(
            Vertical(
                Static("One"),
                Static("Two"),
                classes="column",
            ),
            Vertical(
                Static("Three"),
                Static("Four"),
                classes="column",
            ),
        )


if __name__ == "__main__":
    app = UtilityContainersExample()
    app.run()
```

**utility_containers.tcss**


```css
Static {
    content-align: center middle;
    background: crimson;
    border: solid darkred;
    height: 1fr;
}

.column {
    width: 1fr;
}
```
Note how the end result is the same, but the code with context managers is a little easier to read. It is up to you which method you want to use, and you can mix context managers with positional arguments if you like!

## Grid

The `grid` layout arranges widgets within a grid.
Widgets can span multiple rows and columns to create complex layouts.
The diagram below hints at what can be achieved using `layout: grid`.

![Grid layout](../images/layout/grid.excalidraw.svg)

> **Note**
>
>
> Grid layouts in Textual have little in common with browser-based CSS Grid.


To get started with grid layout, define the number of columns and rows in your grid with the `grid-size` CSS property and set `layout: grid`. Widgets are inserted into the "cells" of the grid from left-to-right and top-to-bottom order.

The following example creates a 3 x 2 grid and adds six widgets to it

**grid_layout1.py**


```python
from textual.app import App, ComposeResult
from textual.widgets import Static


class GridLayoutExample(App):
    CSS_PATH = "grid_layout1.tcss"

    def compose(self) -> ComposeResult:
        yield Static("One", classes="box")
        yield Static("Two", classes="box")
        yield Static("Three", classes="box")
        yield Static("Four", classes="box")
        yield Static("Five", classes="box")
        yield Static("Six", classes="box")


if __name__ == "__main__":
    app = GridLayoutExample()
    app.run()
```

**grid_layout1.tcss**


```css
Screen {
    layout: grid;
    grid-size: 3 2;
}

.box {
    height: 100%;
    border: solid green;
}
```
If we were to yield a seventh widget from our `compose` method, it would not be visible as the grid does not contain enough cells to accommodate it. We can tell Textual to add new rows on demand to fit the number of widgets, by omitting the number of rows from `grid-size`. The following example creates a grid with three columns, with rows created on demand:


**grid_layout2.py**


```python
from textual.app import App, ComposeResult
from textual.widgets import Static


class GridLayoutExample(App):
    CSS_PATH = "grid_layout2.tcss"

    def compose(self) -> ComposeResult:
        yield Static("One", classes="box")
        yield Static("Two", classes="box")
        yield Static("Three", classes="box")
        yield Static("Four", classes="box")
        yield Static("Five", classes="box")
        yield Static("Six", classes="box")
        yield Static("Seven", classes="box")


if __name__ == "__main__":
    app = GridLayoutExample()
    app.run()
```

**grid_layout2.tcss**


```css
Screen {
    layout: grid;
    grid-size: 3;
}

.box {
    height: 100%;
    border: solid green;
}
```
Since we specified that our grid has three columns (`grid-size: 3`), and we've yielded seven widgets in total,
a third row has been created to accommodate the seventh widget.

Now that we know how to define a simple uniform grid, let's look at how we can
customize it to create more complex layouts.

### Row and column sizes

You can adjust the width of columns and the height of rows in your grid using the `grid-columns` and `grid-rows` properties.
These properties can take multiple values, letting you specify dimensions on a column-by-column or row-by-row basis.

Continuing on from our earlier 3x2 example grid, let's adjust the width of the columns using `grid-columns`.
We'll make the first column take up half of the screen width, with the other two columns sharing the remaining space equally.


**grid_layout3_row_col_adjust.py**


```python
from textual.app import App, ComposeResult
from textual.widgets import Static


class GridLayoutExample(App):
    CSS_PATH = "grid_layout3_row_col_adjust.tcss"

    def compose(self) -> ComposeResult:
        yield Static("One", classes="box")
        yield Static("Two", classes="box")
        yield Static("Three", classes="box")
        yield Static("Four", classes="box")
        yield Static("Five", classes="box")
        yield Static("Six", classes="box")


if __name__ == "__main__":
    app = GridLayoutExample()
    app.run()
```

**grid_layout3_row_col_adjust.tcss**


```css
Screen {
    layout: grid;
    grid-size: 3;
    grid-columns: 2fr 1fr 1fr;
}

.box {
    height: 100%;
    border: solid green;
}
```
Since our `grid-size` is 3 (meaning it has three columns), our `grid-columns` declaration has three space-separated values.
Each of these values sets the width of a column.
The first value refers to the left-most column, the second value refers to the next column, and so on.
In the example above, we've given the left-most column a width of `2fr` and the other columns widths of `1fr`.
As a result, the first column is allocated twice the width of the other columns.

Similarly, we can adjust the height of a row using `grid-rows`.
In the following example, we use `%` units to adjust the first row of our grid to `25%` height,
and the second row to `75%` height (while retaining the `grid-columns` change from above).


**grid_layout4_row_col_adjust.py**


```python
from textual.app import App, ComposeResult
from textual.widgets import Static


class GridLayoutExample(App):
    CSS_PATH = "grid_layout4_row_col_adjust.tcss"

    def compose(self) -> ComposeResult:
        yield Static("One", classes="box")
        yield Static("Two", classes="box")
        yield Static("Three", classes="box")
        yield Static("Four", classes="box")
        yield Static("Five", classes="box")
        yield Static("Six", classes="box")


if __name__ == "__main__":
    app = GridLayoutExample()
    app.run()
```

**grid_layout4_row_col_adjust.tcss**


```css
Screen {
    layout: grid;
    grid-size: 3;
    grid-columns: 2fr 1fr 1fr;
    grid-rows: 25% 75%;
}

.box {
    height: 100%;
    border: solid green;
}
```
If you don't specify enough values in a `grid-columns` or `grid-rows` declaration, the values you _have_ provided will be "repeated".
For example, if your grid has four columns (i.e. `grid-size: 4;`), then `grid-columns: 2 4;` is equivalent to `grid-columns: 2 4 2 4;`.
If it instead had three columns, then `grid-columns: 2 4;` would be equivalent to `grid-columns: 2 4 2;`.

#### Auto rows / columns

The `grid-columns` and `grid-rows` rules can both accept a value of "auto" in place of any of the dimensions, which tells Textual to calculate an optimal size based on the content.

Let's modify the previous example to make the first column an `auto` column.

**grid_layout_auto.py**


```python
from textual.app import App, ComposeResult
from textual.widgets import Static


class GridLayoutExample(App):
    CSS_PATH = "grid_layout_auto.tcss"

    def compose(self) -> ComposeResult:
        yield Static("First column", classes="box")
        yield Static("Two", classes="box")
        yield Static("Three", classes="box")
        yield Static("Four", classes="box")
        yield Static("Five", classes="box")
        yield Static("Six", classes="box")


if __name__ == "__main__":
    app = GridLayoutExample()
    app.run()
```

**grid_layout_auto.tcss**


```css
Screen {
    layout: grid;
    grid-size: 3;
    grid-columns: auto 1fr 1fr;
    grid-rows: 25% 75%;
}

.box {
    height: 100%;
    border: solid green;
}
```
Notice how the first column is just wide enough to fit the content of each cell.
The layout will adjust accordingly if you update the content for any widget in that column.


### Cell spans

Cells may _span_ multiple rows or columns, to create more interesting grid arrangements.

To make a single cell span multiple rows or columns in the grid, we need to be able to select it using CSS.
To do this, we'll add an ID to the widget inside our `compose` method so we can set the `row-span` and `column-span` properties using CSS.

Let's add an ID of `#two` to the second widget yielded from `compose`, and give it a `column-span` of 2 to make that widget span two columns.
We'll also add a slight tint using `tint: magenta 40%;` to draw attention to it.


**grid_layout5_col_span.py**


```python
from textual.app import App, ComposeResult
from textual.widgets import Static


class GridLayoutExample(App):
    CSS_PATH = "grid_layout5_col_span.tcss"

    def compose(self) -> ComposeResult:
        yield Static("One", classes="box")
        yield Static("Two [b](column-span: 2)", classes="box", id="two")
        yield Static("Three", classes="box")
        yield Static("Four", classes="box")
        yield Static("Five", classes="box")
        yield Static("Six", classes="box")


if __name__ == "__main__":
    app = GridLayoutExample()
    app.run()
```

**grid_layout5_col_span.tcss**


```css
Screen {
    layout: grid;
    grid-size: 3;
}

#two {
    column-span: 2;
    tint: magenta 40%;
}

.box {
    height: 100%;
    border: solid green;
}
```
Notice that the widget expands to fill columns to the _right_ of its original position.
Since `#two` now spans two cells instead of one, all widgets that follow it are shifted along one cell in the grid to accommodate.
As a result, the final widget wraps on to a new row at the bottom of the grid.

> **Note**
>
>
> In the example above, setting the `column-span` of `#two` to be 3 (instead of 2) would have the same effect, since there are only 2 columns available (including `#two`'s original column).


We can similarly adjust the `row-span` of a cell to have it span multiple rows.
This can be used in conjunction with `column-span`, meaning one cell may span multiple rows and columns.
The example below shows `row-span` in action.
We again target widget `#two` in our CSS, and add a `row-span: 2;` declaration to it.


**grid_layout6_row_span.py**


```python
from textual.app import App, ComposeResult
from textual.widgets import Static


class GridLayoutExample(App):
    CSS_PATH = "grid_layout6_row_span.tcss"

    def compose(self) -> ComposeResult:
        yield Static("One", classes="box")
        yield Static("Two [b](column-span: 2 and row-span: 2)", classes="box", id="two")
        yield Static("Three", classes="box")
        yield Static("Four", classes="box")
        yield Static("Five", classes="box")
        yield Static("Six", classes="box")


app = GridLayoutExample()
if __name__ == "__main__":
    app.run()
```

**grid_layout6_row_span.tcss**


```css
Screen {
    layout: grid;
    grid-size: 3;
}

#two {
    column-span: 2;
    row-span: 2;
    tint: magenta 40%;
}

.box {
    height: 100%;
    border: solid green;
}
```
Widget `#two` now spans two columns and two rows, covering a total of four cells.
Notice how the other cells are moved to accommodate this change.
The widget that previously occupied a single cell now occupies four cells, thus displacing three cells to a new row.

### Gutter

The spacing between cells in the grid can be adjusted using the `grid-gutter` CSS property.
By default, cells have no gutter, meaning their edges touch each other.
Gutter is applied across every cell in the grid, so `grid-gutter` must be used on a widget with `layout: grid` (_not_ on a child/cell widget).

To illustrate gutter let's set our `Screen` background color to `lightgreen`, and the background color of the widgets we yield to `darkmagenta`.
Now if we add `grid-gutter: 1;` to our grid, one cell of spacing appears between the cells and reveals the light green background of the `Screen`.

**grid_layout7_gutter.py**


```python
from textual.app import App, ComposeResult
from textual.widgets import Static


class GridLayoutExample(App):
    CSS_PATH = "grid_layout7_gutter.tcss"

    def compose(self) -> ComposeResult:
        yield Static("One", classes="box")
        yield Static("Two", classes="box")
        yield Static("Three", classes="box")
        yield Static("Four", classes="box")
        yield Static("Five", classes="box")
        yield Static("Six", classes="box")


if __name__ == "__main__":
    app = GridLayoutExample()
    app.run()
```

**grid_layout7_gutter.tcss**


```css
Screen {
    layout: grid;
    grid-size: 3;
    grid-gutter: 1;
    background: lightgreen;
}

.box {
    background: darkmagenta;
    height: 100%;
}
```
Notice that gutter only applies _between_ the cells in a grid, pushing them away from each other.
It doesn't add any spacing between cells and the edges of the parent container.

> **Tip**
>
>
> You can also supply two values to the `grid-gutter` property to set vertical and horizontal gutters respectively.
> Since terminal cells are typically two times taller than they are wide,
> it's common to set the horizontal gutter equal to double the vertical gutter (e.g. `grid-gutter: 1 2;`) in order to achieve visually consistent spacing around grid cells.


## Docking

Widgets may be *docked*.
Docking a widget removes it from the layout and fixes its position, aligned to either the top, right, bottom, or left edges of a container.
Docked widgets will not scroll out of view, making them ideal for sticky headers, footers, and sidebars.

![Dock layout](../images/layout/dock.excalidraw.svg)

To dock a widget to an edge, add a `dock: <EDGE>;` declaration to it, where `<EDGE>` is one of `top`, `right`, `bottom`, or `left`.
For example, a sidebar similar to that shown in the diagram above can be achieved using `dock: left;`.
The code below shows a simple sidebar implementation.

**dock_layout1_sidebar.py**


```python
from textual.app import App, ComposeResult
from textual.widgets import Static

TEXT = """\
Docking a widget removes it from the layout and fixes its position, aligned to either the top, right, bottom, or left edges of a container.

Docked widgets will not scroll out of view, making them ideal for sticky headers, footers, and sidebars.

"""


class DockLayoutExample(App):
    CSS_PATH = "dock_layout1_sidebar.tcss"

    def compose(self) -> ComposeResult:
        yield Static("Sidebar", id="sidebar")
        yield Static(TEXT * 10, id="body")


if __name__ == "__main__":
    app = DockLayoutExample()
    app.run()
```

**dock_layout1_sidebar.tcss**


```css
#sidebar {
    dock: left;
    width: 15;
    height: 100%;
    color: #0f2b41;
    background: dodgerblue;
}
```
If we run the app above and scroll down, the body text will scroll but the sidebar does not (note the position of the scrollbar in the output shown above).

Docking multiple widgets to the same edge will result in overlap.
The first widget yielded from `compose` will appear below widgets yielded after it.
Let's dock a second sidebar, `#another-sidebar`, to the left of the screen.
This new sidebar is double the width of the one previous one, and has a `deeppink` background.

**dock_layout2_sidebar.py**


```python
from textual.app import App, ComposeResult
from textual.widgets import Static

TEXT = """\
Docking a widget removes it from the layout and fixes its position, aligned to either the top, right, bottom, or left edges of a container.

Docked widgets will not scroll out of view, making them ideal for sticky headers, footers, and sidebars.

"""


class DockLayoutExample(App):
    CSS_PATH = "dock_layout2_sidebar.tcss"

    def compose(self) -> ComposeResult:
        yield Static("Sidebar2", id="another-sidebar")
        yield Static("Sidebar1", id="sidebar")
        yield Static(TEXT * 10, id="body")


app = DockLayoutExample()
if __name__ == "__main__":
    app.run()
```

**dock_layout2_sidebar.tcss**


```css
#another-sidebar {
    dock: left;
    width: 30;
    height: 100%;
    background: deeppink;
}

#sidebar {
    dock: left;
    width: 15;
    height: 100%;
    color: #0f2b41;
    background: dodgerblue;
}
```
Notice that the original sidebar (`#sidebar`) appears on top of the newly docked widget.
This is because `#sidebar` was yielded _after_ `#another-sidebar` inside the `compose` method.

Of course, we can also dock widgets to multiple edges within the same container.
The built-in `Header` widget contains some internal CSS which docks it to the top.
We can yield it inside `compose`, and without any additional CSS, we get a header fixed to the top of the screen.

**dock_layout3_sidebar_header.py**


```python
from textual.app import App, ComposeResult
from textual.widgets import Header, Static

TEXT = """\
Docking a widget removes it from the layout and fixes its position, aligned to either the top, right, bottom, or left edges of a container.

Docked widgets will not scroll out of view, making them ideal for sticky headers, footers, and sidebars.

"""


class DockLayoutExample(App):
    CSS_PATH = "dock_layout3_sidebar_header.tcss"

    def compose(self) -> ComposeResult:
        yield Header(id="header")
        yield Static("Sidebar1", id="sidebar")
        yield Static(TEXT * 10, id="body")


if __name__ == "__main__":
    app = DockLayoutExample()
    app.run()
```

**dock_layout3_sidebar_header.tcss**


```css
#sidebar {
    dock: left;
    width: 15;
    height: 100%;
    color: #0f2b41;
    background: dodgerblue;
}
```
If we wished for the sidebar to appear below the header, it'd simply be a case of yielding the sidebar before we yield the header.

## Layers

Textual has a concept of _layers_ which gives you finely grained control over the order widgets are placed.

When drawing widgets, Textual will first draw on _lower_ layers, working its way up to higher layers.
As such, widgets on higher layers will be drawn on top of those on lower layers.

Layer names are defined with a `layers` style on a container (parent) widget.
Descendants of this widget can then be assigned to one of these layers using a `layer` style.

The `layers` style takes a space-separated list of layer names.
The leftmost name is the lowest layer, and the rightmost is the highest layer.
Therefore, if you assign a descendant to the rightmost layer name, it'll be drawn on the top layer and will be visible above all other descendants.

An example `layers` declaration looks like: `layers: one two three;`.
To add a widget to the topmost layer in this case, you'd add a declaration of `layer: three;` to it.

In the example below, `#box1` is yielded before `#box2`.
Given our earlier discussion on yield order, you'd expect `#box2` to appear on top.
However, in this case, both `#box1` and `#box2` are assigned to layers which define the reverse order, so `#box1` is on top of `#box2`



**layers.py**


```python
from textual.app import App, ComposeResult
from textual.widgets import Static


class LayersExample(App):
    CSS_PATH = "layers.tcss"

    def compose(self) -> ComposeResult:
        yield Static("box1 (layer = above)", id="box1")
        yield Static("box2 (layer = below)", id="box2")


if __name__ == "__main__":
    app = LayersExample()
    app.run()
```

**layers.tcss**


```css
Screen {
    align: center middle;
    layers: below above;
}

Static {
    width: 28;
    height: 8;
    color: auto;
    content-align: center middle;
}

#box1 {
    layer: above;
    background: darkcyan;
}

#box2 {
    layer: below;
    background: orange;
    offset: 12 6;
}
```
## Offsets

Widgets have a relative offset which is added to the widget's location, _after_ its location has been determined via its parent's layout.
This means that if a widget hasn't had its offset modified using CSS or Python code, it will have an offset of `(0, 0)`.

![Offset](../images/layout/offset.excalidraw.svg)

The offset of a widget can be set using the `offset` CSS property.
`offset` takes two values.

* The first value defines the `x` (horizontal) offset. Positive values will shift the widget to the right. Negative values will shift the widget to the left.
* The second value defines the `y` (vertical) offset. Positive values will shift the widget down. Negative values will shift the widget up.


## Putting it all together

The sections above show how the various layouts in Textual can be used to position widgets on screen.
In a real application, you'll make use of several layouts.

The example below shows how an advanced layout can be built by combining the various techniques described on this page.

**combining_layouts.py**


```python
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.widgets import Header, Static


class CombiningLayoutsExample(App):
    CSS_PATH = "combining_layouts.tcss"

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="app-grid"):
            with VerticalScroll(id="left-pane"):
                for number in range(15):
                    yield Static(f"Vertical layout, child {number}")
            with Horizontal(id="top-right"):
                yield Static("Horizontally")
                yield Static("Positioned")
                yield Static("Children")
                yield Static("Here")
            with Container(id="bottom-right"):
                yield Static("This")
                yield Static("panel")
                yield Static("is")
                yield Static("using")
                yield Static("grid layout!", id="bottom-right-final")


if __name__ == "__main__":
    app = CombiningLayoutsExample()
    app.run()
```

**combining_layouts.tcss**


```css
#app-grid {
    layout: grid;
    grid-size: 2;  /* two columns */
    grid-columns: 1fr;
    grid-rows: 1fr;
}

#left-pane > Static {
    background: $boost;
    color: auto;
    margin-bottom: 1;
    padding: 1;
}

#left-pane {
    width: 100%;
    height: 100%;
    row-span: 2;
    background: $panel;
    border: dodgerblue;
}

#top-right {
    height: 100%;
    background: $panel;
    border: mediumvioletred;
}

#top-right > Static {
    width: auto;
    height: 100%;
    margin-right: 1;
    background: $boost;
}

#bottom-right {
    height: 100%;
    layout: grid;
    grid-size: 3;
    grid-columns: 1fr;
    grid-rows: 1fr;
    grid-gutter: 1;
    background: $panel;
    border: greenyellow;
}

#bottom-right-final {
    column-span: 2;
}

#bottom-right > Static {
    height: 100%;
    background: $boost;
}
```
Textual layouts make it easy to design and build real-life applications with relatively little code.

---

**See also**

- [Textual CSS](./CSS.md) - CSS selectors, specificity, and stylesheets
- [Styles guide](./styles.md) - Fundamental CSS styles including width, height, margin, and padding
- [Styles reference](../styles/index.md) - Comprehensive list of all CSS properties
- [Widgets](./widgets.md) - Compose and build custom widgets
