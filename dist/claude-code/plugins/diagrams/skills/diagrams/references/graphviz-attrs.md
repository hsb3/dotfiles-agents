# Graphviz Attributes Reference

Professional diagram formatting through custom Graphviz dot attributes. Pass these via `graph_attr`, `node_attr`, and `edge_attr` parameters.

Full reference: https://www.graphviz.org/doc/info/attrs.html

## Attribute Scopes

```python
with Diagram(
    "Name",
    show=False,
    graph_attr={...},  # Diagram-level attributes
    node_attr={...},   # Default node attributes
    edge_attr={...},   # Default edge attributes
):
    ...
```

For clusters:
```python
with Cluster("Name", graph_attr={...}):
    ...
```

## Professional Layout Presets

### Clean Corporate Style
```python
graph_attr = {
    "fontsize": "16",
    "fontname": "Helvetica",
    "bgcolor": "white",
    "pad": "0.5",
    "nodesep": "0.8",
    "ranksep": "1.0",
    "splines": "ortho",
}

node_attr = {
    "fontsize": "12",
    "fontname": "Helvetica",
}

edge_attr = {
    "fontsize": "10",
    "fontname": "Helvetica",
}
```

### Presentation Style (Large, Clear)
```python
graph_attr = {
    "fontsize": "24",
    "fontname": "Arial",
    "bgcolor": "transparent",
    "pad": "1.0",
    "nodesep": "1.2",
    "ranksep": "1.5",
    "dpi": "150",
}

node_attr = {
    "fontsize": "18",
    "fontname": "Arial",
    "penwidth": "2.0",
}

edge_attr = {
    "fontsize": "14",
    "fontname": "Arial",
    "penwidth": "2.0",
    "arrowsize": "1.5",
}
```

### Technical Documentation Style
```python
graph_attr = {
    "fontsize": "14",
    "fontname": "Courier",
    "bgcolor": "#fafafa",
    "pad": "0.3",
    "nodesep": "0.5",
    "ranksep": "0.75",
    "splines": "spline",
}
```

### Compact Style (Many Nodes)
```python
graph_attr = {
    "fontsize": "10",
    "nodesep": "0.3",
    "ranksep": "0.4",
    "concentrate": "true",
    "compound": "true",
}

node_attr = {
    "fontsize": "9",
    "width": "0.5",
    "height": "0.5",
}
```

## Graph Attributes (Detailed)

### Layout Control

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `rankdir` | TB/BT/LR/RL | TB | Direction of layout |
| `nodesep` | double | 0.25 | Min space between nodes in same rank (inches) |
| `ranksep` | double | 0.5 | Min space between ranks (inches) |
| `splines` | string | - | Edge routing: `ortho`, `spline`, `line`, `curved`, `polyline` |
| `overlap` | bool/string | true | Node overlap removal: `false`, `scale`, `prism` |
| `concentrate` | bool | false | Merge multi-edges |
| `compound` | bool | false | Allow edges between clusters |
| `newrank` | bool | false | Use single global ranking (ignores clusters) |
| `ordering` | string | - | Node ordering: `out`, `in` |

### Appearance

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `bgcolor` | color | white | Background color (`transparent` for no bg) |
| `fontsize` | double | 14 | Title/label font size (points) |
| `fontname` | string | Times-Roman | Font family |
| `fontcolor` | color | black | Title/label color |
| `pad` | double | 0.0555 | Padding around graph (inches) |
| `margin` | double | - | Page margin (inches) |
| `dpi` | double | 96 | Resolution for bitmap output |
| `size` | double,double | - | Maximum size (width,height in inches) |
| `ratio` | string/double | - | Aspect ratio: `fill`, `compress`, `auto`, or number |

### Cluster-Specific

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `style` | string | - | `filled`, `rounded`, `dashed`, `bold` |
| `color` | color | black | Border color |
| `fillcolor` | color | lightgrey | Fill color (requires `style=filled`) |
| `penwidth` | double | 1.0 | Border thickness |
| `pencolor` | color | black | Border color (alternative to `color`) |
| `labeljust` | string | c | Label justification: `l`, `r`, `c` |
| `labelloc` | string | t | Label location: `t` (top), `b` (bottom) |

## Node Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `shape` | string | ellipse | See shapes reference |
| `style` | string | - | `filled`, `rounded`, `dashed`, `bold`, `invis` |
| `color` | color | black | Border color |
| `fillcolor` | color | lightgrey | Fill color |
| `fontsize` | double | 14 | Label font size |
| `fontname` | string | Times-Roman | Label font |
| `fontcolor` | color | black | Label color |
| `width` | double | 0.75 | Minimum width (inches) |
| `height` | double | 0.5 | Minimum height (inches) |
| `fixedsize` | bool | false | Use exact width/height |
| `penwidth` | double | 1.0 | Border thickness |
| `margin` | double | - | Space around label |

## Edge Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `style` | string | solid | `solid`, `dashed`, `dotted`, `bold`, `invis` |
| `color` | color | black | Line color |
| `penwidth` | double | 1.0 | Line thickness |
| `arrowhead` | string | normal | Head arrow style |
| `arrowtail` | string | normal | Tail arrow style |
| `arrowsize` | double | 1.0 | Arrow scale factor |
| `dir` | string | forward | Arrow direction: `forward`, `back`, `both`, `none` |
| `label` | string | - | Edge label |
| `fontsize` | double | 14 | Label font size |
| `fontname` | string | Times-Roman | Label font |
| `fontcolor` | color | black | Label color |
| `headlabel` | string | - | Label at head |
| `taillabel` | string | - | Label at tail |
| `minlen` | int | 1 | Minimum edge length (ranks) |
| `weight` | int | 1 | Edge importance for layout |
| `constraint` | bool | true | Use edge in ranking |
| `decorate` | bool | false | Connect label to edge with line |

### Edge Routing (splines values)

| Value | Description |
|-------|-------------|
| `ortho` | Right-angle edges only |
| `spline` | Curved edges avoiding nodes |
| `line` | Straight lines |
| `polyline` | Straight line segments |
| `curved` | Single curved arc |
| `none` / `""` | No edges drawn |

### Arrow Types

Common values: `normal`, `inv`, `dot`, `odot`, `none`, `tee`, `empty`, `diamond`, `box`, `vee`, `crow`

Modifiers: `o` (open), `l` (left half), `r` (right half)

Examples: `obox`, `ldiamond`, `rvee`

## Color Specification

```python
# Named colors (X11)
color="red"
color="lightblue"

# Hex RGB
color="#FF5733"
color="#FF573380"  # With alpha

# HSV (hue, saturation, value)
color="0.5 0.8 0.9"

# Color schemes
graph_attr={"colorscheme": "blues9"}
node_attr={"color": "5"}  # 5th color in scheme
```

## Common Fixes via Attributes

| Problem | Solution |
|---------|----------|
| Nodes overlap | `graph_attr={"overlap": "false"}` |
| Edges overlap nodes | `graph_attr={"splines": "ortho"}` |
| Labels overlap | `graph_attr={"forcelabels": "true"}` |
| Too cramped | Increase `nodesep` and `ranksep` |
| Edges cross clusters | Set `compound=true`, use `lhead`/`ltail` |
| Wrong node order | Use `ordering="out"` or invisible edges with `constraint=false` |
| Title at bottom | `graph_attr={"labelloc": "b"}` |
| Transparent background | `graph_attr={"bgcolor": "transparent"}` |
| Higher resolution | `graph_attr={"dpi": "300"}` |
| Cluster labels overlap | Increase cluster `margin` |

## Professional Formatting Examples

### Financial Dashboard Style
```python
graph_attr = {
    "bgcolor": "#1a1a2e",
    "fontcolor": "white",
    "fontname": "Arial",
    "fontsize": "16",
    "pad": "0.5",
    "nodesep": "0.8",
    "ranksep": "1.0",
}

node_attr = {
    "style": "filled",
    "fillcolor": "#16213e",
    "fontcolor": "white",
    "color": "#0f3460",
    "penwidth": "2",
}

edge_attr = {
    "color": "#e94560",
    "penwidth": "1.5",
    "fontcolor": "#888888",
}
```

### Healthcare/Clinical Style
```python
graph_attr = {
    "bgcolor": "white",
    "fontname": "Helvetica",
    "fontsize": "14",
    "pad": "0.5",
    "nodesep": "0.7",
    "ranksep": "0.9",
    "splines": "ortho",
}

node_attr = {
    "style": "filled,rounded",
    "fillcolor": "#e3f2fd",
    "color": "#1976d2",
    "fontname": "Helvetica",
    "penwidth": "1.5",
}

edge_attr = {
    "color": "#757575",
    "fontcolor": "#424242",
    "penwidth": "1.2",
}
```

### AWS-Like Style
```python
graph_attr = {
    "bgcolor": "#232f3e",
    "fontcolor": "white",
    "pad": "0.75",
    "nodesep": "1.0",
    "ranksep": "1.2",
}

# Cluster styling for service groups
cluster_attr = {
    "style": "rounded,filled",
    "fillcolor": "#37475a",
    "color": "#ff9900",
    "fontcolor": "white",
    "penwidth": "2",
}
```

## Tips for Professional Output

1. **Consistent fonts**: Use the same `fontname` across graph, nodes, and edges
2. **Adequate spacing**: Increase `nodesep`/`ranksep` for clarity (0.8-1.2 typical)
3. **Clear hierarchy**: Use `splines=ortho` for structured diagrams
4. **High resolution**: Set `dpi=150` or higher for presentations
5. **Transparent bg**: Use `bgcolor=transparent` for embedding in documents
6. **Color harmony**: Use color schemes (`colorscheme`) for consistent palettes
7. **Readable labels**: Minimum `fontsize=10` for any text
8. **Clean edges**: Use `penwidth=1.5-2.0` for visibility
9. **Balanced arrows**: `arrowsize=1.0-1.5` for proportional arrows
10. **Padding**: Add `pad=0.5` to prevent clipping at edges
