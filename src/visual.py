from html import escape


NODE_HEIGHT = 32
CHAR_WIDTH = 8
PADDING = 12
GAP_X = 24
GAP_Y = 56
MARGIN = 20
LOOP = 48
HOP_WIDTH = 8
BEND = GAP_Y // 2
FONT_SIZE = 13


def mermaid(graph):
    ids = {name: f"n{number}" for number, name in enumerate(graph, 1)}
    lines = ["graph TD"]
    for name, node in ids.items():
        lines.append(f'    {node}["{name}"]')
    for name, dependencies in graph.items():
        for dependency in dependencies:
            lines.append(f"    {ids[name]} --> {ids[dependency]}")
    return "\n".join(lines)


def ascii_tree(graph, root):
    return "\n".join([root] + tree_lines(graph, root, "", [root], {root}))


def tree_lines(graph, node, prefix, path, shown):
    lines = []
    children = graph[node]
    last_index = len(children) - 1
    for index, child in enumerate(children):
        last = index == last_index
        line = prefix + ("└── " if last else "├── ") + child
        if child in path:
            lines.append(line + " (цикл)")
        elif child in shown:
            lines.append(line + " (*)")
        else:
            shown.add(child)
            lines.append(line)
            lines += tree_lines(
                graph, child, prefix + ("    " if last else "│   "),
                path + [child], shown,
            )
    return lines


def ranks(graph, root):
    seen = set()
    finished = []
    back = set()

    def visit(node, path):
        seen.add(node)
        for child in graph[node]:
            if child in path:
                back.add((node, child))
            elif child not in seen:
                visit(child, path | {child})
        finished.append(node)

    visit(root, {root})
    depth = dict.fromkeys(graph, 0)
    for node in reversed(finished):
        for child in graph[node]:
            if (node, child) not in back:
                depth[child] = max(depth[child], depth[node] + 1)
    return depth, back


def routes(graph, root):
    depth, back = ranks(graph, root)
    rows = [[] for _ in range(max(depth.values()) + 1)]
    for node in graph:
        rows[depth[node]].append(node)
    edges = []
    for node, dependencies in graph.items():
        for child in dependencies:
            hops = []
            if (node, child) not in back:
                for level in range(depth[node] + 1, depth[child]):
                    hops.append((node, child, level))
                    rows[level].append(hops[-1])
            edges.append([node] + hops + [child])
    order_rows(rows, edges)
    return rows, edges


def order_rows(rows, edges):
    parents = {}
    for route in edges:
        for upper, lower in zip(route, route[1:]):
            parents.setdefault(lower, []).append(upper)
    for upper_row, row in zip(rows, rows[1:]):
        position = {item: index for index, item in enumerate(upper_row)}
        keys = {
            item: mean_position(parents.get(item, []), position)
            for item in row
        }
        row.sort(key=keys.get)


def mean_position(items, position):
    indexes = [position[item] for item in items if item in position]
    return sum(indexes) / len(indexes) if indexes else 0


def node_width(item):
    if isinstance(item, tuple):
        return HOP_WIDTH
    return len(item) * CHAR_WIDTH + 2 * PADDING


def row_width(row):
    return sum(node_width(item) for item in row) + GAP_X * (len(row) - 1)


def layout(rows):
    total = max(row_width(row) for row in rows)
    boxes = {}
    for level, row in enumerate(rows):
        x = MARGIN + (total - row_width(row)) // 2
        y = MARGIN + level * (NODE_HEIGHT + GAP_Y)
        for item in row:
            boxes[item] = (x, y, node_width(item))
            x += node_width(item) + GAP_X
    width = total + 2 * MARGIN + LOOP
    height = 2 * MARGIN + len(rows) * (NODE_HEIGHT + GAP_Y) - GAP_Y
    return boxes, width, height


def down_path(route, boxes):
    left, top, width = boxes[route[0]]
    x, y = left + width // 2, top + NODE_HEIGHT
    path = f"M {x} {y}"
    for item in route[1:]:
        left, top, width = boxes[item]
        center = left + width // 2
        path += f" C {x} {y + BEND} {center} {top - BEND} {center} {top}"
        x, y = center, top + NODE_HEIGHT
        if isinstance(item, tuple):
            path += f" L {x} {y}"
    return path


def back_path(source, target, right):
    x1, y1, width1 = source
    x2, y2, width2 = target
    x1 += width1
    x2 += width2
    y1 += NODE_HEIGHT * 2 // 3
    y2 += NODE_HEIGHT // 3
    return f"M {x1} {y1} C {right} {y1} {right} {y2} {x2} {y2}"


def edge_path(route, boxes, right):
    source, target = boxes[route[0]], boxes[route[-1]]
    if target[1] > source[1]:
        return down_path(route, boxes)
    return back_path(source, target, right)


def svg(graph, root):
    rows, edges = routes(graph, root)
    boxes, width, height = layout(rows)
    right = width - MARGIN - LOOP // 2
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="{height}" viewBox="0 0 {width} {height}">',
        '<defs><marker id="arrow" viewBox="0 0 10 10" refX="10" refY="5" '
        'markerWidth="8" markerHeight="8" orient="auto">'
        '<path d="M 0 0 L 10 5 L 0 10 z" fill="#555"/></marker></defs>',
        f'<rect width="{width}" height="{height}" fill="white"/>',
    ]
    for route in edges:
        parts.append(f'<path d="{edge_path(route, boxes, right)}" '
                     'fill="none" stroke="#555" marker-end="url(#arrow)"/>')
    for name in graph:
        x, y, box_width = boxes[name]
        parts.append(
            f'<rect x="{x}" y="{y}" width="{box_width}" '
            f'height="{NODE_HEIGHT}" rx="6" fill="#eef3ff" stroke="#3355aa"/>'
        )
        parts.append(
            f'<text x="{x + box_width // 2}" y="{y + NODE_HEIGHT // 2}" '
            f'font-family="monospace" font-size="{FONT_SIZE}" '
            f'text-anchor="middle" dominant-baseline="central">'
            f"{escape(name)}</text>"
        )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"
