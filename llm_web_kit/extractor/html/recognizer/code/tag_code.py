from lxml.html import HtmlElement

from llm_web_kit.extractor.html.recognizer.code.common import (
    _BLOCK_ELES, replace_node_by_cccode)
from llm_web_kit.extractor.html.recognizer.recognizer import CCTag

"""
处理仅由<code>标签组成的代码块
"""


def __get_html_element(root: HtmlElement, node_path: list[str]) -> HtmlElement:
    path = '/'.join(node_path)
    path = '/'.join(path.removeprefix('/').split('/')[1:])
    if not path:
        return root
    node = root.find(path, {'og': 'http://ogp.me/ns'})
    assert node is not None
    return node


def __is_all_chars_in_code_element(node: HtmlElement) -> bool:
    full_text = ''.join([x for x in ''.join(node.itertext(None)) if not x.isspace() and not x.isdigit()])
    code_text = ''
    for s in node.xpath('.//code//text()'):
        for c in s:
            if not c.isspace() and not c.isdigit():
                code_text += c
    return full_text == code_text


def __group_code_by_distance(
    root: HtmlElement,
    node_paths: list[list[str]],
    dist: list[list[int]],
) -> list[str]:
    father = list(range(len(node_paths)))

    def get_father(x: int) -> int:
        if father[x] == x:
            return x
        father[x] = get_father(father[x])
        return father[x]

    edges: list[tuple[int, int, int]] = []
    root_paths: list[list[str]] = []
    for i in range(len(node_paths)):
        root_paths.append(node_paths[i])
        for j in range(i + 1, len(node_paths)):
            edges.append((dist[i][j], i, j))
    edges = sorted(edges)

    used_edge = 0
    meet = set()
    for edge in edges:
        _, i, j = edge
        i = get_father(i)
        j = get_father(j)
        if i != j and (i, j) not in meet:
            common_node_idx = min(len(root_paths[i]), len(root_paths[j]))
            for idx, (x, y) in enumerate(zip(root_paths[i], root_paths[j])):
                if idx == 0:
                    continue
                if x != y:
                    common_node_idx = idx
                    break
            maybe_tree_root = __get_html_element(root, root_paths[i][:common_node_idx])

            if len(maybe_tree_root.xpath(f'.//{CCTag.CC_CODE}|.//{CCTag.CC_CODE_INLINE}')) > 0:
                meet.add((i, j))
                continue

            if not __is_all_chars_in_code_element(maybe_tree_root):
                meet.add((i, j))
                continue

            root_paths[i] = root_paths[i][:common_node_idx]
            used_edge += 1
            father[j] = i

    root_paths = [
        root_path for i, root_path in enumerate(root_paths) if i == get_father(i)
    ]

    removed = set()
    root_paths_joined = sorted(
        list(set(['/'.join(root_path) for root_path in root_paths]))
    )
    for x in root_paths_joined:
        for y in root_paths_joined:
            if len(x) < len(y) and y.startswith(x):
                removed.add(y)
    return [x for x in root_paths_joined if x not in removed]


def __compute_distance_matrix(node_paths: list[list[str]]) -> list[list[int]]:
    """
    计算节点路径的距离矩阵，具体步骤：
    1. 创建距离矩阵，计算每两个节点之间的距离
    2. 距离计算方法：从共同祖先节点到两个节点的路径长度之和
    例如：
    节点1路径：/html/body/div/code
    节点2路径：/html/body/pre/code
    共同祖先到 body，距离为 2（div->code) + 2(pre->code) = 4
    节点1和节点2的距离为 4

    距离矩阵（对称矩阵）：
    [0, 1, 2, 3],
    [1, 0, 1, 2],
    [2, 1, 0, 1],
    [3, 2, 1, 0]

    Args:
        node_paths: 节点路径

    Returns:
        list[list[int]]: 距离矩阵
    """
    def get_lca_depth(path1: list[str], path2: list[str]) -> int:
        for i, (x, y) in enumerate(zip(path1, path2)):
            if x != y:
                return i
        return min(len(path1), len(path2))

    n = len(node_paths)
    dist = [[0] * n for _ in range(n)]

    for i in range(n):
        for j in range(i + 1, n):
            lca_depth = get_lca_depth(node_paths[i], node_paths[j])
            d = len(node_paths[i]) + len(node_paths[j]) - 2 * lca_depth
            dist[i][j] = dist[j][i] = d

    return dist


def __get_code_node_paths(html_el: HtmlElement) -> list[list[str]]:
    """获取 html_el 中所有 code 标签的路径 只获取最外层的code标签， 如果code标签内还有code标签，则不获取。

    Args:
        html_el: 根节点

    Returns:
        list[list[str]]: 所有 code 标签的路径: 如[['body', 'div', 'code'], ['body', 'div', 'span', 'code']]
    """
    node_paths: list[list[str]] = []
    for code_node in html_el.iterchildren():
        if code_node.tag == 'code':
            hit = False
            for _ in code_node.iter('cccode'):
                hit = True
                break
            if hit:
                continue
            node_path = code_node.getroottree().getpath(code_node)
            node_paths.append(node_path.split('/'))
        else:
            node_paths.extend(__get_code_node_paths(code_node))
    return node_paths


def __get_code_blocks_nodes(node: HtmlElement, tree_roots: list[str]) -> list[HtmlElement]:
    """找出所有需要被转换为代码块的候选节点.

    Args:
        node: 当前正在检查的节点
        tree_roots: 代码块组的根节点路径列表

    Returns:
        list[HtmlElement]: 需要被转换的候选节点列表
    """
    current_path = node.getroottree().getpath(node)

    # 检查当前节点是否是某个代码块组的根节点
    if current_path in tree_roots:
        return [node]

    # 检查当前节点是否是某个代码块组的祖先节点
    is_ancestor = any(root_path.startswith(current_path) for root_path in tree_roots)
    if not is_ancestor:
        return []

    # 递归检查子节点
    candidates = []
    for child in node.getchildren():
        if isinstance(child, HtmlElement):
            candidates.extend(__get_code_blocks_nodes(child, tree_roots))

    return candidates


def detect(body: HtmlElement) -> bool:
    for code_node in body.iter('code'):
        hit = False
        for _ in code_node.iter('cccode'):
            hit = True
            break
        if not hit:
            return True
    return False


def __detect_inline_code(root: HtmlElement, node_paths: list[list[str]]) -> tuple[list[list[str]], list[HtmlElement]]:
    new_node_paths = []
    inline_code = []

    for node_path in node_paths:
        ele = __get_html_element(root, node_path)

        parent = ele
        while parent.tag not in _BLOCK_ELES and parent.getparent() is not None:
            parent = parent.getparent()

        """
        并非所有 inline code 都可以识别出来
        """
        if not __is_all_chars_in_code_element(parent):
            inline_code.append(ele)
            continue

        new_node_paths.append(node_path)

    return new_node_paths, inline_code


def modify_tree(root: HtmlElement) -> None:
    """将 html 树中所有 code 标签转换为代码块.

    Args:
        root: html 树的根节点
    """
    node_paths = __get_code_node_paths(root)  # 获取所有 code 标签的路径，不包含嵌套的子 code 标签
    node_paths, inline_code = __detect_inline_code(root, node_paths)
    for node in inline_code:
        replace_node_by_cccode(node, 'tag_code', False, True)

    if len(node_paths) == 0:
        tree_roots = []
    elif len(node_paths) == 1:
        tree_roots = ['/'.join(node_paths[0])]
    else:
        dist_matrix = __compute_distance_matrix(node_paths)  # 计算距离矩阵
        tree_roots = __group_code_by_distance(root, node_paths, dist_matrix)  # 根据距离矩阵，对code标签进行分组

    nodes = __get_code_blocks_nodes(root, tree_roots)  # 获取所有需要被转换为代码块的节点，并进行标签替换
    for node in nodes:
        replace_node_by_cccode(node, 'tag_code', False)
