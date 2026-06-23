# Sparkline

> **Tip: Added in version 0.27.0**


A widget that is used to visually represent numerical data.

- [ ] Focusable
- [ ] Container

## Examples

### Basic example

The example below illustrates the relationship between the data, its length, the width of the sparkline, and the number of bars displayed.

> **Tip**
>
>
> The sparkline data is split into equally-sized chunks.
> Each chunk is represented by a bar and the width of the sparkline dictates how many bars there are.


**sparkline_basic.py**


```python
from textual.app import App, ComposeResult
from textual.widgets import Sparkline

data = [1, 2, 2, 1, 1, 4, 3, 1, 1, 8, 8, 2]  # (1)!


class SparklineBasicApp(App[None]):
    CSS_PATH = "sparkline_basic.tcss"

    def compose(self) -> ComposeResult:
        yield Sparkline(  # (2)!
            data,  # (3)!
            summary_function=max,  # (4)!
        )


app = SparklineBasicApp()
if __name__ == "__main__":
    app.run()
```

2. This sparkline will have its width set to 3 via CSS.
3. The data (12 numbers) will be split across 3 bars, so 4 data points are associated with each bar.
4. Each bar will represent its largest value.
The largest value of each chunk is 2, 4, and 8, respectively.
That explains why the first bar is half the height of the second and the second bar is half the height of the third.

**sparkline_basic.tcss**


```css
Screen {
    align: center middle;
}

Sparkline {
    width: 3;  /* (1)! */
    margin: 2;
}
```


### Different summary functions

The example below shows a sparkline widget with different summary functions.
The summary function is what determines the height of each bar.

**sparkline.py**


```python
import random
from statistics import mean

from textual.app import App, ComposeResult
from textual.widgets import Sparkline

random.seed(73)
data = [random.expovariate(1 / 3) for _ in range(1000)]


class SparklineSummaryFunctionApp(App[None]):
    CSS_PATH = "sparkline.tcss"

    def compose(self) -> ComposeResult:
        yield Sparkline(data, summary_function=max)  # (1)!
        yield Sparkline(data, summary_function=mean)  # (2)!
        yield Sparkline(data, summary_function=min)  # (3)!


app = SparklineSummaryFunctionApp()
if __name__ == "__main__":
    app.run()
```

2. Each bar will show the mean value of that bucket.
3. Each bar will show the smaller value of that bucket.

**sparkline.tcss**


```css
Sparkline {
    width: 100%;
    margin: 2;
}
```
### Changing the colors

The example below shows how to use component classes to change the colors of the sparkline.

**sparkline_colors.py**


```python
from math import sin

from textual.app import App, ComposeResult
from textual.widgets import Sparkline


class SparklineColorsApp(App[None]):
    CSS_PATH = "sparkline_colors.tcss"

    def compose(self) -> ComposeResult:
        nums = [abs(sin(x / 3.14)) for x in range(0, 360 * 6, 20)]
        yield Sparkline(nums, summary_function=max, id="fst")
        yield Sparkline(nums, summary_function=max, id="snd")
        yield Sparkline(nums, summary_function=max, id="trd")
        yield Sparkline(nums, summary_function=max, id="frt")
        yield Sparkline(nums, summary_function=max, id="fft")
        yield Sparkline(nums, summary_function=max, id="sxt")
        yield Sparkline(nums, summary_function=max, id="svt")
        yield Sparkline(nums, summary_function=max, id="egt")
        yield Sparkline(nums, summary_function=max, id="nnt")
        yield Sparkline(nums, summary_function=max, id="tnt")


app = SparklineColorsApp()
if __name__ == "__main__":
    app.run()
```

**sparkline_colors.tcss**


```css
Sparkline {
    width: 100%;
    margin: 1;
}

#fst > .sparkline--max-color {
    color: $success;
}
#fst > .sparkline--min-color {
    color: $warning;
}

#snd > .sparkline--max-color {
    color: $warning;
}
#snd > .sparkline--min-color {
    color: $success;
}

#trd > .sparkline--max-color {
    color: $error;
}
#trd > .sparkline--min-color {
    color: $warning;
}

#frt > .sparkline--max-color {
    color: $warning;
}
#frt > .sparkline--min-color {
    color: $error;
}

#fft > .sparkline--max-color {
    color: $accent;
}
#fft > .sparkline--min-color {
    color: $accent 30%;
}

#sxt > .sparkline--max-color {
    color: $primary 30%;
}
#sxt > .sparkline--min-color {
    color: $primary;
}

#svt > .sparkline--max-color {
    color: $error;
}
#svt > .sparkline--min-color {
    color: $error 30%;
}

#egt > .sparkline--max-color {
    color: $error 30%;
}
#egt > .sparkline--min-color {
    color: $error;
}

#nnt > .sparkline--max-color {
    color: $success;
}
#nnt > .sparkline--min-color {
    color: $success 30%;
}

#tnt > .sparkline--max-color {
    color: $success 30%;
}
#tnt > .sparkline--min-color {
    color: $success;
}
```
## Reactive Attributes

| Name               | Type                                 | Default | Description                                        |
|--------------------|--------------------------------------|---------|----------------------------------------------------|
| `data`             | `Sequence[float] | None`             | `None`  | The data represented by the sparkline.             |
| `summary_function` | `Callable[[Sequence[float]], float]` | `max`   | The function that computes the height of each bar. |


## Messages

This widget posts no messages.

## Bindings

This widget has no bindings.

## Component Classes

The sparkline widget provides the following component classes:

*API reference: `textual.widgets.Sparkline.COMPONENT_CLASSES`*


## See also

- [ProgressBar](./progress_bar.md) - Visualize progress as a bar
- [Digits](./digits.md) - Display numerical values in large characters
- [Widgets guide](../guide/widgets.md) - How to build and use widgets

---


*API reference: `textual.widgets.Sparkline`*
