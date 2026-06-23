---
name: textual
description: Textual TUI framework documentation reference
---

# Textual Framework Documentation

Textual is a Python framework for building terminal and web UIs by [Textualize.io](https://www.textualize.io). See [index.md](index.md) for the landing page.

Tables below map topics to markdown files. Use the Read tool to load referenced files identified as relevant for full details.
Start with the most specific section: Widgets for widget docs, Styles for CSS properties,
Events for event handlers, API Reference for module-level API, Examples for runnable code.
Documents are cross-referenced: each page has a "See also" section linking to related pages.
CSS type pages have "Used by" sections listing all style properties that accept that type.
API stubs link to their corresponding guide pages for in-depth explanations.
In the Examples section, entries marked (+tcss) have a companion .tcss stylesheet.

---

## Getting Started

| Page                                  | Description                                            |
|---------------------------------------|--------------------------------------------------------|
| [Getting Started](getting_started.md) | Installation and first steps with Textual              |
| [Tutorial](tutorial.md)               | Step-by-step tutorial building a stopwatch application |
| [FAQ](FAQ.md)                         | Frequently asked questions                             |
| [Help](help.md)                       | Getting help and reporting issues                      |
| [Roadmap](roadmap.md)                 | Project roadmap and planned features                   |
| [Linux Console](linux-console.md)     | Notes on running Textual in the Linux console          |

---

## Guide

The Textual guide covers core concepts for building terminal applications. Each guide page links to related guides, widgets, styles, and events. See [guide/index.md](guide/index.md).

| Page                                        | Description                                                          |
|---------------------------------------------|----------------------------------------------------------------------|
| [App Basics](guide/app.md)                  | Creating and running Textual applications                            |
| [Textual CSS](guide/CSS.md)                 | Styling with Textual CSS, the DOM, and selectors                     |
| [Actions](guide/actions.md)                 | Allow-listed functions with string syntax for links and key bindings |
| [Animation](guide/animation.md)             | Visual effects such as movement, blending, and fading                |
| [Command Palette](guide/command_palette.md) | Built-in command palette for quick access to app functionality       |
| [Content](guide/content.md)                 | Specifying and formatting widget content                             |
| [Themes](guide/design.md)                   | Built-in themes and creating custom themes                           |
| [Devtools](guide/devtools.md)               | Development tools for debugging Textual apps                         |
| [Events and Messages](guide/events.md)      | Event handling and the message system                                |
| [Input](guide/input.md)                     | Responding to key presses and mouse actions                          |
| [Layout](guide/layout.md)                   | Arranging widgets with vertical, horizontal, grid, and dock layouts  |
| [DOM Queries](guide/queries.md)             | Finding and updating widgets using CSS selectors in Python           |
| [Reactivity](guide/reactivity.md)           | Reactive attributes for simplified app state management              |
| [Screens](guide/screens.md)                 | Creating screens and switching between them                          |
| [Styles](guide/styles.md)                   | Applying styles to create user interfaces                            |
| [Testing](guide/testing.md)                 | Writing tests for Textual applications                               |
| [Widgets](guide/widgets.md)                 | Exploring widgets and creating custom widgets                        |
| [Workers](guide/workers.md)                 | Concurrency and the Worker API                                       |

---

## Widgets

Reference documentation for all built-in widgets. Each widget page includes a "See also" section linking to related widgets, events, and guide pages. See [widgets/index.md](widgets/index.md) or the [Widget Gallery](widget_gallery.md) for an overview.

| Page                                             | Description                                                                  |
|--------------------------------------------------|------------------------------------------------------------------------------|
| [Button](widgets/button.md)                      | A simple button with a variety of semantic styles                            |
| [Checkbox](widgets/checkbox.md)                  | A classic checkbox control                                                   |
| [Collapsible](widgets/collapsible.md)            | Content that may be toggled on and off by clicking a title                   |
| [ContentSwitcher](widgets/content_switcher.md)   | A widget for containing and switching display between multiple child widgets |
| [DataTable](widgets/data_table.md)               | A powerful data table with configurable cursors                              |
| [Digits](widgets/digits.md)                      | Display numbers in tall characters                                           |
| [DirectoryTree](widgets/directory_tree.md)       | A tree view of files and folders                                             |
| [Footer](widgets/footer.md)                      | A footer to display and interact with key bindings                           |
| [Header](widgets/header.md)                      | A header to display the app's title and subtitle                             |
| [Input](widgets/input.md)                        | A control to enter text                                                      |
| [Label](widgets/label.md)                        | A simple text label                                                          |
| [Link](widgets/link.md)                          | A clickable link that opens a URL                                            |
| [ListItem](widgets/list_item.md)                 | An item within a ListView                                                    |
| [ListView](widgets/list_view.md)                 | Display a list of items (items may be other widgets)                         |
| [LoadingIndicator](widgets/loading_indicator.md) | Display an animation while data is loading                                   |
| [Log](widgets/log.md)                            | Display and update lines of text (such as from a file)                       |
| [Markdown](widgets/markdown.md)                  | Display a Markdown document                                                  |
| [MarkdownViewer](widgets/markdown_viewer.md)     | Display and interact with a Markdown document with navigation                |
| [MaskedInput](widgets/masked_input.md)           | A control to enter input according to a template mask                        |
| [OptionList](widgets/option_list.md)             | Display a vertical list of options                                           |
| [Placeholder](widgets/placeholder.md)            | Display placeholder content while designing a UI                             |
| [Pretty](widgets/pretty.md)                      | Display a pretty-formatted Rich renderable                                   |
| [ProgressBar](widgets/progress_bar.md)           | A configurable progress bar with ETA and percentage complete                 |
| [RadioButton](widgets/radiobutton.md)            | A simple radio button                                                        |
| [RadioSet](widgets/radioset.md)                  | A collection of radio buttons that enforces uniqueness                       |
| [RichLog](widgets/rich_log.md)                   | Display and update text in a scrolling panel                                 |
| [Rule](widgets/rule.md)                          | A rule widget to separate content, similar to an HTML `<hr>` tag             |
| [Select](widgets/select.md)                      | Select from a number of possible options                                     |
| [SelectionList](widgets/selection_list.md)       | Select multiple values from a list of options                                |
| [Sparkline](widgets/sparkline.md)                | Display numerical data as a sparkline                                        |
| [Static](widgets/static.md)                      | Displays simple static content; typically used as a base class               |
| [Switch](widgets/switch.md)                      | An on/off control, inspired by toggle buttons                                |
| [TabbedContent](widgets/tabbed_content.md)       | A combination of Tabs and ContentSwitcher to navigate static content         |
| [Tabs](widgets/tabs.md)                          | A row of tabs you can select with the mouse or navigate with keys            |
| [TextArea](widgets/text_area.md)                 | A multi-line text area with syntax highlighting                              |
| [Toast](widgets/toast.md)                        | A notification message widget used by the built-in notify system             |
| [Tree](widgets/tree.md)                          | A tree control with expandable nodes                                         |

---

## Styles

CSS styles for customizing appearance and layout. Each style page links to related properties and CSS types. See [styles/index.md](styles/index.md).

### Subsections

| Section                                              | Description                |
|------------------------------------------------------|----------------------------|
| [Grid](styles/grid/index.md)                         | Grid layout properties     |
| [Links](styles/links/index.md)                       | Link styling properties    |
| [Scrollbar Colors](styles/scrollbar_colors/index.md) | Scrollbar color properties |

### Style Properties

| Page                                                               | Description                                                    |
|--------------------------------------------------------------------|----------------------------------------------------------------|
| [Align](styles/align.md)                                           | Defines how a widget's children are aligned                    |
| [Background](styles/background.md)                                 | Sets the background color of a widget                          |
| [Background-tint](styles/background_tint.md)                       | Modifies the background color by tinting it with a new color   |
| [Border](styles/border.md)                                         | Enables the drawing of a box around a widget                   |
| [Border-subtitle-align](styles/border_subtitle_align.md)           | Sets the horizontal alignment for the border subtitle          |
| [Border-subtitle-background](styles/border_subtitle_background.md) | Sets the background color of the border subtitle               |
| [Border-subtitle-color](styles/border_subtitle_color.md)           | Sets the color of the border subtitle                          |
| [Border-subtitle-style](styles/border_subtitle_style.md)           | Sets the text style of the border subtitle                     |
| [Border-title-align](styles/border_title_align.md)                 | Sets the horizontal alignment for the border title             |
| [Border-title-background](styles/border_title_background.md)       | Sets the background color of the border title                  |
| [Border-title-color](styles/border_title_color.md)                 | Sets the color of the border title                             |
| [Border-title-style](styles/border_title_style.md)                 | Sets the text style of the border title                        |
| [Box-sizing](styles/box_sizing.md)                                 | Determines how the width and height of a widget are calculated |
| [Color](styles/color.md)                                           | Sets the text color of a widget                                |
| [Content-align](styles/content_align.md)                           | Aligns content inside a widget                                 |
| [Display](styles/display.md)                                       | Defines whether a widget is displayed or not                   |
| [Dock](styles/dock.md)                                             | Fixes a widget to the edge of a container                      |
| [Hatch](styles/hatch.md)                                           | Fills a widget's background with a repeating character pattern |
| [Height](styles/height.md)                                         | Sets a widget's height                                         |
| [Keyline](styles/keyline.md)                                       | Draws lines around child widgets in a container                |
| [Layer](styles/layer.md)                                           | Defines the layer a widget belongs to                          |
| [Layers](styles/layers.md)                                         | Defines an ordered set of layers                               |
| [Layout](styles/layout.md)                                         | Defines how a widget arranges its children                     |
| [Margin](styles/margin.md)                                         | Specifies spacing around a widget                              |
| [Max-height](styles/max_height.md)                                 | Sets a maximum height for a widget                             |
| [Max-width](styles/max_width.md)                                   | Sets a maximum width for a widget                              |
| [Min-height](styles/min_height.md)                                 | Sets a minimum height for a widget                             |
| [Min-width](styles/min_width.md)                                   | Sets a minimum width for a widget                              |
| [Offset](styles/offset.md)                                         | Defines an offset for the position of a widget                 |
| [Opacity](styles/opacity.md)                                       | Sets the opacity of a widget                                   |
| [Outline](styles/outline.md)                                       | Draws a box around the content area of a widget                |
| [Overflow](styles/overflow.md)                                     | Specifies if and when scrollbars should be displayed           |
| [Padding](styles/padding.md)                                       | Specifies spacing around the content of a widget               |
| [Pointer](styles/pointer.md)                                       | Sets the shape of the mouse pointer when over a widget         |
| [Position](styles/position.md)                                     | Modifies what offset is applied to                             |
| [Scrollbar-gutter](styles/scrollbar_gutter.md)                     | Reserves space for a vertical scrollbar                        |
| [Scrollbar-size](styles/scrollbar_size.md)                         | Defines the width of scrollbars                                |
| [Scrollbar-visibility](styles/scrollbar_visibility.md)             | Shows or hides scrollbars                                      |
| [Text-align](styles/text_align.md)                                 | Sets the text alignment in a widget                            |
| [Text-opacity](styles/text_opacity.md)                             | Blends the foreground color with the background color          |
| [Text-overflow](styles/text_overflow.md)                           | Defines what happens when text overflows                       |
| [Text-style](styles/text_style.md)                                 | Sets the style for the text in a widget                        |
| [Text-wrap](styles/text_wrap.md)                                   | Sets how Textual should wrap text                              |
| [Tint](styles/tint.md)                                             | Blends a color with the whole widget                           |
| [Visibility](styles/visibility.md)                                 | Determines whether a widget is visible or not                  |
| [Width](styles/width.md)                                           | Sets a widget's width                                          |

### Grid Properties

| Page                                        | Description                                                    |
|---------------------------------------------|----------------------------------------------------------------|
| [Column-span](styles/grid/column_span.md)   | Specifies how many columns a widget will span in a grid layout |
| [Grid-columns](styles/grid/grid_columns.md) | Defines the width of the columns of the grid                   |
| [Grid-gutter](styles/grid/grid_gutter.md)   | Sets the spacing between adjacent cells in the grid            |
| [Grid-rows](styles/grid/grid_rows.md)       | Defines the height of the rows of the grid                     |
| [Grid-size](styles/grid/grid_size.md)       | Sets the number of columns and rows in a grid layout           |
| [Row-span](styles/grid/row_span.md)         | Specifies how many rows a widget will span in a grid layout    |

### Link Styles

| Page                                                           | Description                                                      |
|----------------------------------------------------------------|------------------------------------------------------------------|
| [Link-background](styles/links/link_background.md)             | Sets the background color of the link                            |
| [Link-background-hover](styles/links/link_background_hover.md) | Sets the background color of the link when the cursor is over it |
| [Link-color](styles/links/link_color.md)                       | Sets the color of the link text                                  |
| [Link-color-hover](styles/links/link_color_hover.md)           | Sets the color of the link text when the cursor is over it       |
| [Link-style](styles/links/link_style.md)                       | Sets the text style for the link text                            |
| [Link-style-hover](styles/links/link_style_hover.md)           | Sets the text style for the link text when the cursor is over it |

### Scrollbar Color Properties

| Page                                                                                  | Description                                                          |
|---------------------------------------------------------------------------------------|----------------------------------------------------------------------|
| [Scrollbar-background](styles/scrollbar_colors/scrollbar_background.md)               | Sets the background color of the scrollbar                           |
| [Scrollbar-background-active](styles/scrollbar_colors/scrollbar_background_active.md) | Sets the scrollbar background color when the thumb is being dragged  |
| [Scrollbar-background-hover](styles/scrollbar_colors/scrollbar_background_hover.md)   | Sets the scrollbar background color when the cursor is over it       |
| [Scrollbar-color](styles/scrollbar_colors/scrollbar_color.md)                         | Sets the color of the scrollbar thumb                                |
| [Scrollbar-color-active](styles/scrollbar_colors/scrollbar_color_active.md)           | Sets the scrollbar thumb color when it is being dragged              |
| [Scrollbar-color-hover](styles/scrollbar_colors/scrollbar_color_hover.md)             | Sets the scrollbar thumb color when the cursor is over it            |
| [Scrollbar-corner-color](styles/scrollbar_colors/scrollbar_corner_color.md)           | Sets the color of the gap between horizontal and vertical scrollbars |

---

## Events

Reference for all built-in events. Each event page links to complementary events, related widgets, and the events guide. See [events/index.md](events/index.md) or the [Events guide](guide/events.md).

| Page                                             | Description                                |
|--------------------------------------------------|--------------------------------------------|
| [AppBlur](events/app_blur.md)                    | Sent when the application loses focus      |
| [AppFocus](events/app_focus.md)                  | Sent when the application gains focus      |
| [Blur](events/blur.md)                           | Sent when a widget loses focus             |
| [Click](events/click.md)                         | Sent when a widget is clicked              |
| [DescendantBlur](events/descendant_blur.md)      | Sent when a descendant widget loses focus  |
| [DescendantFocus](events/descendant_focus.md)    | Sent when a descendant widget gains focus  |
| [Enter](events/enter.md)                         | Sent when the mouse enters a widget        |
| [Focus](events/focus.md)                         | Sent when a widget gains focus             |
| [Hide](events/hide.md)                           | Sent when a widget is hidden               |
| [Key](events/key.md)                             | Sent when a key is pressed                 |
| [Leave](events/leave.md)                         | Sent when the mouse leaves a widget        |
| [Load](events/load.md)                           | Sent when the application is loading       |
| [Mount](events/mount.md)                         | Sent when a widget is mounted to the DOM   |
| [MouseCapture](events/mouse_capture.md)          | Sent when a widget captures the mouse      |
| [MouseDown](events/mouse_down.md)                | Sent when a mouse button is pressed        |
| [MouseMove](events/mouse_move.md)                | Sent when the mouse moves over a widget    |
| [MouseRelease](events/mouse_release.md)          | Sent when a widget releases the mouse      |
| [MouseScrollDown](events/mouse_scroll_down.md)   | Sent when the mouse scrolls down           |
| [MouseScrollLeft](events/mouse_scroll_left.md)   | Sent when the mouse scrolls left           |
| [MouseScrollRight](events/mouse_scroll_right.md) | Sent when the mouse scrolls right          |
| [MouseScrollUp](events/mouse_scroll_up.md)       | Sent when the mouse scrolls up             |
| [MouseUp](events/mouse_up.md)                    | Sent when a mouse button is released       |
| [Paste](events/paste.md)                         | Sent when text is pasted into the terminal |
| [Print](events/print.md)                         | Sent when the app receives a print request |
| [Resize](events/resize.md)                       | Sent when a widget is resized              |
| [ScreenResume](events/screen_resume.md)          | Sent when a screen is resumed              |
| [ScreenSuspend](events/screen_suspend.md)        | Sent when a screen is suspended            |
| [Show](events/show.md)                           | Sent when a widget becomes visible         |
| [Unmount](events/unmount.md)                     | Sent when a widget is removed from the DOM |

---

## CSS Types

CSS types define the values that Textual CSS styles accept. Each type page includes a "Used by" section listing all style properties that accept it. See [css_types/index.md](css_types/index.md).

| Page                                    | Description                                                                                                                       |
|-----------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------|
| [<border>](css_types/border.md)         | Border style type — used by border, outline                                                                                       |
| [<color>](css_types/color.md)           | Color type — used by 23 style properties (background, color, tint, border colors, link colors, scrollbar colors)                  |
| [<hatch>](css_types/hatch.md)           | Hatch character type — used by hatch                                                                                              |
| [<horizontal>](css_types/horizontal.md) | Horizontal position — used by align, content-align, border-title-align, border-subtitle-align                                     |
| [<integer>](css_types/integer.md)       | Integer type — used by column-span, row-span, grid-size, grid-gutter, margin, padding, scrollbar-size                             |
| [<keyline>](css_types/keyline.md)       | Keyline style type — used by keyline                                                                                              |
| [<name>](css_types/name.md)             | Name identifier type — used by layer, layers                                                                                      |
| [<number>](css_types/number.md)         | Number type (int or decimal) — used by opacity, text-opacity                                                                      |
| [<overflow>](css_types/overflow.md)     | Overflow mode type — used by overflow                                                                                             |
| [<percentage>](css_types/percentage.md) | Percentage type — used by 22 style properties (color alphas, opacity, background, tint)                                           |
| [<pointer>](css_types/pointer.md)       | Mouse cursor shape type — used by pointer                                                                                         |
| [<position>](css_types/position.md)     | Offset application mode — used by position                                                                                        |
| [<scalar>](css_types/scalar.md)         | Length type (number + unit or auto) — used by width, height, min/max dimensions, margin, padding, offset, grid-columns, grid-rows |
| [<text-align>](css_types/text_align.md) | Text alignment type — used by text-align                                                                                          |
| [<text-style>](css_types/text_style.md) | Text style type — used by text-style, border-title-style, border-subtitle-style, link-style, link-style-hover                     |
| [<vertical>](css_types/vertical.md)     | Vertical position — used by align, content-align                                                                                  |

---

## API Reference

Module-level API reference. Each API stub links to its corresponding guide page for in-depth coverage. See [api/index.md](api/index.md).

| Module                                                   | Description                                  |
|----------------------------------------------------------|----------------------------------------------|
| [textual.app](api/app.md)                                | The App class and related utilities          |
| [textual.await_complete](api/await_complete.md)          | AwaitComplete for background work completion |
| [textual.await_remove](api/await_remove.md)              | AwaitRemove for widget removal               |
| [textual.binding](api/binding.md)                        | Key bindings                                 |
| [textual.cache](api/cache.md)                            | Caching utilities                            |
| [textual.color](api/color.md)                            | Color handling and manipulation              |
| [textual.command](api/command.md)                        | Command palette                              |
| [textual.compose](api/compose.md)                        | Compose utility                              |
| [textual.constants](api/constants.md)                    | Framework constants                          |
| [textual.containers](api/containers.md)                  | Layout containers                            |
| [textual.content](api/content.md)                        | Content rendering                            |
| [textual.coordinate](api/coordinate.md)                  | Coordinate data type                         |
| [textual.dom](api/dom_node.md)                           | DOM node base class                          |
| [textual.errors](api/errors.md)                          | Exception classes                            |
| [textual.events](api/events.md)                          | Event classes                                |
| [textual.filter](api/filter.md)                          | Display filters                              |
| [textual.fuzzy](api/fuzzy_matcher.md)                    | Fuzzy matching                               |
| [textual.geometry](api/geometry.md)                      | Geometry primitives                          |
| [textual.getters](api/getters.md)                        | Getter utilities                             |
| [textual.highlight](api/highlight.md)                    | Syntax highlighting                          |
| [textual.layout](api/layout.md)                          | Layout engine                                |
| [textual.lazy](api/lazy.md)                              | Lazy loading                                 |
| [textual (logger)](api/logger.md)                        | Root logger                                  |
| [textual.logging](api/logging.md)                        | Logging utilities                            |
| [textual.map_geometry](api/map_geometry.md)              | Map geometry data structure                  |
| [textual.markup](api/markup.md)                          | Markup processing                            |
| [textual.message](api/message.md)                        | Message base class                           |
| [textual.message_pump](api/message_pump.md)              | Message pump                                 |
| [textual.on](api/on.md)                                  | The on decorator for event handling          |
| [textual.pilot](api/pilot.md)                            | Testing pilot                                |
| [textual.css.query](api/query.md)                        | DOM query API                                |
| [textual.reactive](api/reactive.md)                      | Reactive attributes                          |
| [textual.renderables](api/renderables.md)                | Rich renderables for widgets                 |
| [textual.screen](api/screen.md)                          | Screen class                                 |
| [textual.scroll_view](api/scroll_view.md)                | Scroll view widget                           |
| [textual.scrollbar](api/scrollbar.md)                    | Scrollbar widget                             |
| [textual.signal](api/signal.md)                          | Signal for pub/sub messaging                 |
| [textual.strip](api/strip.md)                            | Strip rendering                              |
| [textual.style](api/style.md)                            | Style data type                              |
| [textual.suggester](api/suggester.md)                    | Input suggestion                             |
| [textual.system_commands](api/system_commands_source.md) | System commands                              |
| [textual.timer](api/timer.md)                            | Timer utilities                              |
| [textual.types](api/types.md)                            | Type exports                                 |
| [textual.validation](api/validation.md)                  | Input validation                             |
| [textual.walk](api/walk.md)                              | DOM tree walking                             |
| [textual.widget](api/widget.md)                          | Widget base class                            |
| [textual.work](api/work.md)                              | Work decorator                               |
| [textual.worker](api/worker.md)                          | Worker class                                 |
| [textual.worker_manager](api/worker_manager.md)          | Worker manager                               |

---

## How-To Guides

Practical articles covering various Textual topics. Each guide links to relevant reference pages and guide sections. See [how-to/index.md](how-to/index.md).

| Guide                                                  | Description                                                 |
|--------------------------------------------------------|-------------------------------------------------------------|
| [Center Things](how-to/center-things.md)               | Different ways to center widgets, text, and content         |
| [Design a Layout](how-to/design-a-layout.md)           | Tips for designing your application layout from scratch     |
| [Package with Hatch](how-to/package-with-hatch.md)     | How to package and publish a Textual app using Hatch        |
| [Render and Compose](how-to/render-and-compose.md)     | Understanding the difference between render() and compose() |
| [Style Inline Apps](how-to/style-inline-apps.md)       | Customizing the appearance of inline-mode apps              |
| [Work with Containers](how-to/work-with-containers.md) | Using container widgets to arrange layout                   |

---

## Examples

Example source code referenced throughout these docs (317 entries). Files marked *(+tcss)* have a companion `.tcss` stylesheet with the same base name.

### App

| File                                                    | Description                                                          |
|---------------------------------------------------------|----------------------------------------------------------------------|
| [event01.py](examples/app/event01.py)                   | Demonstrates changing screen background color on key press events    |
| [question01.py](examples/app/question01.py)             | Simple yes/no question app returning button press result             |
| [question02.py](examples/app/question02.py)             | Question app with external TCSS stylesheet for grid layout *(+tcss)* |
| [question03.py](examples/app/question03.py)             | Question app with inline CSS grid layout styling                     |
| [question_title01.py](examples/app/question_title01.py) | Question app with Header widget, title, and subtitle                 |
| [question_title02.py](examples/app/question_title02.py) | Question app updating title and subtitle on key events               |
| [simple01.py](examples/app/simple01.py)                 | Minimal empty Textual App subclass definition                        |
| [simple02.py](examples/app/simple02.py)                 | Minimal Textual app with run entry point                             |
| [suspend.py](examples/app/suspend.py)                   | Demonstrates suspending the app to run an external editor            |
| [suspend_process.py](examples/app/suspend_process.py)   | Demonstrates Ctrl+Z key binding to suspend the process               |
| [widgets01.py](examples/app/widgets01.py)               | Welcome widget app that exits on button press                        |
| [widgets02.py](examples/app/widgets02.py)               | Mounts Welcome widget dynamically on any key press                   |
| [widgets03.py](examples/app/widgets03.py)               | Dynamically mounts Welcome widget and changes button label           |
| [widgets04.py](examples/app/widgets04.py)               | Async mount of Welcome widget with button label update               |

### Events

| File                                                   | Description                                                          |
|--------------------------------------------------------|----------------------------------------------------------------------|
| [custom01.py](examples/events/custom01.py)             | Custom message event with ColorButton posting Selected messages      |
| [dictionary.py](examples/events/dictionary.py)         | Dictionary lookup app searching an API as you type *(+tcss)*         |
| [on_decorator.tcss](examples/events/on_decorator.tcss) | Centers buttons horizontally with margin spacing                     |
| [on_decorator01.py](examples/events/on_decorator01.py) | Handles multiple button actions with if/elif in single handler       |
| [on_decorator02.py](examples/events/on_decorator02.py) | Uses @on decorator to route button events to separate handlers       |
| [prevent.py](examples/events/prevent.py)               | Demonstrates prevent context manager to suppress input change events |

### Getting Started

| File                                              | Description                                            |
|---------------------------------------------------|--------------------------------------------------------|
| [console.py](examples/getting_started/console.py) | Simulates a screenshot of the Textual devtools console |

### Guide (root)

| File                                        | Description                                                   |
|---------------------------------------------|---------------------------------------------------------------|
| [dom1.py](examples/guide/dom1.py)           | Minimal empty Textual app skeleton                            |
| [dom2.py](examples/guide/dom2.py)           | App composing Header and Footer widgets                       |
| [dom3.py](examples/guide/dom3.py)           | Dialog with question text and Yes/No buttons                  |
| [dom4.py](examples/guide/dom4.py)           | Dialog with question and buttons using external CSS *(+tcss)* |
| [structure.py](examples/guide/structure.py) | Clock widget rendering current datetime with interval refresh |

### Guide: Actions

| File                                                | Description                                                                |
|-----------------------------------------------------|----------------------------------------------------------------------------|
| [actions01.py](examples/guide/actions/actions01.py) | Action setting screen background color on key press                        |
| [actions02.py](examples/guide/actions/actions02.py) | Action invoked via run_action with string syntax                           |
| [actions03.py](examples/guide/actions/actions03.py) | Actions triggered by markup click links to set background                  |
| [actions04.py](examples/guide/actions/actions04.py) | Actions with key bindings and click links for background color             |
| [actions05.py](examples/guide/actions/actions05.py) | Widget-level actions with ColorSwitcher on two Static widgets *(+tcss)*    |
| [actions06.py](examples/guide/actions/actions06.py) | Paginated app with check_action disabling next/previous bindings *(+tcss)* |
| [actions07.py](examples/guide/actions/actions07.py) | Paginated app using reactive bindings=True for auto refresh                |

### Guide: Animation

| File                                                                   | Description                                               |
|------------------------------------------------------------------------|-----------------------------------------------------------|
| [animation01.py](examples/guide/animator/animation01.py)               | Animates widget opacity from 1.0 to 0.0 over two seconds  |
| [animation01_static.py](examples/guide/animator/animation01_static.py) | Static easing keyframes showing opacity at discrete steps |

### Guide: Command Palette

| File                                                        | Description                                            |
|-------------------------------------------------------------|--------------------------------------------------------|
| [command01.py](examples/guide/command_palette/command01.py) | Adds custom Bell system command to command palette     |
| [command02.py](examples/guide/command_palette/command02.py) | Custom command provider to open Python files in viewer |

### Guide: Compound Widgets

| File                                                   | Description                                                            |
|--------------------------------------------------------|------------------------------------------------------------------------|
| [byte01.py](examples/guide/compound/byte01.py)         | Byte editor with BitSwitch, ByteInput, and ByteEditor compound widgets |
| [byte02.py](examples/guide/compound/byte02.py)         | Byte editor with BitChanged message for switch-to-input updates        |
| [byte03.py](examples/guide/compound/byte03.py)         | Byte editor with bidirectional sync between input and switches         |
| [compound01.py](examples/guide/compound/compound01.py) | InputWithLabel compound widget demonstrating compose pattern           |

### Guide: Content

| File                                                    | Description                                                   |
|---------------------------------------------------------|---------------------------------------------------------------|
| [content01.py](examples/guide/content/content01.py)     | Static widget demonstrating markup vs plain text rendering    |
| [playground.py](examples/guide/content/playground.py)   | Launches the built-in Textual markup playground app           |
| [renderables.py](examples/guide/content/renderables.py) | CodeView widget rendering Rich Syntax highlighted Python code |

### Guide: CSS

| File                                            | Description                                          |
|-------------------------------------------------|------------------------------------------------------|
| [nesting01.py](examples/guide/css/nesting01.py) | Demo app for flat non-nested CSS selectors *(+tcss)* |
| [nesting02.py](examples/guide/css/nesting02.py) | Demo app for nested CSS selectors *(+tcss)*          |

### Guide: Input

| File                                              | Description                                                           |
|---------------------------------------------------|-----------------------------------------------------------------------|
| [binding01.py](examples/guide/input/binding01.py) | Key bindings to add colored bars via actions *(+tcss)*                |
| [key01.py](examples/guide/input/key01.py)         | Displays key events in a RichLog widget                               |
| [key02.py](examples/guide/input/key02.py)         | Key events logger with space key handler ringing bell                 |
| [key03.py](examples/guide/input/key03.py)         | Four KeyLogger widgets in a grid showing focused key events *(+tcss)* |
| [mouse01.py](examples/guide/input/mouse01.py)     | Tracks mouse movement and moves a ball widget to cursor *(+tcss)*     |

### Guide: Layout

| File                                                                                       | Description                                                               |
|--------------------------------------------------------------------------------------------|---------------------------------------------------------------------------|
| [combining_layouts.py](examples/guide/layout/combining_layouts.py)                         | Combines vertical scroll, horizontal, and grid layouts together *(+tcss)* |
| [dock_layout1_sidebar.py](examples/guide/layout/dock_layout1_sidebar.py)                   | Dock layout with a left-docked sidebar *(+tcss)*                          |
| [dock_layout2_sidebar.py](examples/guide/layout/dock_layout2_sidebar.py)                   | Dock layout with two left-docked sidebars *(+tcss)*                       |
| [dock_layout3_sidebar_header.py](examples/guide/layout/dock_layout3_sidebar_header.py)     | Dock layout with Header widget and left sidebar *(+tcss)*                 |
| [grid_layout1.py](examples/guide/layout/grid_layout1.py)                                   | Basic 3x2 grid layout with six static widgets *(+tcss)*                   |
| [grid_layout2.py](examples/guide/layout/grid_layout2.py)                                   | Grid layout with 3 columns and auto-flowing rows *(+tcss)*                |
| [grid_layout3_row_col_adjust.py](examples/guide/layout/grid_layout3_row_col_adjust.py)     | Grid layout with custom column widths using fr units *(+tcss)*            |
| [grid_layout4_row_col_adjust.py](examples/guide/layout/grid_layout4_row_col_adjust.py)     | Grid layout with custom column widths and row heights *(+tcss)*           |
| [grid_layout5_col_span.py](examples/guide/layout/grid_layout5_col_span.py)                 | Grid layout demonstrating column-span on a cell *(+tcss)*                 |
| [grid_layout6_row_span.py](examples/guide/layout/grid_layout6_row_span.py)                 | Grid layout demonstrating combined column and row spanning *(+tcss)*      |
| [grid_layout7_gutter.py](examples/guide/layout/grid_layout7_gutter.py)                     | Grid layout demonstrating gutter spacing between cells *(+tcss)*          |
| [grid_layout_auto.py](examples/guide/layout/grid_layout_auto.py)                           | Grid layout with auto-width first column *(+tcss)*                        |
| [horizontal_layout.py](examples/guide/layout/horizontal_layout.py)                         | Basic horizontal layout with three equal-width boxes *(+tcss)*            |
| [horizontal_layout_overflow.py](examples/guide/layout/horizontal_layout_overflow.py)       | Horizontal layout with overflow scrolling enabled *(+tcss)*               |
| [layers.py](examples/guide/layout/layers.py)                                               | Demonstrates overlapping widgets on different layers *(+tcss)*            |
| [utility_containers.py](examples/guide/layout/utility_containers.py)                       | Horizontal and Vertical containers composing a 2x2 layout *(+tcss)*       |
| [utility_containers_using_with.py](examples/guide/layout/utility_containers_using_with.py) | Same utility container layout using context manager with syntax           |
| [vertical_layout.py](examples/guide/layout/vertical_layout.py)                             | Basic vertical layout with three equal-height boxes *(+tcss)*             |
| [vertical_layout_scrolled.py](examples/guide/layout/vertical_layout_scrolled.py)           | Vertical layout with fixed-height boxes causing scroll *(+tcss)*          |

### Guide: Reactivity

| File                                                             | Description                                                                 |
|------------------------------------------------------------------|-----------------------------------------------------------------------------|
| [computed01.py](examples/guide/reactivity/computed01.py)         | Computed reactive color from RGB input fields *(+tcss)*                     |
| [dynamic_watch.py](examples/guide/reactivity/dynamic_watch.py)   | Dynamically watches a Counter reactive to update ProgressBar                |
| [recompose01.py](examples/guide/reactivity/recompose01.py)       | Clock app using watch_time to update Digits display                         |
| [recompose02.py](examples/guide/reactivity/recompose02.py)       | Clock app using recompose=True to rebuild on time change                    |
| [refresh01.py](examples/guide/reactivity/refresh01.py)           | Reactive greeting widget refreshing render on name change *(+tcss)*         |
| [refresh02.py](examples/guide/reactivity/refresh02.py)           | Reactive with layout=True triggering layout refresh on change *(+tcss)*     |
| [refresh03.py](examples/guide/reactivity/refresh03.py)           | Reactive with recompose=True rebuilding widget children on change *(+tcss)* |
| [set_reactive01.py](examples/guide/reactivity/set_reactive01.py) | Greeter widget setting reactives directly in __init__                       |
| [set_reactive02.py](examples/guide/reactivity/set_reactive02.py) | Greeter widget using set_reactive to avoid triggering watchers              |
| [set_reactive03.py](examples/guide/reactivity/set_reactive03.py) | MultiGreet using mutate_reactive with recompose for dynamic list            |
| [validate01.py](examples/guide/reactivity/validate01.py)         | Validates reactive count value clamped between 0 and 10 *(+tcss)*           |
| [watch01.py](examples/guide/reactivity/watch01.py)               | Watch method showing old and new color values side by side *(+tcss)*        |
| [world_clock01.py](examples/guide/reactivity/world_clock01.py)   | World clock manually updating child clocks via watch_time *(+tcss)*         |
| [world_clock02.py](examples/guide/reactivity/world_clock02.py)   | World clock using data_bind to sync time reactives                          |
| [world_clock03.py](examples/guide/reactivity/world_clock03.py)   | World clock using data_bind with keyword argument mapping                   |

### Guide: Screens

| File                                                    | Description                                                       |
|---------------------------------------------------------|-------------------------------------------------------------------|
| [modal01.py](examples/guide/screens/modal01.py)         | Modal quit dialog using Screen pushed on key press *(+tcss)*      |
| [modal02.py](examples/guide/screens/modal02.py)         | Modal quit dialog using ModalScreen base class                    |
| [modal03.py](examples/guide/screens/modal03.py)         | Modal dialog returning bool result via dismiss callback           |
| [modes01.py](examples/guide/screens/modes01.py)         | App with switchable Dashboard, Settings, and Help screen modes    |
| [questions01.py](examples/guide/screens/questions01.py) | Question screen using push_screen_wait for async result *(+tcss)* |
| [screen01.py](examples/guide/screens/screen01.py)       | BSOD screen pushed via SCREENS dict and key binding *(+tcss)*     |
| [screen02.py](examples/guide/screens/screen02.py)       | BSOD screen installed at runtime via install_screen *(+tcss)*     |

### Guide: Styles

| File                                                     | Description                                                  |
|----------------------------------------------------------|--------------------------------------------------------------|
| [border01.py](examples/guide/styles/border01.py)         | Demonstrates setting heavy yellow border on a widget         |
| [border_title.py](examples/guide/styles/border_title.py) | Widget with border title and subtitle text                   |
| [box_sizing01.py](examples/guide/styles/box_sizing01.py) | Compares border-box vs content-box sizing behavior           |
| [colors.py](examples/guide/styles/colors.py)             | Sets background and border on a Static widget via styles API |
| [colors01.py](examples/guide/styles/colors01.py)         | Demonstrates hex, HSL, and Color object background colors    |
| [colors02.py](examples/guide/styles/colors02.py)         | Displays ten widgets with increasing alpha transparency      |
| [dimensions01.py](examples/guide/styles/dimensions01.py) | Sets explicit pixel width and height on a widget             |
| [dimensions02.py](examples/guide/styles/dimensions02.py) | Widget with fixed width and auto height                      |
| [dimensions03.py](examples/guide/styles/dimensions03.py) | Widget sized with percentage width and height                |
| [dimensions04.py](examples/guide/styles/dimensions04.py) | Two widgets split using fractional height units (2fr/1fr)    |
| [margin01.py](examples/guide/styles/margin01.py)         | Two widgets demonstrating margin spacing between borders     |
| [outline01.py](examples/guide/styles/outline01.py)       | Widget with heavy yellow outline style                       |
| [padding01.py](examples/guide/styles/padding01.py)       | Widget with uniform padding of 2 units                       |
| [padding02.py](examples/guide/styles/padding02.py)       | Widget with asymmetric vertical and horizontal padding       |
| [screen.py](examples/guide/styles/screen.py)             | Sets background and border styles directly on screen         |
| [widget.py](examples/guide/styles/widget.py)             | Sets background and border on a Static widget                |

### Guide: Testing

| File                                              | Description                                                     |
|---------------------------------------------------|-----------------------------------------------------------------|
| [rgb.py](examples/guide/testing/rgb.py)           | RGB color switcher app with buttons and key bindings            |
| [test_rgb.py](examples/guide/testing/test_rgb.py) | Async tests for RGB app verifying key presses and button clicks |

### Guide: Widgets

| File                                                  | Description                                                          |
|-------------------------------------------------------|----------------------------------------------------------------------|
| [checker01.py](examples/guide/widgets/checker01.py)   | Checkerboard widget using render_line with Strip segments            |
| [checker02.py](examples/guide/widgets/checker02.py)   | Checkerboard using component classes for themeable square colors     |
| [checker03.py](examples/guide/widgets/checker03.py)   | Scrollable checkerboard using ScrollView with virtual size           |
| [checker04.py](examples/guide/widgets/checker04.py)   | Scrollable checkerboard with mouse-tracking cursor highlight         |
| [counter.tcss](examples/guide/widgets/counter.tcss)   | Counter focus styles with accent outline and bold text               |
| [counter01.py](examples/guide/widgets/counter01.py)   | Focusable counter widget displaying reactive count value             |
| [counter02.py](examples/guide/widgets/counter02.py)   | Counter widget with key bindings to increment and decrement          |
| [fizzbuzz01.py](examples/guide/widgets/fizzbuzz01.py) | FizzBuzz results displayed in a Rich Table widget *(+tcss)*          |
| [fizzbuzz02.py](examples/guide/widgets/fizzbuzz02.py) | FizzBuzz table with custom get_content_width override *(+tcss)*      |
| [hello01.py](examples/guide/widgets/hello01.py)       | Minimal custom Hello widget with render method *(+tcss)*             |
| [hello02.py](examples/guide/widgets/hello02.py)       | Hello widget styled with external TCSS file *(+tcss)*                |
| [hello03.py](examples/guide/widgets/hello03.py)       | Cycling multilingual greeting on click using Static.update *(+tcss)* |
| [hello04.py](examples/guide/widgets/hello04.py)       | Hello widget with DEFAULT_CSS defining inline styles *(+tcss)*       |
| [hello05.py](examples/guide/widgets/hello05.py)       | Clickable greeting cycling via action link in markup *(+tcss)*       |
| [hello06.py](examples/guide/widgets/hello06.py)       | Hello widget with BORDER_TITLE and border_subtitle *(+tcss)*         |
| [loading01.py](examples/guide/widgets/loading01.py)   | DataTable grid with async loading indicator using workers            |
| [tooltip01.py](examples/guide/widgets/tooltip01.py)   | Button with tooltip text displayed on hover                          |
| [tooltip02.py](examples/guide/widgets/tooltip02.py)   | Button with custom-styled tooltip using CSS                          |

### Guide: Workers

| File                                                | Description                                                |
|-----------------------------------------------------|------------------------------------------------------------|
| [weather.tcss](examples/guide/workers/weather.tcss) | Docked input and centered weather display container styles |
| [weather01.py](examples/guide/workers/weather01.py) | Weather app fetching API data with async without workers   |
| [weather02.py](examples/guide/workers/weather02.py) | Weather app using run_worker with exclusive flag           |
| [weather03.py](examples/guide/workers/weather03.py) | Weather app using @work decorator with exclusive=True      |
| [weather04.py](examples/guide/workers/weather04.py) | Weather worker with Worker.StateChanged event logging      |
| [weather05.py](examples/guide/workers/weather05.py) | Weather app using threaded worker with get_current_worker  |

### How-To

| File                                                   | Description                                                             |
|--------------------------------------------------------|-------------------------------------------------------------------------|
| [center01.py](examples/how-to/center01.py)             | Center a Static widget on screen using align                            |
| [center02.py](examples/how-to/center02.py)             | Center a Static with blue background and white border                   |
| [center03.py](examples/how-to/center03.py)             | Center a Static with auto width and border                              |
| [center04.py](examples/how-to/center04.py)             | Center a fixed-width Static displaying a quote                          |
| [center05.py](examples/how-to/center05.py)             | Center a fixed-width Static with text-align center                      |
| [center06.py](examples/how-to/center06.py)             | Center a Static with fixed width, height, and text-align                |
| [center07.py](examples/how-to/center07.py)             | Center a Static using content-align for vertical text centering         |
| [center08.py](examples/how-to/center08.py)             | Multiple auto-width Static widgets without screen alignment             |
| [center09.py](examples/how-to/center09.py)             | Multiple auto-width Static widgets centered on screen with align        |
| [center10.py](examples/how-to/center10.py)             | Center multiple Static widgets individually using Center container      |
| [containers01.py](examples/how-to/containers01.py)     | Three Placeholder boxes in a Horizontal container                       |
| [containers02.py](examples/how-to/containers02.py)     | Three Placeholder boxes in a Vertical container                         |
| [containers03.py](examples/how-to/containers03.py)     | Horizontal container with green heavy border around boxes               |
| [containers04.py](examples/how-to/containers04.py)     | Two bordered Horizontal containers each with three boxes                |
| [containers05.py](examples/how-to/containers05.py)     | Two HorizontalGroup containers each with three boxes                    |
| [containers06.py](examples/how-to/containers06.py)     | Ten Placeholder boxes overflowing a Horizontal container                |
| [containers07.py](examples/how-to/containers07.py)     | Ten Placeholder boxes in a scrollable HorizontalScroll container        |
| [containers08.py](examples/how-to/containers08.py)     | Boxes aligned left, center, and right using Center and Right containers |
| [containers09.py](examples/how-to/containers09.py)     | Three boxes vertically centered using the Middle container              |
| [inline01.py](examples/how-to/inline01.py)             | Inline-mode clock app displaying current time with Digits widget        |
| [inline02.py](examples/how-to/inline02.py)             | Inline clock with custom inline-mode styles and green color             |
| [layout.py](examples/how-to/layout.py)                 | Tweet-column layout with header, footer, and scrollable columns         |
| [layout01.py](examples/how-to/layout01.py)             | Basic layout with Header and Footer placeholder widgets                 |
| [layout02.py](examples/how-to/layout02.py)             | Header and Footer docked to top and bottom of screen                    |
| [layout03.py](examples/how-to/layout03.py)             | Docked header, footer, and a ColumnsContainer placeholder area          |
| [layout04.py](examples/how-to/layout04.py)             | Header, footer, and an empty HorizontalScroll container                 |
| [layout05.py](examples/how-to/layout05.py)             | Tweet columns inside HorizontalScroll with unstyled Tweet placeholders  |
| [layout06.py](examples/how-to/layout06.py)             | Fully styled tweet-column layout with sized tweets and columns          |
| [render_compose.py](examples/how-to/render_compose.py) | Custom Splash widget with animated linear gradient background           |

### Styles

| File                                                                           | Description                                                                             |
|--------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------|
| [align.py](examples/styles/align.py)                                           | Demonstrates center-middle alignment of labels on screen *(+tcss)*                      |
| [align_all.py](examples/styles/align_all.py)                                   | Demonstrates all nine alignment combinations in a grid *(+tcss)*                        |
| [background.py](examples/styles/background.py)                                 | Demonstrates background color on three labeled widgets *(+tcss)*                        |
| [background_tint.py](examples/styles/background_tint.py)                       | Demonstrates background-tint at varying opacity levels *(+tcss)*                        |
| [background_transparency.py](examples/styles/background_transparency.py)       | Demonstrates background color transparency from 10% to 100% *(+tcss)*                   |
| [border.py](examples/styles/border.py)                                         | Demonstrates solid, dashed, and tall border styles *(+tcss)*                            |
| [border_all.py](examples/styles/border_all.py)                                 | Demonstrates all sixteen available border types in a grid *(+tcss)*                     |
| [border_sub_title_align_all.py](examples/styles/border_sub_title_align_all.py) | Demonstrates border title and subtitle alignment combinations *(+tcss)*                 |
| [border_subtitle_align.py](examples/styles/border_subtitle_align.py)           | Demonstrates left, center, and right border subtitle alignment *(+tcss)*                |
| [border_title_align.py](examples/styles/border_title_align.py)                 | Demonstrates left, center, and right border title alignment *(+tcss)*                   |
| [border_title_colors.py](examples/styles/border_title_colors.py)               | Demonstrates border title and subtitle color and style customization *(+tcss)*          |
| [box_sizing.py](examples/styles/box_sizing.py)                                 | Demonstrates border-box versus content-box sizing behavior *(+tcss)*                    |
| [color.py](examples/styles/color.py)                                           | Demonstrates text color using named, rgb, and hsl formats *(+tcss)*                     |
| [color_auto.py](examples/styles/color_auto.py)                                 | Demonstrates automatic text color contrast on varied backgrounds *(+tcss)*              |
| [column_span.py](examples/styles/column_span.py)                               | Demonstrates column-span in a grid layout with placeholders *(+tcss)*                   |
| [content_align.py](examples/styles/content_align.py)                           | Demonstrates content alignment with left-top, center-middle, right-bottom *(+tcss)*     |
| [content_align_all.py](examples/styles/content_align_all.py)                   | Demonstrates all nine content-align combinations in a grid *(+tcss)*                    |
| [display.py](examples/styles/display.py)                                       | Demonstrates hiding a widget using display none *(+tcss)*                               |
| [dock_all.py](examples/styles/dock_all.py)                                     | Demonstrates docking widgets to left, top, right, and bottom *(+tcss)*                  |
| [grid.py](examples/styles/grid.py)                                             | Demonstrates grid layout with row-span and column-span *(+tcss)*                        |
| [grid_columns.py](examples/styles/grid_columns.py)                             | Demonstrates grid-columns with fractional and fixed widths *(+tcss)*                    |
| [grid_gutter.py](examples/styles/grid_gutter.py)                               | Demonstrates grid-gutter spacing between grid cells *(+tcss)*                           |
| [grid_rows.py](examples/styles/grid_rows.py)                                   | Demonstrates grid-rows with fractional, fixed, and percent heights *(+tcss)*            |
| [grid_size_both.py](examples/styles/grid_size_both.py)                         | Demonstrates grid-size setting both columns and rows *(+tcss)*                          |
| [grid_size_columns.py](examples/styles/grid_size_columns.py)                   | Demonstrates grid-size setting column count only *(+tcss)*                              |
| [hatch.py](examples/styles/hatch.py)                                           | Demonstrates hatch fill patterns including cross, horizontal, and custom *(+tcss)*      |
| [height.py](examples/styles/height.py)                                         | Demonstrates setting widget height to 50 percent *(+tcss)*                              |
| [height_comparison.py](examples/styles/height_comparison.py)                   | Demonstrates height using cells, percent, w, h, vw, vh, auto, and fr units *(+tcss)*    |
| [keyline.py](examples/styles/keyline.py)                                       | Demonstrates keyline borders around grid cells *(+tcss)*                                |
| [keyline_horizontal.py](examples/styles/keyline_horizontal.py)                 | Demonstrates keyline on a horizontal container layout *(+tcss)*                         |
| [layout.py](examples/styles/layout.py)                                         | Demonstrates vertical and horizontal layout modes *(+tcss)*                             |
| [link_background.py](examples/styles/link_background.py)                       | Demonstrates link background color styling on clickable text *(+tcss)*                  |
| [link_background_hover.py](examples/styles/link_background_hover.py)           | Demonstrates link background color on hover state *(+tcss)*                             |
| [link_color.py](examples/styles/link_color.py)                                 | Demonstrates link text color styling on clickable text *(+tcss)*                        |
| [link_color_hover.py](examples/styles/link_color_hover.py)                     | Demonstrates link text color on hover state *(+tcss)*                                   |
| [link_style.py](examples/styles/link_style.py)                                 | Demonstrates link text style with bold, italic, and reverse *(+tcss)*                   |
| [link_style_hover.py](examples/styles/link_style_hover.py)                     | Demonstrates link text style on hover state *(+tcss)*                                   |
| [links.py](examples/styles/links.py)                                           | Demonstrates combined link color, background, and style customization *(+tcss)*         |
| [margin.py](examples/styles/margin.py)                                         | Demonstrates margin spacing around a label widget *(+tcss)*                             |
| [margin_all.py](examples/styles/margin_all.py)                                 | Demonstrates all margin variants including per-side margins *(+tcss)*                   |
| [max_height.py](examples/styles/max_height.py)                                 | Demonstrates max-height constraint with different units *(+tcss)*                       |
| [max_width.py](examples/styles/max_width.py)                                   | Demonstrates max-width constraint with different units *(+tcss)*                        |
| [min_height.py](examples/styles/min_height.py)                                 | Demonstrates min-height constraint with different units *(+tcss)*                       |
| [min_width.py](examples/styles/min_width.py)                                   | Demonstrates min-width constraint with different units *(+tcss)*                        |
| [offset.py](examples/styles/offset.py)                                         | Demonstrates offset positioning of widgets with x-y values *(+tcss)*                    |
| [opacity.py](examples/styles/opacity.py)                                       | Demonstrates widget opacity from 0% to 100% *(+tcss)*                                   |
| [outline.py](examples/styles/outline.py)                                       | Demonstrates outline style around a label widget *(+tcss)*                              |
| [outline_all.py](examples/styles/outline_all.py)                               | Demonstrates all available outline style types in a grid *(+tcss)*                      |
| [outline_vs_border.py](examples/styles/outline_vs_border.py)                   | Demonstrates visual difference between outline and border *(+tcss)*                     |
| [overflow.py](examples/styles/overflow.py)                                     | Demonstrates overflow scrolling versus hidden behavior *(+tcss)*                        |
| [padding.py](examples/styles/padding.py)                                       | Demonstrates padding spacing inside a label widget *(+tcss)*                            |
| [padding_all.py](examples/styles/padding_all.py)                               | Demonstrates all padding variants including per-side padding *(+tcss)*                  |
| [position.py](examples/styles/position.py)                                     | Demonstrates absolute versus relative positioning *(+tcss)*                             |
| [row_span.py](examples/styles/row_span.py)                                     | Demonstrates row-span in a grid layout with placeholders *(+tcss)*                      |
| [scrollbar_corner_color.py](examples/styles/scrollbar_corner_color.py)         | Demonstrates scrollbar corner color customization *(+tcss)*                             |
| [scrollbar_gutter.py](examples/styles/scrollbar_gutter.py)                     | Demonstrates scrollbar gutter stable reservation *(+tcss)*                              |
| [scrollbar_size.py](examples/styles/scrollbar_size.py)                         | Demonstrates custom scrollbar width and height sizing *(+tcss)*                         |
| [scrollbar_size2.py](examples/styles/scrollbar_size2.py)                       | Demonstrates scrollbar-size-vertical and scrollbar-size-horizontal separately *(+tcss)* |
| [scrollbar_visibility.py](examples/styles/scrollbar_visibility.py)             | Demonstrates visible versus hidden scrollbar visibility *(+tcss)*                       |
| [scrollbars.py](examples/styles/scrollbars.py)                                 | Demonstrates scrollbar color and background customization *(+tcss)*                     |
| [scrollbars2.py](examples/styles/scrollbars2.py)                               | Demonstrates scrollbar colors with active and hover states *(+tcss)*                    |
| [text_align.py](examples/styles/text_align.py)                                 | Demonstrates left, center, right, and justify text alignment *(+tcss)*                  |
| [text_opacity.py](examples/styles/text_opacity.py)                             | Demonstrates text opacity from 0% to 100% *(+tcss)*                                     |
| [text_overflow.py](examples/styles/text_overflow.py)                           | Demonstrates text overflow with clip, fold, and ellipsis modes *(+tcss)*                |
| [text_style.py](examples/styles/text_style.py)                                 | Demonstrates bold, italic, and reverse text styles *(+tcss)*                            |
| [text_style_all.py](examples/styles/text_style_all.py)                         | Demonstrates all text-style options including strike and underline *(+tcss)*            |
| [text_wrap.py](examples/styles/text_wrap.py)                                   | Demonstrates text wrap versus nowrap behavior *(+tcss)*                                 |
| [tint.py](examples/styles/tint.py)                                             | Demonstrates tint overlay at varying alpha levels *(+tcss)*                             |
| [visibility.py](examples/styles/visibility.py)                                 | Demonstrates hiding a widget using visibility hidden *(+tcss)*                          |
| [visibility_containers.py](examples/styles/visibility_containers.py)           | Demonstrates visibility inheritance and override in nested containers *(+tcss)*         |
| [width.py](examples/styles/width.py)                                           | Demonstrates setting widget width to 50 percent *(+tcss)*                               |
| [width_comparison.py](examples/styles/width_comparison.py)                     | Demonstrates width using cells, percent, w, h, vw, vh, auto, and fr units *(+tcss)*     |

### Themes

| File                                                         | Description                                                          |
|--------------------------------------------------------------|----------------------------------------------------------------------|
| [colored_text.py](examples/themes/colored_text.py)           | Displays theme semantic text colors for six color roles              |
| [muted_backgrounds.py](examples/themes/muted_backgrounds.py) | Displays text colors on muted background variants for theme colors   |
| [todo_app.py](examples/themes/todo_app.py)                   | Todo list app demonstrating theme cycling with styled task selection |

### Tutorial

| File                                               | Description                                                                         |
|----------------------------------------------------|-------------------------------------------------------------------------------------|
| [stopwatch.py](examples/tutorial/stopwatch.py)     | Complete stopwatch app with start, stop, reset, and add/remove timers *(+tcss)*     |
| [stopwatch01.py](examples/tutorial/stopwatch01.py) | Minimal stopwatch app skeleton with Header, Footer, and dark mode toggle            |
| [stopwatch02.py](examples/tutorial/stopwatch02.py) | Stopwatch app composing TimeDisplay, buttons, and three stopwatch widgets *(+tcss)* |
| [stopwatch03.py](examples/tutorial/stopwatch03.py) | Stopwatch app with external TCSS stylesheet for button and layout styling *(+tcss)* |
| [stopwatch04.py](examples/tutorial/stopwatch04.py) | Stopwatch with button press handlers toggling started CSS class *(+tcss)*           |
| [stopwatch05.py](examples/tutorial/stopwatch05.py) | Stopwatch with reactive time display updating at 60fps                              |
| [stopwatch06.py](examples/tutorial/stopwatch06.py) | Stopwatch with start, stop, and reset controlling a pausable timer                  |

### Widgets

| File                                                                            | Description                                                                     |
|---------------------------------------------------------------------------------|---------------------------------------------------------------------------------|
| [button.py](examples/widgets/button.py)                                         | Demonstrates standard, disabled, and flat button variants *(+tcss)*             |
| [checkbox.py](examples/widgets/checkbox.py)                                     | Displays a list of checkboxes with various labels *(+tcss)*                     |
| [clock.py](examples/widgets/clock.py)                                           | Displays a real-time updating digital clock using Digits                        |
| [collapsible.py](examples/widgets/collapsible.py)                               | Demonstrates collapsible containers with expand and collapse bindings           |
| [collapsible_custom_symbol.py](examples/widgets/collapsible_custom_symbol.py)   | Shows collapsible widgets with custom expand and collapse symbols               |
| [collapsible_nested.py](examples/widgets/collapsible_nested.py)                 | Demonstrates nested collapsible containers                                      |
| [content_switcher.py](examples/widgets/content_switcher.py)                     | Switches between a DataTable and Markdown view via buttons *(+tcss)*            |
| [data_table.py](examples/widgets/data_table.py)                                 | Displays a basic DataTable with swimmer Olympic results                         |
| [data_table_cursors.py](examples/widgets/data_table_cursors.py)                 | DataTable with cycling cursor types and zebra stripes                           |
| [data_table_fixed.py](examples/widgets/data_table_fixed.py)                     | DataTable with fixed rows, fixed columns, and row cursor                        |
| [data_table_labels.py](examples/widgets/data_table_labels.py)                   | DataTable with custom styled Rich Text row labels                               |
| [data_table_renderables.py](examples/widgets/data_table_renderables.py)         | DataTable with styled and right-justified Rich Text cell content                |
| [data_table_sort.py](examples/widgets/data_table_sort.py)                       | DataTable with multiple sorting strategies using custom key functions           |
| [digits.py](examples/widgets/digits.py)                                         | Displays the value of pi using the Digits widget                                |
| [directory_tree.py](examples/widgets/directory_tree.py)                         | Shows a directory tree of the current working directory                         |
| [directory_tree_filtered.py](examples/widgets/directory_tree_filtered.py)       | Filtered directory tree that hides dotfiles                                     |
| [footer.py](examples/widgets/footer.py)                                         | Demonstrates a Footer widget with key bindings                                  |
| [header.py](examples/widgets/header.py)                                         | Displays a basic Header widget                                                  |
| [header_app_title.py](examples/widgets/header_app_title.py)                     | Header widget with custom application title and sub-title                       |
| [horizontal_rules.py](examples/widgets/horizontal_rules.py)                     | Shows horizontal rules in various line styles *(+tcss)*                         |
| [input.py](examples/widgets/input.py)                                           | Displays two text input fields with placeholder text                            |
| [input_types.py](examples/widgets/input_types.py)                               | Input widgets restricted to integer and number types                            |
| [input_validation.py](examples/widgets/input_validation.py)                     | Input with multiple validators including number range and palindrome check      |
| [java_highlights.scm](examples/widgets/java_highlights.scm)                     | Defines tree-sitter syntax highlighting queries for Java language               |
| [label.py](examples/widgets/label.py)                                           | Displays a simple Label widget with hello world text                            |
| [link.py](examples/widgets/link.py)                                             | Displays a clickable Link widget pointing to textualize.io                      |
| [list_view.py](examples/widgets/list_view.py)                                   | Shows a ListView with three labeled list items *(+tcss)*                        |
| [loading_indicator.py](examples/widgets/loading_indicator.py)                   | Displays a loading indicator animation widget                                   |
| [log.py](examples/widgets/log.py)                                               | Writes repeated text lines to a Log widget                                      |
| [markdown.py](examples/widgets/markdown.py)                                     | Renders Markdown with quotes, tables, and code blocks                           |
| [markdown_viewer.py](examples/widgets/markdown_viewer.py)                       | MarkdownViewer with table of contents and syntax-highlighted code blocks        |
| [masked_input.py](examples/widgets/masked_input.py)                             | Masked input field for credit card number entry                                 |
| [option_list.tcss](examples/widgets/option_list.tcss)                           | Centers screen and sets OptionList width and height                             |
| [option_list_options.py](examples/widgets/option_list_options.py)               | OptionList using Option objects with IDs and separators                         |
| [option_list_strings.py](examples/widgets/option_list_strings.py)               | OptionList populated from a simple list of strings                              |
| [option_list_tables.py](examples/widgets/option_list_tables.py)                 | OptionList displaying Rich Table renderables for each colony                    |
| [placeholder.py](examples/widgets/placeholder.py)                               | Demonstrates Placeholder widgets in various grid layouts *(+tcss)*              |
| [pretty.py](examples/widgets/pretty.py)                                         | Renders a nested Python dictionary using the Pretty widget                      |
| [progress_bar.py](examples/widgets/progress_bar.py)                             | Funding tracker app with donation input advancing a progress bar *(+tcss)*      |
| [progress_bar_gradient.py](examples/widgets/progress_bar_gradient.py)           | Progress bar with a custom rainbow color gradient                               |
| [progress_bar_isolated.py](examples/widgets/progress_bar_isolated.py)           | Indeterminate progress bar started via key binding                              |
| [progress_bar_isolated_.py](examples/widgets/progress_bar_isolated_.py)         | Progress bar with MockClock for frozen time testing                             |
| [progress_bar_styled.py](examples/widgets/progress_bar_styled.py)               | Progress bar with custom TCSS styling applied *(+tcss)*                         |
| [progress_bar_styled_.py](examples/widgets/progress_bar_styled_.py)             | Styled progress bar with MockClock for time-controlled testing                  |
| [radio_button.py](examples/widgets/radio_button.py)                             | RadioButton choices inside a RadioSet with pre-selected value *(+tcss)*         |
| [radio_set.py](examples/widgets/radio_set.py)                                   | Two side-by-side RadioSets built from buttons and strings *(+tcss)*             |
| [radio_set_changed.py](examples/widgets/radio_set_changed.py)                   | RadioSet demonstrating the Changed event with label and index display *(+tcss)* |
| [rich_log.py](examples/widgets/rich_log.py)                                     | RichLog displaying syntax-highlighted code, tables, and key events              |
| [select.tcss](examples/widgets/select.tcss)                                     | Centers screen and styles Select widget width and margin                        |
| [select_from_values_widget.py](examples/widgets/select_from_values_widget.py)   | Select dropdown created from a list of string values                            |
| [select_widget.py](examples/widgets/select_widget.py)                           | Select dropdown built from label-value tuple pairs                              |
| [select_widget_no_blank.py](examples/widgets/select_widget_no_blank.py)         | Select widget with allow_blank disabled and swappable options                   |
| [selection_list.tcss](examples/widgets/selection_list.tcss)                     | Centers screen and styles SelectionList with border and padding                 |
| [selection_list_selected.py](examples/widgets/selection_list_selected.py)       | SelectionList showing selected items in a Pretty widget sidebar *(+tcss)*       |
| [selection_list_selections.py](examples/widgets/selection_list_selections.py)   | SelectionList using Selection objects with pre-selected items                   |
| [selection_list_tuples.py](examples/widgets/selection_list_tuples.py)           | SelectionList built from simple tuples with default selections                  |
| [sparkline.py](examples/widgets/sparkline.py)                                   | Sparklines with max, mean, and min summary functions *(+tcss)*                  |
| [sparkline_basic.py](examples/widgets/sparkline_basic.py)                       | Basic sparkline widget displaying a small data series *(+tcss)*                 |
| [sparkline_colors.py](examples/widgets/sparkline_colors.py)                     | Multiple sparklines rendered from sine wave data with custom colors *(+tcss)*   |
| [static.py](examples/widgets/static.py)                                         | Displays a simple Static widget with hello world text                           |
| [switch.py](examples/widgets/switch.py)                                         | Demonstrates switch widgets in off, on, focused, and custom states *(+tcss)*    |
| [tabbed_content.py](examples/widgets/tabbed_content.py)                         | TabbedContent with nested tabs and key bindings to switch panes                 |
| [tabbed_content_label_color.py](examples/widgets/tabbed_content_label_color.py) | TabbedContent with custom colored tab labels via CSS                            |
| [tabs.py](examples/widgets/tabs.py)                                             | Tabs widget with add, remove, and clear tab actions                             |
| [text_area_custom_language.py](examples/widgets/text_area_custom_language.py)   | TextArea with custom Java language and tree-sitter highlighting                 |
| [text_area_custom_theme.py](examples/widgets/text_area_custom_theme.py)         | TextArea with a custom color theme for syntax highlighting                      |
| [text_area_example.py](examples/widgets/text_area_example.py)                   | Basic TextArea code editor with Python syntax highlighting                      |
| [text_area_extended.py](examples/widgets/text_area_extended.py)                 | Extended TextArea that auto-closes parentheses on key press                     |
| [text_area_selection.py](examples/widgets/text_area_selection.py)               | TextArea with a programmatic initial text selection range                       |
| [toast.py](examples/widgets/toast.py)                                           | Displays multiple toast notifications with different severity levels            |
| [tree.py](examples/widgets/tree.py)                                             | Builds a simple Tree widget with Dune character leaf nodes                      |
| [vertical_rules.py](examples/widgets/vertical_rules.py)                         | Shows vertical rules in various line styles *(+tcss)*                           |

---

## Reference

Cross-cutting reference material. See [reference/index.md](reference/index.md).
