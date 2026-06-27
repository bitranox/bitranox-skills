# Styles

In this chapter we will explore how you can apply styles to your application to create beautiful user interfaces.

## Styles object

Every Textual widget class provides a `styles` object which contains a number of attributes. These attributes tell Textual how the widget should be displayed. Setting any of these attributes will update the screen accordingly.

> **Note**
>
>
> These docs use the term *screen* to describe the contents of the terminal, which will typically be a window on your desktop.


Let's look at a simple example which sets styles on `screen` (a special widget that represents the screen).

```python
from textual.app import App


class ScreenApp(App):
    def on_mount(self) -> None:
        self.screen.styles.background = "darkblue"
        self.screen.styles.border = ("heavy", "white")


if __name__ == "__main__":
    app = ScreenApp()
    app.run()
```

The first line sets the [background](../styles/background.md) style to `"darkblue"` which will change the background color to dark blue. There are a few other ways of setting color which we will explore later.

The second line sets [border](../styles/border.md) to a tuple of `("heavy", "white")` which tells Textual to draw a white border with a style of `"heavy"`. Running this code will show the following:


## Styling widgets

Setting styles on screen is useful, but to create most user interfaces we will also need to apply styles to other widgets.

The following example adds a static widget which we will apply some styles to:

```python
from textual.app import App, ComposeResult
from textual.widgets import Static


class WidgetApp(App):
    def compose(self) -> ComposeResult:
        self.widget = Static("Textual")
        yield self.widget

    def on_mount(self) -> None:
        self.widget.styles.background = "darkblue"
        self.widget.styles.border = ("heavy", "white")


if __name__ == "__main__":
    app = WidgetApp()
    app.run()
```

The compose method stores a reference to the widget before yielding it. In the mount handler we use that reference to set the same styles on the widget as we did for the screen example. Here is the result:


Widgets will occupy the full width of their container and as many lines as required to fit in the vertical direction.

Note how the combined height of the widget is three rows in the terminal. This is because a border adds two rows (and two columns). If you were to remove the line that sets the border style, the widget would occupy a single row.

> **Information**
>
>
> Widgets will wrap text by default. If you were to replace `"Textual"` with a long paragraph of text, the widget will expand downwards to fit.


## Colors

There are a number of style attributes which accept colors. The most commonly used are [color](../styles/color.md) which sets the default color of text on a widget, and [background](../styles/background.md) which sets the background color (beneath the text).

You can set a color value to one of a number of pre-defined color constants, such as `"crimson"`, `"lime"`, and `"palegreen"`. You can find a full list in the [Color API](../api/color.md#textual.color--named-colors).

Here's how you would set the screen background to lime:

```python
self.screen.styles.background = "lime"
```

In addition to color names, you can also use any of the following ways of expressing a color:

- RGB hex colors starts with a `#` followed by three pairs of one or two hex digits; one for the red, green, and blue color components. For example, `#f00` is an intense red color, and `#9932CC` is *dark orchid*.
- RGB decimal color start with `rgb` followed by a tuple of three numbers in the range 0 to 255. For example `rgb(255,0,0)` is intense red, and `rgb(153,50,204)` is *dark orchid*.
- HSL colors start with `hsl` followed by an angle between 0 and 360 and two percentage values, representing Hue, Saturation and Lightness. For example `hsl(0,100%,50%)` is intense red and `hsl(280,60%,49%)` is *dark orchid*.


The background and color styles also accept a `Color` object which can be used to create colors dynamically.

The following example adds three widgets and sets their color styles.

```python
from textual.app import App, ComposeResult
from textual.color import Color
from textual.widgets import Static


class ColorApp(App):
    def compose(self) -> ComposeResult:
        self.widget1 = Static("Textual One")
        yield self.widget1
        self.widget2 = Static("Textual Two")
        yield self.widget2
        self.widget3 = Static("Textual Three")
        yield self.widget3

    def on_mount(self) -> None:
        self.widget1.styles.background = "#9932CC"
        self.widget2.styles.background = "hsl(150,42.9%,49.4%)"
        self.widget2.styles.color = "blue"
        self.widget3.styles.background = Color(191, 78, 96)


if __name__ == "__main__":
    app = ColorApp()
    app.run()
```

Here is the output:


### Alpha

Textual represents color internally as a tuple of three values for the red, green, and blue components.

Textual supports a common fourth value called *alpha* which can make a color translucent. If you set alpha on a background color, Textual will blend the background with the color beneath it. If you set alpha on the text color, then Textual will blend the text with the background color.

There are a few ways you can set alpha on a color in Textual.

- You can set the alpha value of a color by adding a fourth digit or pair of digits to a hex color. The extra digits form an alpha component which ranges from 0 for completely transparent to 255 (completely opaque). Any value between 0 and 255 will be translucent. For example `"#9932CC7f"` is a dark orchid which is roughly 50% translucent.
- You can also set alpha with the `rgba` format, which is identical to `rgb` with the additional of a fourth value that should be between 0 and 1, where 0 is invisible and 1 is opaque. For example `"rgba(192,78,96,0.5)"`.
- You can add the `a` parameter on a `Color` object. For example `Color(192, 78, 96, a=0.5)` creates a translucent dark orchid.

The following example shows what happens when you set alpha on background colors:

```python
from textual.app import App, ComposeResult
from textual.color import Color
from textual.widgets import Static


class ColorApp(App):
    def compose(self) -> ComposeResult:
        self.widgets = [Static("") for n in range(10)]
        yield from self.widgets

    def on_mount(self) -> None:
        for index, widget in enumerate(self.widgets, 1):
            alpha = index * 0.1
            widget.update(f"alpha={alpha:.1f}")
            widget.styles.background = Color(191, 78, 96, a=alpha)


if __name__ == "__main__":
    app = ColorApp()
    app.run()
```

Notice that at an alpha of 0.1 the background almost matches the screen, but at 1.0 it is a solid color.


## Dimensions

Widgets occupy a rectangular region of the screen, which may be as small as a single character or as large as the screen (potentially *larger* if [scrolling](../styles/overflow.md) is enabled).

### Box Model

The following styles influence the dimensions of a widget.

- [width](../styles/width.md) and [height](../styles/height.md) define the size of the widget.
- [padding](../styles/padding.md) adds optional space around the content area.
- [border](../styles/border.md) draws an optional rectangular border around the padding and the content area.

Additionally, the [margin](../styles/margin.md) style adds space around a widget's border, which isn't technically part of the widget, but provides visual separation between widgets.

Together these styles compose the widget's *box model*. The following diagram shows how these settings are combined:

![Box model](../images/styles/box.excalidraw.svg)

### Width and height

Setting the width restricts the number of columns used by a widget, and setting the height restricts the number of rows. Let's look at an example which sets both dimensions.

```python
from textual.app import App, ComposeResult
from textual.widgets import Static


TEXT = """I must not fear.
Fear is the mind-killer.
Fear is the little-death that brings total obliteration.
I will face my fear.
I will permit it to pass over me and through me.
And when it has gone past, I will turn the inner eye to see its path.
Where the fear has gone there will be nothing. Only I will remain."""


class DimensionsApp(App):
    def compose(self) -> ComposeResult:
        self.widget = Static(TEXT)
        yield self.widget

    def on_mount(self) -> None:
        self.widget.styles.background = "purple"
        self.widget.styles.width = 30
        self.widget.styles.height = 10


if __name__ == "__main__":
    app = DimensionsApp()
    app.run()
```

This code produces the following result.


Note how the text wraps, but doesn't fit in the 10 lines provided, resulting in the last line being omitted entirely.

#### Auto dimensions

In practice, we generally want the size of a widget to adapt to its content, which we can do by setting a dimension to `"auto"`.

Let's set the height to auto and see what happens.

```python
from textual.app import App, ComposeResult
from textual.widgets import Static


TEXT = """I must not fear.
Fear is the mind-killer.
Fear is the little-death that brings total obliteration.
I will face my fear.
I will permit it to pass over me and through me.
And when it has gone past, I will turn the inner eye to see its path.
Where the fear has gone there will be nothing. Only I will remain."""


class DimensionsApp(App):
    def compose(self) -> ComposeResult:
        self.widget = Static(TEXT)
        yield self.widget

    def on_mount(self) -> None:
        self.widget.styles.background = "purple"
        self.widget.styles.width = 30
        self.widget.styles.height = "auto"


if __name__ == "__main__":
    app = DimensionsApp()
    app.run()
```

If you run this you will see the height of the widget now grows to accommodate the full text:


### Units

Textual offers a few different *units* which allow you to specify dimensions relative to the screen or container. Relative units can better make use of available space if the user resizes the terminal.

- Percentage units are given as a number followed by a percent (`%`) symbol and will set a dimension to a proportion of the widget's *parent* size. For instance, setting width to `"50%"` will cause a widget to be half the width of its parent.
- View units are similar to percentage units, but explicitly reference a dimension. The `vw` unit sets a dimension to a percentage of the terminal *width*, and `vh` sets a dimension to a percentage of the terminal *height*.
- The `w` unit sets a dimension to a percentage of the available width (which may be smaller than the terminal size if the widget is within another widget).
- The `h` unit sets a dimension to a percentage of the available height.


The following example demonstrates applying percentage units:

```python
from textual.app import App, ComposeResult
from textual.widgets import Static


TEXT = """I must not fear.
Fear is the mind-killer.
Fear is the little-death that brings total obliteration.
I will face my fear.
I will permit it to pass over me and through me.
And when it has gone past, I will turn the inner eye to see its path.
Where the fear has gone there will be nothing. Only I will remain."""


class DimensionsApp(App):
    def compose(self) -> ComposeResult:
        self.widget = Static(TEXT)
        yield self.widget

    def on_mount(self) -> None:
        self.widget.styles.background = "purple"
        self.widget.styles.width = "50%"
        self.widget.styles.height = "80%"


if __name__ == "__main__":
    app = DimensionsApp()
    app.run()
```

With the width set to `"50%"` and the height set to `"80%"`, the widget will keep those relative dimensions when resizing the terminal window:


#### FR units

Percentage units can be problematic for some relative values. For instance, if we want to divide the screen into thirds, we would have to set a dimension to `33.3333333333%` which is awkward. Textual supports `fr` units which are often better than percentage-based units for these situations.

When specifying `fr` units for a given dimension, Textual will divide the available space by the sum of the `fr` units for that dimension. That space is then assigned according to each widget's `fr` values.

Let's look at an example. We will create two widgets, one with a height of `"2fr"` and one with a height of `"1fr"`.

```python
from textual.app import App, ComposeResult
from textual.widgets import Static


TEXT = """I must not fear.
Fear is the mind-killer.
Fear is the little-death that brings total obliteration.
I will face my fear.
I will permit it to pass over me and through me.
And when it has gone past, I will turn the inner eye to see its path.
Where the fear has gone there will be nothing. Only I will remain."""


class DimensionsApp(App):
    def compose(self) -> ComposeResult:
        self.widget1 = Static(TEXT)
        yield self.widget1
        self.widget2 = Static(TEXT)
        yield self.widget2

    def on_mount(self) -> None:
        self.widget1.styles.background = "purple"
        self.widget2.styles.background = "darkgreen"
        self.widget1.styles.height = "2fr"
        self.widget2.styles.height = "1fr"


if __name__ == "__main__":
    app = DimensionsApp()
    app.run()
```

The total `fr` units for height is 3.
The first widget has a height ot `2fr`, which results in the height being two thirds of the total height.
The second widget has a height of `1fr` which makes it take up the remaining third of the height.
Here's what that looks like.


### Maximum and minimums

The same units may also be used to set limits on a dimension.
The following styles set minimum and maximum sizes and can accept any of the values used in width and height.

- [min-width](../styles/min_width.md) sets a minimum width.
- [max-width](../styles/max_width.md) sets a maximum width.
- [min-height](../styles/min_height.md) sets a minimum height.
- [max-height](../styles/max_height.md) sets a maximum height.

### Padding

Padding adds space around your content which can aid readability. Setting [padding](../styles/padding.md) to an integer will add that number additional rows and columns around the content area. The following example sets padding to 2:

```python
from textual.app import App, ComposeResult
from textual.widgets import Static


TEXT = """I must not fear.
Fear is the mind-killer.
Fear is the little-death that brings total obliteration.
I will face my fear.
I will permit it to pass over me and through me.
And when it has gone past, I will turn the inner eye to see its path.
Where the fear has gone there will be nothing. Only I will remain."""


class PaddingApp(App):
    def compose(self) -> ComposeResult:
        self.widget = Static(TEXT)
        yield self.widget

    def on_mount(self) -> None:
        self.widget.styles.background = "purple"
        self.widget.styles.width = 30
        self.widget.styles.padding = 2


if __name__ == "__main__":
    app = PaddingApp()
    app.run()
```

Notice the additional space around the text:


You can also set padding to a tuple of *two* integers which will apply padding to the top/bottom and left/right edges. The following example sets padding to `(2, 4)` which adds two rows to the top and bottom of the widget, and 4 columns to the left and right of the widget.

```python
from textual.app import App, ComposeResult
from textual.widgets import Static


TEXT = """I must not fear.
Fear is the mind-killer.
Fear is the little-death that brings total obliteration.
I will face my fear.
I will permit it to pass over me and through me.
And when it has gone past, I will turn the inner eye to see its path.
Where the fear has gone there will be nothing. Only I will remain."""


class PaddingApp(App):
    def compose(self) -> ComposeResult:
        self.widget = Static(TEXT)
        yield self.widget

    def on_mount(self) -> None:
        self.widget.styles.background = "purple"
        self.widget.styles.width = 30
        self.widget.styles.padding = (2, 4)


if __name__ == "__main__":
    app = PaddingApp()
    app.run()
```

Compare the output of this example to the previous example:


You can also set padding to a tuple of *four* values which applies padding to each edge individually. The first value is the padding for the top of the widget, followed by the right of the widget, then bottom, then left.

### Border

The [border](../styles/border.md) style draws a border around a widget. To add a border set `styles.border` to a tuple of two values. The first value is the border type, which should be a string. The second value is the border color which will accept any value that works with  [color](../styles/color.md) and [background](../styles/background.md).

The following example adds a border around a widget:

```python
from textual.app import App, ComposeResult
from textual.widgets import Label

TEXT = """I must not fear.
Fear is the mind-killer.
Fear is the little-death that brings total obliteration.
I will face my fear.
I will permit it to pass over me and through me.
And when it has gone past, I will turn the inner eye to see its path.
Where the fear has gone there will be nothing. Only I will remain."""


class BorderApp(App):
    def compose(self) -> ComposeResult:
        self.widget = Label(TEXT)
        yield self.widget

    def on_mount(self) -> None:
        self.widget.styles.background = "darkblue"
        self.widget.styles.width = "50%"
        self.widget.styles.border = ("heavy", "yellow")


if __name__ == "__main__":
    app = BorderApp()
    app.run()
```

Here is the result:


There are many other border types. Run the following from the command prompt to preview them.


```bash
textual borders
```
#### Title alignment

Widgets have two attributes, `border_title` and `border_subtitle` which (if set) will be displayed within the border.
The `border_title` attribute is displayed in the top border, and `border_subtitle` is displayed in the bottom border.

There are two styles to set the alignment of these border labels, which may be set to "left", "right", or "center".

 - [`border-title-align`](../styles/border_title_align.md) sets the alignment of the title, which defaults to "left".
 - [`border-subtitle-align`](../styles/border_subtitle_align.md) sets the alignment of the subtitle, which defaults to "right".

The following example sets both titles and changes the alignment of the title (top) to "center".

```python
from textual.app import App, ComposeResult
from textual.widgets import Static

TEXT = """I must not fear.
Fear is the mind-killer.
Fear is the little-death that brings total obliteration.
I will face my fear.
I will permit it to pass over me and through me.
And when it has gone past, I will turn the inner eye to see its path.
Where the fear has gone there will be nothing. Only I will remain."""


class BorderTitleApp(App[None]):
    def compose(self) -> ComposeResult:
        self.widget = Static(TEXT)
        yield self.widget

    def on_mount(self) -> None:
        self.widget.styles.background = "darkblue"
        self.widget.styles.width = "50%"
        self.widget.styles.border = ("heavy", "yellow")
        self.widget.border_title = "Litany Against Fear"
        self.widget.border_subtitle = "by Frank Herbert, in “Dune”"
        self.widget.styles.border_title_align = "center"


if __name__ == "__main__":
    app = BorderTitleApp()
    app.run()
```

Note the addition of the titles and their alignments:


### Outline

[Outline](../styles/outline.md) is similar to border and is set in the same way. The difference is that outline will not change the size of the widget, and may overlap the content area. The following example sets an outline on a widget:

```python
from textual.app import App, ComposeResult
from textual.widgets import Static


TEXT = """I must not fear.
Fear is the mind-killer.
Fear is the little-death that brings total obliteration.
I will face my fear.
I will permit it to pass over me and through me.
And when it has gone past, I will turn the inner eye to see its path.
Where the fear has gone there will be nothing. Only I will remain."""


class OutlineApp(App):
    def compose(self) -> ComposeResult:
        self.widget = Static(TEXT)
        yield self.widget

    def on_mount(self) -> None:
        self.widget.styles.background = "darkblue"
        self.widget.styles.width = "50%"
        self.widget.styles.outline = ("heavy", "yellow")


if __name__ == "__main__":
    app = OutlineApp()
    app.run()
```

Notice how the outline overlaps the text in the widget.


Outline can be useful to emphasize a widget, but be mindful that it may obscure your content.

### Box sizing

When you set padding or border it reduces the size of the widget's content area. In other words, setting padding or border won't change the width or height of the widget.

This is generally desirable when you arrange things on screen as you can add border or padding without breaking your layout. Occasionally though you may want to keep the size of the content area constant and grow the size of the widget to fit padding and border. The [box-sizing](../styles/box_sizing.md) style allows you to switch between these two modes.

If you set `box_sizing` to `"content-box"` then the space required for padding and border will be added to the widget dimensions. The default value of `box_sizing` is `"border-box"`. Compare the box model diagram for `content-box` to the box model for `border-box`.

**content-box**


![Content box](../images/styles/content_box.excalidraw.svg)

**border-box**


![Border box](../images/styles/border_box.excalidraw.svg)


The following example creates two widgets with a width of 30, a height of 6, and a border and padding of 1.
The first widget has the default `box_sizing` (`"border-box"`).
The second widget sets `box_sizing` to `"content-box"`.

```python
from textual.app import App, ComposeResult
from textual.widgets import Static


TEXT = """I must not fear.
Fear is the mind-killer.
Fear is the little-death that brings total obliteration.
I will face my fear.
I will permit it to pass over me and through me.
And when it has gone past, I will turn the inner eye to see its path.
Where the fear has gone there will be nothing. Only I will remain."""


class BoxSizing(App):
    def compose(self) -> ComposeResult:
        self.widget1 = Static(TEXT)
        yield self.widget1
        self.widget2 = Static(TEXT)
        yield self.widget2

    def on_mount(self) -> None:
        self.widget1.styles.background = "purple"
        self.widget2.styles.background = "darkgreen"
        self.widget1.styles.width = 30
        self.widget2.styles.width = 30
        self.widget1.styles.height = 6
        self.widget2.styles.height = 6
        self.widget1.styles.border = ("heavy", "white")
        self.widget2.styles.border = ("heavy", "white")
        self.widget1.styles.padding = 1
        self.widget2.styles.padding = 1
        self.widget2.styles.box_sizing = "content-box"


if __name__ == "__main__":
    app = BoxSizing()
    app.run()
```

The padding and border of the first widget is subtracted from the height leaving only 2 lines in the content area. The second widget also has a height of 6, but the padding and border adds additional height so that the content area remains 6 lines.


### Margin

Margin is similar to padding in that it adds space, but unlike padding, [margin](../styles/margin.md) is outside of the widget's border. It is used to add space between widgets.

The following example creates two widgets, each with a margin of 2.

```python
from textual.app import App, ComposeResult
from textual.widgets import Static


TEXT = """I must not fear.
Fear is the mind-killer.
Fear is the little-death that brings total obliteration.
I will face my fear.
I will permit it to pass over me and through me.
And when it has gone past, I will turn the inner eye to see its path.
Where the fear has gone there will be nothing. Only I will remain."""


class MarginApp(App):
    def compose(self) -> ComposeResult:
        self.widget1 = Static(TEXT)
        yield self.widget1
        self.widget2 = Static(TEXT)
        yield self.widget2

    def on_mount(self) -> None:
        self.widget1.styles.background = "purple"
        self.widget2.styles.background = "darkgreen"
        self.widget1.styles.border = ("heavy", "white")
        self.widget2.styles.border = ("heavy", "white")
        self.widget1.styles.margin = 2
        self.widget2.styles.margin = 2


if __name__ == "__main__":
    app = MarginApp()
    app.run()
```

Notice how each widget has an additional two rows and columns around the border.


> **Note: Margins overlap**
>
>
> In the above example both widgets have a margin of 2, but there are only 2 lines of space between the widgets. This is because margins of consecutive widgets *overlap*. In other words when there are two widgets next to each other Textual picks the greater of the two margins.


## More styles

We've covered some fundamental styles used by Textual apps, but there are many more which you can use to customize all aspects of how your app looks. See the [Styles reference](../styles/index.md) for a comprehensive list.

In the next chapter we will discuss Textual CSS which is a powerful way of applying styles to widgets that keeps your code free of style attributes.

---

**See also**

- [Styles reference](../styles/index.md) - Comprehensive list of all CSS properties
- [Textual CSS](./CSS.md) - CSS selectors, specificity, and stylesheets
- [Layout](./layout.md) - Arrange widgets using layout properties
- [Design](./design.md) - Theme colors and the design system
- [Animation](./animation.md) - Animate style transitions
