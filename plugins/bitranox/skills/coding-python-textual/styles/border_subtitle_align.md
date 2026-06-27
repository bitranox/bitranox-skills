# Border-subtitle-align

The `border-subtitle-align` style sets the horizontal alignment for the border subtitle.

## Syntax

```
border-subtitle-align: <horizontal>;
```

The `border-subtitle-align` style takes a [`<horizontal>`](../css_types/horizontal.md) that determines where the border subtitle is aligned along the top edge of the border.
This means that the border corners are always visible.

### Default

The default alignment is `right`.


## Examples

### Basic usage

This example shows three labels, each with a different border subtitle alignment:

**border_subtitle_align.py**


```py
from textual.app import App
from textual.widgets import Label


class BorderSubtitleAlignApp(App):
    CSS_PATH = "border_subtitle_align.tcss"

    def compose(self):
        lbl = Label("My subtitle is on the left.", id="label1")
        lbl.border_subtitle = "< Left"
        yield lbl

        lbl = Label("My subtitle is centered", id="label2")
        lbl.border_subtitle = "Centered!"
        yield lbl

        lbl = Label("My subtitle is on the right", id="label3")
        lbl.border_subtitle = "Right >"
        yield lbl


if __name__ == "__main__":
    app = BorderSubtitleAlignApp()
    app.run()
```

**border_subtitle_align.tcss**


```css
#label1 {
    border: solid $secondary;
    border-subtitle-align: left;
}

#label2 {
    border: dashed $secondary;
    border-subtitle-align: center;
}

#label3 {
    border: tall $secondary;
    border-subtitle-align: right;
}

Screen > Label {
    width: 100%;
    height: 5;
    content-align: center middle;
    color: white;
    margin: 1;
    box-sizing: border-box;
}
```
### Complete usage reference

This example shows all border title and subtitle alignments, together with some examples of how (sub)titles can have custom markup.
Open the code tabs to see the details of the code examples.

**border_sub_title_align_all.py**


```python
from textual.app import App
from textual.containers import Container, Grid
from textual.widgets import Label


def make_label_container(  # (11)!
    text: str, id: str, border_title: str, border_subtitle: str
) -> Container:
    lbl = Label(text, id=id)
    lbl.border_title = border_title
    lbl.border_subtitle = border_subtitle
    return Container(lbl)


class BorderSubTitleAlignAll(App[None]):
    CSS_PATH = "border_sub_title_align_all.tcss"

    def compose(self):
        with Grid():
            yield make_label_container(  # (1)!
                "This is the story of",
                "lbl1",
                "[b]Border [i]title[/i][/]",
                "[u][r]Border[/r] subtitle[/]",
            )
            yield make_label_container(  # (2)!
                "a Python",
                "lbl2",
                "[b red]Left, but it's loooooooooooong",
                "[reverse]Center, but it's loooooooooooong",
            )
            yield make_label_container(  # (3)!
                "developer that",
                "lbl3",
                "[b i on purple]Left[/]",
                "[r u white on black]@@@[/]",
            )
            yield make_label_container(
                "had to fill up",
                "lbl4",
                "",  # (4)!
                "[link='https://textual.textualize.io']Left[/]",  # (5)!
            )
            yield make_label_container(  # (6)!
                "nine labels", "lbl5", "Title", "Subtitle"
            )
            yield make_label_container(  # (7)!
                "and ended up redoing it",
                "lbl6",
                "Title",
                "Subtitle",
            )
            yield make_label_container(  # (8)!
                "because the first try",
                "lbl7",
                "Title, but really loooooooooong!",
                "Subtitle, but really loooooooooong!",
            )
            yield make_label_container(  # (9)!
                "had some labels",
                "lbl8",
                "Title, but really loooooooooong!",
                "Subtitle, but really loooooooooong!",
            )
            yield make_label_container(  # (10)!
                "that were too long.",
                "lbl9",
                "Title, but really loooooooooong!",
                "Subtitle, but really loooooooooong!",
            )


if __name__ == "__main__":
    app = BorderSubTitleAlignAll()
    app.run()
```

3. (Sub)titles can be stylised with Rich markup.
4. An empty (sub)title isn't displayed.
5. The markup can even contain Rich links.
6. If the widget does not have a border, the title and subtitle are not shown.
7. When the side borders are not set, the (sub)title will align with the edge of the widget.
8. The title and subtitle are aligned on the left and very long, so they get truncated and we can still see the rightmost character of the border edge.
9. The title and subtitle are centered and very long, so they get truncated and are centered with one character of padding on each side.
10. The title and subtitle are aligned on the right and very long, so they get truncated and we can still see the leftmost character of the border edge.
11. An auxiliary function to create labels with border title and subtitle.

**border_sub_title_align_all.tcss**


```css
Grid {
    grid-size: 3 3;
    align: center middle;
}

Container {
    width: 100%;
    height: 100%;
    align: center middle;
}

#lbl1 {  /* (1)! */
    border: vkey $secondary;
}

#lbl2 {  /* (2)! */
    border: round $secondary;
    border-title-align: right;
    border-subtitle-align: right;
}

#lbl3 {
    border: wide $secondary;
    border-title-align: center;
    border-subtitle-align: center;
}

#lbl4 {
    border: ascii $success;
    border-title-align: center;  /* (3)! */
    border-subtitle-align: left;
}

#lbl5 {  /* (4)! */
    /* No border = no (sub)title. */
    border: none $success;
    border-title-align: center;
    border-subtitle-align: center;
}

#lbl6 {  /* (5)! */
    border-top: solid $success;
    border-bottom: solid $success;
}

#lbl7 {  /* (6)! */
    border-top: solid $error;
    border-bottom: solid $error;
    padding: 1 2;
    border-subtitle-align: left;
}

#lbl8 {
    border-top: solid $error;
    border-bottom: solid $error;
    border-title-align: center;
    border-subtitle-align: center;
}

#lbl9 {
    border-top: solid $error;
    border-bottom: solid $error;
    border-title-align: right;
}
```

3. Setting the alignment does not affect empty (sub)titles.
4. If the border is not set, or set to `none`/`hidden`, the (sub)title is not shown.
5. If the (sub)title alignment is on a side which does not have a border edge, the (sub)title will be flush to that side.
6. Naturally, (sub)title positioning is affected by padding.


## CSS

```css
border-subtitle-align: left;
border-subtitle-align: center;
border-subtitle-align: right;
```

## Python

```py
widget.styles.border_subtitle_align = "left"
widget.styles.border_subtitle_align = "center"
widget.styles.border_subtitle_align = "right"
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
