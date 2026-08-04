# -*- coding: utf-8 -*-
"""
geometry.py

Responsável por:

1. Obter as direções horizontal e vertical da vista.
2. Analisar os limites dos elementos coletados.
3. Projetar pontos no sistema de coordenadas da vista.
4. Criar linhas horizontais e verticais para as cotas.
5. Classificar curvas conforme sua orientação.
6. Preparar a geometria para o módulo dimension.py.

Compatível com pyRevit e IronPython 2.7.
"""

from Autodesk.Revit.DB import (
    Line,
    XYZ,
)


# ----------------------------------------------------------------------
# CONSTANTES
# ----------------------------------------------------------------------

TOLERANCE = 1e-9

ORIENTATION_HORIZONTAL = "horizontal"
ORIENTATION_VERTICAL = "vertical"
ORIENTATION_DIAGONAL = "diagonal"


# ----------------------------------------------------------------------
# VETORES BÁSICOS
# ----------------------------------------------------------------------

def normalize_vector(vector):
    """
    Retorna o vetor normalizado.

    Args:
        vector (XYZ):
            Vetor que será normalizado.

    Returns:
        XYZ:
            Vetor normalizado.

    Raises:
        ValueError:
            Quando o vetor é nulo ou possui comprimento muito pequeno.
    """

    if vector is None:
        raise ValueError("O vetor informado é nulo.")

    if vector.GetLength() < TOLERANCE:
        raise ValueError("Não é possível normalizar um vetor de comprimento zero.")

    return vector.Normalize()


def get_view_basis(view):
    """
    Obtém o sistema de coordenadas da vista.

    Para uma planta:

    - right: direção horizontal da tela;
    - up: direção vertical da tela;
    - normal: direção perpendicular à vista;
    - origin: origem da vista.

    Args:
        view (Autodesk.Revit.DB.View):
            Vista utilizada.

    Returns:
        dict:
            Dicionário contendo origin, right, up e normal.
    """

    if view is None:
        raise ValueError("A vista não foi informada.")

    right = normalize_vector(view.RightDirection)
    up = normalize_vector(view.UpDirection)
    normal = normalize_vector(view.ViewDirection)
    origin = view.Origin

    return {
        "origin": origin,
        "right": right,
        "up": up,
        "normal": normal,
    }


# ----------------------------------------------------------------------
# PROJEÇÃO DE PONTOS NA VISTA
# ----------------------------------------------------------------------

def project_point_to_view(point, view):
    """
    Converte um ponto XYZ do modelo para coordenadas locais da vista.

    A coordenada local é representada por:

    - u: posição horizontal;
    - v: posição vertical;
    - w: profundidade em relação ao plano da vista.

    Args:
        point (XYZ):
            Ponto no sistema global do Revit.

        view (Autodesk.Revit.DB.View):
            Vista usada como referência.

    Returns:
        tuple:
            Tupla no formato (u, v, w).
    """

    if point is None:
        raise ValueError("O ponto não foi informado.")

    basis = get_view_basis(view)

    relative = point - basis["origin"]

    u = relative.DotProduct(basis["right"])
    v = relative.DotProduct(basis["up"])
    w = relative.DotProduct(basis["normal"])

    return u, v, w


def point_from_view_coordinates(view, u, v, w=0.0):
    """
    Converte coordenadas locais da vista para um ponto XYZ global.

    Args:
        view (Autodesk.Revit.DB.View):
            Vista utilizada.

        u (float):
            Coordenada horizontal na vista.

        v (float):
            Coordenada vertical na vista.

        w (float):
            Profundidade relativa ao plano da vista.

    Returns:
        XYZ:
            Ponto no sistema global do Revit.
    """

    basis = get_view_basis(view)

    point = (
        basis["origin"]
        + basis["right"].Multiply(u)
        + basis["up"].Multiply(v)
        + basis["normal"].Multiply(w)
    )

    return point


def project_point_to_view_plane(point, view, plane_depth=0.0):
    """
    Projeta um ponto sobre o plano da vista.

    Args:
        point (XYZ):
            Ponto original.

        view (Autodesk.Revit.DB.View):
            Vista usada como referência.

        plane_depth (float):
            Profundidade desejada no sistema local da vista.

    Returns:
        XYZ:
            Ponto projetado no plano.
    """

    u, v, unused_w = project_point_to_view(point, view)

    return point_from_view_coordinates(
        view=view,
        u=u,
        v=v,
        w=plane_depth,
    )


# ----------------------------------------------------------------------
# BOUNDING BOX
# ----------------------------------------------------------------------

def get_bounding_box_corners(bounding_box):
    """
    Retorna os oito vértices de um BoundingBoxXYZ.

    O Transform do BoundingBoxXYZ é aplicado aos pontos.

    Args:
        bounding_box (BoundingBoxXYZ):
            Caixa envolvente do elemento.

    Returns:
        list[XYZ]:
            Lista com os oito vértices.
    """

    if bounding_box is None:
        return []

    minimum = bounding_box.Min
    maximum = bounding_box.Max
    transform = bounding_box.Transform

    local_corners = [
        XYZ(minimum.X, minimum.Y, minimum.Z),
        XYZ(maximum.X, minimum.Y, minimum.Z),
        XYZ(minimum.X, maximum.Y, minimum.Z),
        XYZ(maximum.X, maximum.Y, minimum.Z),

        XYZ(minimum.X, minimum.Y, maximum.Z),
        XYZ(maximum.X, minimum.Y, maximum.Z),
        XYZ(minimum.X, maximum.Y, maximum.Z),
        XYZ(maximum.X, maximum.Y, maximum.Z),
    ]

    global_corners = []

    for corner in local_corners:
        global_corner = transform.OfPoint(corner)
        global_corners.append(global_corner)

    return global_corners


def get_element_bounding_box(element, view):
    """
    Obtém a caixa envolvente de um elemento na vista.

    Args:
        element (Element):
            Elemento do Revit.

        view (View):
            Vista utilizada.

    Returns:
        BoundingBoxXYZ or None:
            Caixa envolvente do elemento.
    """

    if element is None:
        return None

    try:
        bounding_box = element.get_BoundingBox(view)
    except Exception:
        bounding_box = None

    if bounding_box is None:
        try:
            bounding_box = element.get_BoundingBox(None)
        except Exception:
            bounding_box = None

    return bounding_box


def get_element_view_bounds(element, view):
    """
    Calcula os limites de um elemento no sistema local da vista.

    Args:
        element (Element):
            Elemento analisado.

        view (View):
            Vista utilizada.

    Returns:
        dict or None:
            Limites locais do elemento:

            {
                "min_u": float,
                "max_u": float,
                "min_v": float,
                "max_v": float,
                "min_w": float,
                "max_w": float
            }
    """

    bounding_box = get_element_bounding_box(element, view)

    if bounding_box is None:
        return None

    corners = get_bounding_box_corners(bounding_box)

    if not corners:
        return None

    u_values = []
    v_values = []
    w_values = []

    for corner in corners:
        u, v, w = project_point_to_view(corner, view)

        u_values.append(u)
        v_values.append(v)
        w_values.append(w)

    return {
        "min_u": min(u_values),
        "max_u": max(u_values),
        "min_v": min(v_values),
        "max_v": max(v_values),
        "min_w": min(w_values),
        "max_w": max(w_values),
    }


# ----------------------------------------------------------------------
# ELEMENTOS COLETADOS
# ----------------------------------------------------------------------

def flatten_element_groups(element_groups):
    """
    Converte o dicionário retornado pelo collector.py em uma lista única.

    Args:
        element_groups (dict or list):
            Dicionário de categorias ou lista de elementos.

    Returns:
        list:
            Lista única de elementos.
    """

    if element_groups is None:
        return []

    if isinstance(element_groups, dict):
        elements = []

        for group_name in element_groups:
            group_elements = element_groups.get(group_name, [])

            for element in group_elements:
                if element is not None:
                    elements.append(element)

        return elements

    return [
        element
        for element in element_groups
        if element is not None
    ]


def calculate_plan_bounds(element_groups, view):
    """
    Calcula os limites gerais dos elementos na vista.

    Args:
        element_groups (dict or list):
            Elementos retornados pelo collector.py ou lista de elementos.

        view (View):
            Vista utilizada.

    Returns:
        dict:
            Limites gerais da planta no sistema local da vista.

    Raises:
        ValueError:
            Quando nenhum limite válido é encontrado.
    """

    elements = flatten_element_groups(element_groups)

    if not elements:
        raise ValueError(
            "Nenhum elemento foi informado para calcular os limites da planta."
        )

    minimum_u = None
    maximum_u = None
    minimum_v = None
    maximum_v = None
    minimum_w = None
    maximum_w = None

    valid_element_count = 0

    for element in elements:
        bounds = get_element_view_bounds(element, view)

        if bounds is None:
            continue

        valid_element_count += 1

        if minimum_u is None:
            minimum_u = bounds["min_u"]
            maximum_u = bounds["max_u"]
            minimum_v = bounds["min_v"]
            maximum_v = bounds["max_v"]
            minimum_w = bounds["min_w"]
            maximum_w = bounds["max_w"]

            continue

        minimum_u = min(minimum_u, bounds["min_u"])
        maximum_u = max(maximum_u, bounds["max_u"])
        minimum_v = min(minimum_v, bounds["min_v"])
        maximum_v = max(maximum_v, bounds["max_v"])
        minimum_w = min(minimum_w, bounds["min_w"])
        maximum_w = max(maximum_w, bounds["max_w"])

    if valid_element_count == 0:
        raise ValueError(
            "Não foi possível obter a geometria dos elementos coletados."
        )

    width = maximum_u - minimum_u
    height = maximum_v - minimum_v

    return {
        "min_u": minimum_u,
        "max_u": maximum_u,
        "min_v": minimum_v,
        "max_v": maximum_v,
        "min_w": minimum_w,
        "max_w": maximum_w,
        "width": width,
        "height": height,
        "center_u": (minimum_u + maximum_u) / 2.0,
        "center_v": (minimum_v + maximum_v) / 2.0,
        "element_count": valid_element_count,
    }


# ----------------------------------------------------------------------
# ORIENTAÇÃO DE CURVAS
# ----------------------------------------------------------------------

def classify_direction(direction, view, tolerance=0.001):
    """
    Classifica um vetor como horizontal, vertical ou diagonal na vista.

    Args:
        direction (XYZ):
            Vetor de direção.

        view (View):
            Vista utilizada.

        tolerance (float):
            Tolerância angular baseada no produto escalar.

    Returns:
        str:
            horizontal, vertical ou diagonal.
    """

    if direction is None:
        return ORIENTATION_DIAGONAL

    if direction.GetLength() < TOLERANCE:
        return ORIENTATION_DIAGONAL

    normalized_direction = direction.Normalize()
    basis = get_view_basis(view)

    horizontal_alignment = abs(
        normalized_direction.DotProduct(basis["right"])
    )

    vertical_alignment = abs(
        normalized_direction.DotProduct(basis["up"])
    )

    if horizontal_alignment >= 1.0 - tolerance:
        return ORIENTATION_HORIZONTAL

    if vertical_alignment >= 1.0 - tolerance:
        return ORIENTATION_VERTICAL

    return ORIENTATION_DIAGONAL


def classify_curve(curve, view, tolerance=0.001):
    """
    Classifica a orientação de uma curva.

    Args:
        curve (Curve):
            Curva analisada.

        view (View):
            Vista utilizada.

        tolerance (float):
            Tolerância para classificação.

    Returns:
        str:
            horizontal, vertical ou diagonal.
    """

    if curve is None:
        return ORIENTATION_DIAGONAL

    try:
        start_point = curve.GetEndPoint(0)
        end_point = curve.GetEndPoint(1)
    except Exception:
        return ORIENTATION_DIAGONAL

    direction = end_point - start_point

    return classify_direction(
        direction=direction,
        view=view,
        tolerance=tolerance,
    )


# ----------------------------------------------------------------------
# LINHAS DE COTA
# ----------------------------------------------------------------------

def create_horizontal_dimension_line(
    view,
    bounds,
    picked_point,
    extension=0.0,
):
    """
    Cria uma linha horizontal passando pelo ponto escolhido pelo usuário.

    Essa linha será usada para cotas cujas referências estejam separadas
    horizontalmente, como faces verticais de paredes.

    Args:
        view (View):
            Vista ativa.

        bounds (dict):
            Limites retornados por calculate_plan_bounds().

        picked_point (XYZ):
            Ponto escolhido pelo usuário para posicionar a cota.

        extension (float):
            Extensão aplicada em cada extremidade da linha, em pés.

    Returns:
        Line:
            Linha horizontal para NewDimension().
    """

    if bounds is None:
        raise ValueError("Os limites da planta não foram informados.")

    if picked_point is None:
        raise ValueError("O ponto de posicionamento não foi informado.")

    picked_u, picked_v, picked_w = project_point_to_view(
        picked_point,
        view,
    )

    start_u = bounds["min_u"] - extension
    end_u = bounds["max_u"] + extension

    start_point = point_from_view_coordinates(
        view=view,
        u=start_u,
        v=picked_v,
        w=picked_w,
    )

    end_point = point_from_view_coordinates(
        view=view,
        u=end_u,
        v=picked_v,
        w=picked_w,
    )

    if start_point.DistanceTo(end_point) < TOLERANCE:
        raise ValueError("A linha horizontal possui comprimento inválido.")

    return Line.CreateBound(start_point, end_point)


def create_vertical_dimension_line(
    view,
    bounds,
    picked_point,
    extension=0.0,
):
    """
    Cria uma linha vertical passando pelo ponto escolhido pelo usuário.

    Essa linha será usada para cotas cujas referências estejam separadas
    verticalmente, como faces horizontais de paredes.

    Args:
        view (View):
            Vista ativa.

        bounds (dict):
            Limites retornados por calculate_plan_bounds().

        picked_point (XYZ):
            Ponto escolhido pelo usuário para posicionar a cota.

        extension (float):
            Extensão aplicada em cada extremidade da linha, em pés.

    Returns:
        Line:
            Linha vertical para NewDimension().
    """

    if bounds is None:
        raise ValueError("Os limites da planta não foram informados.")

    if picked_point is None:
        raise ValueError("O ponto de posicionamento não foi informado.")

    picked_u, picked_v, picked_w = project_point_to_view(
        picked_point,
        view,
    )

    start_v = bounds["min_v"] - extension
    end_v = bounds["max_v"] + extension

    start_point = point_from_view_coordinates(
        view=view,
        u=picked_u,
        v=start_v,
        w=picked_w,
    )

    end_point = point_from_view_coordinates(
        view=view,
        u=picked_u,
        v=end_v,
        w=picked_w,
    )

    if start_point.DistanceTo(end_point) < TOLERANCE:
        raise ValueError("A linha vertical possui comprimento inválido.")

    return Line.CreateBound(start_point, end_point)


# ----------------------------------------------------------------------
# POSICIONAMENTO AUTOMÁTICO OPCIONAL
# ----------------------------------------------------------------------

def get_default_horizontal_position(view, bounds, offset):
    """
    Retorna um ponto abaixo da planta para posicionar uma cota horizontal.

    Args:
        view (View):
            Vista utilizada.

        bounds (dict):
            Limites da planta.

        offset (float):
            Distância entre a planta e a linha de cota, em pés.

    Returns:
        XYZ:
            Ponto de posicionamento.
    """

    return point_from_view_coordinates(
        view=view,
        u=bounds["center_u"],
        v=bounds["min_v"] - offset,
        w=0.0,
    )


def get_default_vertical_position(view, bounds, offset):
    """
    Retorna um ponto à esquerda da planta para posicionar uma cota vertical.

    Args:
        view (View):
            Vista utilizada.

        bounds (dict):
            Limites da planta.

        offset (float):
            Distância entre a planta e a linha de cota, em pés.

    Returns:
        XYZ:
            Ponto de posicionamento.
    """

    return point_from_view_coordinates(
        view=view,
        u=bounds["min_u"] - offset,
        v=bounds["center_v"],
        w=0.0,
    )


# ----------------------------------------------------------------------
# PONTOS ÚTEIS DOS LIMITES
# ----------------------------------------------------------------------

def get_bounds_corners(view, bounds, depth=0.0):
    """
    Retorna os quatro cantos dos limites gerais da planta.

    Args:
        view (View):
            Vista utilizada.

        bounds (dict):
            Limites calculados.

        depth (float):
            Profundidade dos pontos no plano da vista.

    Returns:
        dict:
            Quatro cantos da planta.
    """

    return {
        "bottom_left": point_from_view_coordinates(
            view,
            bounds["min_u"],
            bounds["min_v"],
            depth,
        ),

        "bottom_right": point_from_view_coordinates(
            view,
            bounds["max_u"],
            bounds["min_v"],
            depth,
        ),

        "top_left": point_from_view_coordinates(
            view,
            bounds["min_u"],
            bounds["max_v"],
            depth,
        ),

        "top_right": point_from_view_coordinates(
            view,
            bounds["max_u"],
            bounds["max_v"],
            depth,
        ),
    }