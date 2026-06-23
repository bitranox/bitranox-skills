# Border-subtitle-color

The `border-subtitle-color` style sets the color of the `border_subtitle`.

## Syntax

```
border-subtitle-color: (<color> | auto) [<percentage>];
```
## Example

The following examples demonstrates customization of the border color and text style rules.

**border_title_colors.py**


```python
from textual.app import App, ComposeResult
from textual.widgets import Label


class BorderTitleApp(App):
    CSS_PATH = "border_title_colors.tcss"

    def compose(self) -> ComposeResult:
        yield Label("Hello, World!")

    def on_mount(self) -> None:
        label = self.query_one(Label)
        label.border_title = "Textual Rocks"
        label.border_subtitle = "Textual Rocks"


if __name__ == "__main__":
    app = BorderTitleApp()
    app.run()
```

**border_title_colors.tcss**


```css
Screen {
    align: center middle;
}

Label {
    padding: 4 8;
    border: heavy red;

    border-title-color: green;
    border-title-background: white;
    border-title-style: bold;

    border-subtitle-color: magenta;
    border-subtitle-background: yellow;
    border-subtitle-style: italic;
}
```
## CSS

```css
border-subtitle-color: red;
```

## Python

```python
widget.styles.border_subtitle_color = "red"
```
## See also

- [`border-title-align`](./border_title_align.md) to set the title's alignment.
- [`border-title-color`](./border_title_color.md) to set the title's color.
- [`border-title-background`](./border_title_background.md) to set the title's background color.
- [`border-title-style`](./border_title_style.md) to set the title's text style.

- [`border-subtitle-align`](./border_subtitle_align.md) to set the sub-title's alignment.
- [`border-subtitle-color`](./border_subtitle_color.md) to set the sub-title's color.
- [`border-subtitle-background`](./border_subtitle_background.md) to set the sub-title's background color.
- [`border-subtitle-style`](./border_subtitle_style.md) to set the sub-title's text style.
