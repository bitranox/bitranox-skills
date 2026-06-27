# Rule

A rule widget to separate content, similar to a `<hr>` HTML tag.

- [ ] Focusable
- [ ] Container

## Examples

### Horizontal Rule

The default orientation of a rule is horizontal.

The example below shows horizontal rules with all the available line styles.

**horizontal_rules.py**


```python
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Label, Rule


class HorizontalRulesApp(App):
    CSS_PATH = "horizontal_rules.tcss"

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("solid (default)")
            yield Rule()
            yield Label("heavy")
            yield Rule(line_style="heavy")
            yield Label("thick")
            yield Rule(line_style="thick")
            yield Label("dashed")
            yield Rule(line_style="dashed")
            yield Label("double")
            yield Rule(line_style="double")
            yield Label("ascii")
            yield Rule(line_style="ascii")


if __name__ == "__main__":
    app = HorizontalRulesApp()
    app.run()
```

**horizontal_rules.tcss**


```css
Screen {
    align: center middle;
}

Vertical {
    height: auto;
    width: 80%;
}

Label {
    width: 100%;
    text-align: center;
}
```
### Vertical Rule

The example below shows vertical rules with all the available line styles.

**vertical_rules.py**


```python
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Label, Rule


class VerticalRulesApp(App):
    CSS_PATH = "vertical_rules.tcss"

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label("solid")
            yield Rule(orientation="vertical")
            yield Label("heavy")
            yield Rule(orientation="vertical", line_style="heavy")
            yield Label("thick")
            yield Rule(orientation="vertical", line_style="thick")
            yield Label("dashed")
            yield Rule(orientation="vertical", line_style="dashed")
            yield Label("double")
            yield Rule(orientation="vertical", line_style="double")
            yield Label("ascii")
            yield Rule(orientation="vertical", line_style="ascii")


if __name__ == "__main__":
    app = VerticalRulesApp()
    app.run()
```

**vertical_rules.tcss**


```css
Screen {
    align: center middle;
}

Horizontal {
    width: auto;
    height: 80%;
}

Label {
    width: 6;
    height: 100%;
    text-align: center;
}
```
## Reactive Attributes

| Name          | Type              | Default        | Description                  |
|---------------|-------------------|----------------|------------------------------|
| `orientation` | `RuleOrientation` | `"horizontal"` | The orientation of the rule. |
| `line_style`  | `LineStyle`       | `"solid"`      | The line style of the rule.  |

## Messages

This widget sends no messages.

## Bindings

This widget has no bindings.

## Component Classes

This widget has no component classes.

## See also

- [Widgets guide](../guide/widgets.md) - How to build and use widgets
- [Layout guide](../guide/layout.md) - How to design layouts for your app

---


*API reference: `textual.widgets.Rule`*


*API reference: `textual.widgets.rule`*
