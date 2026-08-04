# -*- coding: utf-8 -*-
"""
references.py

Responsável por:

1. Extrair referências geométricas válidas.
2. Obter faces laterais de paredes.
3. Obter planos de referência de famílias.
4. Obter referências geométricas de famílias.
5. Obter referências de eixos.
6. Separar referências para cotas horizontais e verticais.
7. Ordenar e remover apenas referências realmente duplicadas.
8. Organizar as referências por categoria e orientação.

Compatível com pyRevit, IronPython e versões recentes do Revit.
"""

from Autodesk.Revit.DB import (
    BuiltInCategory,
    FamilyInstance,
    FamilyInstanceReferenceType,
    GeometryInstance,
    Grid,
    HostObjectUtils,
    Options,
    PlanarFace,
    Reference,
    ShellLayerType,
    Solid,
    Transform,
    XYZ,
)

import geometry


# ----------------------------------------------------------------------
# CONSTANTES
# ----------------------------------------------------------------------

TOLERANCE = 0.001
POSITION_TOLERANCE = 1e-6
MINIMUM_FACE_AREA = 1e-8

REFERENCE_HORIZONTAL = "horizontal"
REFERENCE_VERTICAL = "vertical"


# ----------------------------------------------------------------------
# ELEMENT ID
# ----------------------------------------------------------------------

def get_element_id_value(element_id):
    """
    Retorna o valor numérico de um ElementId.

    Compatibilidade:

    - Revit recente: ElementId.Value;
    - Revit antigo: ElementId.IntegerValue.
    """

    if element_id is None:
        return -1

    try:
        return element_id.Value
    except AttributeError:
        pass
    except Exception:
        pass

    try:
        return element_id.IntegerValue
    except AttributeError:
        pass
    except Exception:
        pass

    return -1


def get_element_value(element):
    """
    Retorna o valor numérico do ID de um elemento.
    """

    if element is None:
        return -1

    try:
        return get_element_id_value(element.Id)
    except Exception:
        return -1


# ----------------------------------------------------------------------
# CATEGORIAS
# ----------------------------------------------------------------------

def get_element_category_id(element):
    """
    Retorna o valor numérico da categoria de um elemento.
    """

    if element is None:
        return None

    category = element.Category

    if category is None:
        return None

    return get_element_id_value(category.Id)


def is_category(element, built_in_category):
    """
    Verifica se o elemento pertence à categoria indicada.
    """

    category_id = get_element_category_id(element)

    if category_id is None:
        return False

    try:
        expected_id = int(built_in_category)
    except Exception:
        return False

    return category_id == expected_id


# ----------------------------------------------------------------------
# IDENTIFICAÇÃO DAS REFERÊNCIAS
# ----------------------------------------------------------------------

def get_reference_key(reference, document):
    """
    Cria uma chave única para uma referência.

    A representação estável diferencia:

    - faces diferentes do mesmo elemento;
    - planos de referência;
    - referências de famílias;
    - referências de eixos.

    Args:
        reference (Reference):
            Referência analisada.

        document (Document):
            Documento do Revit.

    Returns:
        str or None:
            Chave única da referência.
    """

    if reference is None:
        return None

    if document is not None:
        try:
            stable_reference = (
                reference.ConvertToStableRepresentation(document)
            )

            if stable_reference:
                return stable_reference

        except Exception:
            pass

    # Alternativa para referências que não fornecem representação estável.
    try:
        element_id = get_element_id_value(reference.ElementId)
    except Exception:
        element_id = -1

    try:
        reference_type = str(reference.ElementReferenceType)
    except Exception:
        reference_type = "unknown"

    try:
        reference_hash = reference.GetHashCode()
    except Exception:
        reference_hash = id(reference)

    return "{0}|{1}|{2}".format(
        element_id,
        reference_type,
        reference_hash,
    )


def remove_duplicate_references(reference_data, document):
    """
    Remove somente referências realmente repetidas.

    Args:
        reference_data (list[dict]):
            Lista com os dados das referências.

        document (Document):
            Documento atual.

    Returns:
        list[dict]:
            Referências sem duplicidade.
    """

    unique_items = []
    registered_keys = set()

    for item in reference_data:

        if item is None:
            continue

        reference = item.get("reference")

        if reference is None:
            continue

        key = get_reference_key(
            reference=reference,
            document=document,
        )

        if key is None:
            continue

        if key in registered_keys:
            continue

        registered_keys.add(key)
        unique_items.append(item)

    return unique_items


# ----------------------------------------------------------------------
# OPÇÕES DE GEOMETRIA
# ----------------------------------------------------------------------

def create_geometry_options(view):
    """
    Cria as opções usadas para extrair a geometria.

    ComputeReferences precisa estar ativado para que faces e arestas
    possam fornecer referências para dimensões.
    """

    options = Options()

    options.ComputeReferences = True
    options.IncludeNonVisibleObjects = True

    if view is not None:
        try:
            options.View = view
        except Exception:
            pass

    return options


# ----------------------------------------------------------------------
# TRANSFORMAÇÕES
# ----------------------------------------------------------------------

def combine_transforms(parent_transform, child_transform):
    """
    Combina duas transformações.

    Args:
        parent_transform (Transform or None):
            Transformação acumulada.

        child_transform (Transform or None):
            Transformação da instância atual.

    Returns:
        Transform:
            Transformação combinada.
    """

    if parent_transform is None and child_transform is None:
        return Transform.Identity

    if parent_transform is None:
        return child_transform

    if child_transform is None:
        return parent_transform

    return parent_transform.Multiply(child_transform)


def transform_point(point, transform):
    """
    Aplica transformação a um ponto.
    """

    if point is None:
        return None

    if transform is None:
        return point

    try:
        return transform.OfPoint(point)
    except Exception:
        return point


def transform_vector(vector, transform):
    """
    Aplica transformação a um vetor.
    """

    if vector is None:
        return None

    if transform is None:
        return vector

    try:
        return transform.OfVector(vector)
    except Exception:
        return vector


# ----------------------------------------------------------------------
# EXTRAÇÃO DE FACES PLANAS
# ----------------------------------------------------------------------

def collect_planar_faces_from_geometry(
    geometry_element,
    transform=None,
):
    """
    Percorre a geometria e retorna faces planas referenciáveis.

    Para GeometryInstance, utiliza GetSymbolGeometry(). A origem e o vetor
    normal são transformados para as coordenadas do projeto.

    Args:
        geometry_element (GeometryElement):
            Geometria analisada.

        transform (Transform):
            Transformação acumulada.

    Returns:
        list[dict]:
            Faces planas encontradas.
    """

    faces = []

    if geometry_element is None:
        return faces

    if transform is None:
        transform = Transform.Identity

    for geometry_object in geometry_element:

        # --------------------------------------------------------------
        # SÓLIDOS
        # --------------------------------------------------------------

        if isinstance(geometry_object, Solid):

            try:
                if geometry_object.Faces is None:
                    continue
            except Exception:
                continue

            try:
                if geometry_object.Volume <= 0:
                    continue
            except Exception:
                pass

            for face in geometry_object.Faces:

                if not isinstance(face, PlanarFace):
                    continue

                try:
                    face_area = face.Area
                except Exception:
                    face_area = 0.0

                if face_area < MINIMUM_FACE_AREA:
                    continue

                try:
                    reference = face.Reference
                except Exception:
                    reference = None

                if reference is None:
                    continue

                try:
                    local_normal = face.FaceNormal
                    local_origin = face.Origin
                except Exception:
                    continue

                global_normal = transform_vector(
                    local_normal,
                    transform,
                )

                global_origin = transform_point(
                    local_origin,
                    transform,
                )

                if global_normal is None or global_origin is None:
                    continue

                try:
                    global_normal = global_normal.Normalize()
                except Exception:
                    continue

                faces.append({
                    "face": face,
                    "reference": reference,
                    "normal": global_normal,
                    "origin": global_origin,
                    "area": face_area,
                })

        # --------------------------------------------------------------
        # INSTÂNCIAS DE GEOMETRIA
        # --------------------------------------------------------------

        elif isinstance(geometry_object, GeometryInstance):

            try:
                instance_transform = geometry_object.Transform
            except Exception:
                instance_transform = Transform.Identity

            accumulated_transform = combine_transforms(
                transform,
                instance_transform,
            )

            try:
                symbol_geometry = geometry_object.GetSymbolGeometry()
            except Exception:
                symbol_geometry = None

            if symbol_geometry is None:
                continue

            nested_faces = collect_planar_faces_from_geometry(
                geometry_element=symbol_geometry,
                transform=accumulated_transform,
            )

            faces.extend(nested_faces)

    return faces


def get_element_planar_faces(element, view):
    """
    Obtém as faces planas referenciáveis de um elemento.
    """

    if element is None:
        return []

    options = create_geometry_options(view)

    try:
        geometry_element = element.get_Geometry(options)
    except Exception:
        geometry_element = None

    if geometry_element is None:
        return []

    return collect_planar_faces_from_geometry(
        geometry_element=geometry_element,
        transform=Transform.Identity,
    )


# ----------------------------------------------------------------------
# CLASSIFICAÇÃO DE FACES
# ----------------------------------------------------------------------

def classify_face_reference(
    face_data,
    view,
    tolerance=TOLERANCE,
):
    """
    Classifica uma face conforme a direção em que ela pode ser cotada.

    Uma face com normal horizontal é usada em uma cota horizontal.

    Uma face com normal vertical é usada em uma cota vertical.
    """

    if face_data is None:
        return None

    normal = face_data.get("normal")

    if normal is None:
        return None

    basis = geometry.get_view_basis(view)

    horizontal_alignment = abs(
        normal.DotProduct(basis["right"])
    )

    vertical_alignment = abs(
        normal.DotProduct(basis["up"])
    )

    if horizontal_alignment >= 1.0 - tolerance:
        return REFERENCE_HORIZONTAL

    if vertical_alignment >= 1.0 - tolerance:
        return REFERENCE_VERTICAL

    return None


def get_reference_position(face_data, view, orientation):
    """
    Retorna a posição da face no sistema local da vista.
    """

    origin = face_data.get("origin")

    if origin is None:
        return None

    u, v, unused_w = geometry.project_point_to_view(
        origin,
        view,
    )

    if orientation == REFERENCE_HORIZONTAL:
        return u

    if orientation == REFERENCE_VERTICAL:
        return v

    return None


def create_face_reference_data(
    element,
    face_data,
    view,
    source,
):
    """
    Converte os dados de uma face para o formato usado pelo plugin.
    """

    orientation = classify_face_reference(
        face_data=face_data,
        view=view,
    )

    if orientation is None:
        return None

    position = get_reference_position(
        face_data=face_data,
        view=view,
        orientation=orientation,
    )

    if position is None:
        return None

    return {
        "reference": face_data["reference"],
        "position": position,
        "origin": face_data["origin"],
        "normal": face_data["normal"],
        "element": element,
        "element_id": element.Id,
        "source": source,
        "orientation": orientation,
    }


def classify_element_faces(element, view):
    """
    Separa as faces de um elemento entre referências horizontais e
    verticais.
    """

    result = {
        REFERENCE_HORIZONTAL: [],
        REFERENCE_VERTICAL: [],
    }

    if element is None:
        return result

    faces = get_element_planar_faces(
        element=element,
        view=view,
    )

    for face_data in faces:

        item = create_face_reference_data(
            element=element,
            face_data=face_data,
            view=view,
            source="face",
        )

        if item is None:
            continue

        orientation = item["orientation"]
        result[orientation].append(item)

    document = element.Document

    result[REFERENCE_HORIZONTAL] = remove_duplicate_references(
        result[REFERENCE_HORIZONTAL],
        document,
    )

    result[REFERENCE_VERTICAL] = remove_duplicate_references(
        result[REFERENCE_VERTICAL],
        document,
    )

    return result


# ----------------------------------------------------------------------
# REFERÊNCIAS DE PAREDES
# ----------------------------------------------------------------------

def append_wall_side_references(
    references_list,
    wall,
    shell_layer_type,
):
    """
    Adiciona faces laterais internas ou externas de uma parede.
    """

    try:
        wall_references = HostObjectUtils.GetSideFaces(
            wall,
            shell_layer_type,
        )
    except Exception:
        wall_references = None

    if wall_references is None:
        return

    for reference in wall_references:
        if reference is not None:
            references_list.append(reference)


def get_wall_side_references(wall, view):
    """
    Obtém as faces laterais interna e externa de uma parede.
    """

    result = {
        REFERENCE_HORIZONTAL: [],
        REFERENCE_VERTICAL: [],
    }

    if wall is None:
        return result

    wall_references = []

    append_wall_side_references(
        references_list=wall_references,
        wall=wall,
        shell_layer_type=ShellLayerType.Exterior,
    )

    append_wall_side_references(
        references_list=wall_references,
        wall=wall,
        shell_layer_type=ShellLayerType.Interior,
    )

    # Caso a parede não forneça faces pelo HostObjectUtils.
    if not wall_references:
        return classify_element_faces(
            element=wall,
            view=view,
        )

    for reference in wall_references:

        try:
            face = wall.GetGeometryObjectFromReference(reference)
        except Exception:
            face = None

        if not isinstance(face, PlanarFace):
            continue

        try:
            normal = face.FaceNormal.Normalize()
            origin = face.Origin
            area = face.Area
        except Exception:
            continue

        face_data = {
            "face": face,
            "reference": reference,
            "normal": normal,
            "origin": origin,
            "area": area,
        }

        item = create_face_reference_data(
            element=wall,
            face_data=face_data,
            view=view,
            source="wall_side_face",
        )

        if item is None:
            continue

        orientation = item["orientation"]
        result[orientation].append(item)

    document = wall.Document

    result[REFERENCE_HORIZONTAL] = remove_duplicate_references(
        result[REFERENCE_HORIZONTAL],
        document,
    )

    result[REFERENCE_VERTICAL] = remove_duplicate_references(
        result[REFERENCE_VERTICAL],
        document,
    )

    return result


# ----------------------------------------------------------------------
# REFERÊNCIAS NOMEADAS DE FAMÍLIAS
# ----------------------------------------------------------------------

def get_family_instance_references(
    family_instance,
    reference_type,
):
    """
    Obtém planos ou linhas de referência de uma família.
    """

    if not isinstance(family_instance, FamilyInstance):
        return []

    try:
        family_references = family_instance.GetReferences(
            reference_type
        )
    except Exception:
        family_references = None

    if family_references is None:
        return []

    return [
        reference
        for reference in family_references
        if reference is not None
    ]


def get_family_location_point(family_instance):
    """
    Obtém um ponto aproximado da instância de família.
    """

    if family_instance is None:
        return None

    try:
        location = family_instance.Location
    except Exception:
        location = None

    if location is None:
        return None

    try:
        return location.Point
    except Exception:
        pass

    try:
        curve = location.Curve

        start_point = curve.GetEndPoint(0)
        end_point = curve.GetEndPoint(1)

        return XYZ(
            (start_point.X + end_point.X) / 2.0,
            (start_point.Y + end_point.Y) / 2.0,
            (start_point.Z + end_point.Z) / 2.0,
        )

    except Exception:
        return None


def get_family_bounds(family_instance, view):
    """
    Retorna os limites da instância no sistema local da vista.
    """

    try:
        return geometry.get_element_view_bounds(
            family_instance,
            view,
        )
    except Exception:
        return None


def append_family_reference_type(
    result,
    family_instance,
    view,
    reference_type,
    orientation,
    position,
    source,
):
    """
    Adiciona um tipo de referência nomeada ao resultado.
    """

    if position is None:
        return

    family_references = get_family_instance_references(
        family_instance=family_instance,
        reference_type=reference_type,
    )

    location_point = get_family_location_point(
        family_instance
    )

    for reference in family_references:

        result[orientation].append({
            "reference": reference,
            "position": position,
            "origin": location_point,
            "normal": None,
            "element": family_instance,
            "element_id": family_instance.Id,
            "source": source,
            "orientation": orientation,
        })


def collect_named_family_references(
    family_instance,
    view,
):
    """
    Coleta planos de referência nomeados da família.

    São tentados:

    - esquerda;
    - direita;
    - frente;
    - fundo;
    - centro esquerda/direita;
    - centro frente/fundo.
    """

    result = {
        REFERENCE_HORIZONTAL: [],
        REFERENCE_VERTICAL: [],
    }

    bounds = get_family_bounds(
        family_instance,
        view,
    )

    if bounds is None:
        return result

    # Referências que posicionamos pela coordenada horizontal da vista.
    horizontal_types = [
        (
            FamilyInstanceReferenceType.Left,
            bounds["min_u"],
            "family_left",
        ),
        (
            FamilyInstanceReferenceType.Right,
            bounds["max_u"],
            "family_right",
        ),
        (
            FamilyInstanceReferenceType.CenterLeftRight,
            (bounds["min_u"] + bounds["max_u"]) / 2.0,
            "family_center_left_right",
        ),
    ]

    # Referências que posicionamos pela coordenada vertical da vista.
    vertical_types = [
        (
            FamilyInstanceReferenceType.Front,
            bounds["min_v"],
            "family_front",
        ),
        (
            FamilyInstanceReferenceType.Back,
            bounds["max_v"],
            "family_back",
        ),
        (
            FamilyInstanceReferenceType.CenterFrontBack,
            (bounds["min_v"] + bounds["max_v"]) / 2.0,
            "family_center_front_back",
        ),
    ]

    for reference_type, position, source in horizontal_types:

        append_family_reference_type(
            result=result,
            family_instance=family_instance,
            view=view,
            reference_type=reference_type,
            orientation=REFERENCE_HORIZONTAL,
            position=position,
            source=source,
        )

    for reference_type, position, source in vertical_types:

        append_family_reference_type(
            result=result,
            family_instance=family_instance,
            view=view,
            reference_type=reference_type,
            orientation=REFERENCE_VERTICAL,
            position=position,
            source=source,
        )

    document = family_instance.Document

    result[REFERENCE_HORIZONTAL] = remove_duplicate_references(
        result[REFERENCE_HORIZONTAL],
        document,
    )

    result[REFERENCE_VERTICAL] = remove_duplicate_references(
        result[REFERENCE_VERTICAL],
        document,
    )

    return result


def select_extreme_references(reference_data):
    """
    Mantém somente as referências geométricas extremas.

    Para uma determinada direção, seleciona:

    - referência de menor posição;
    - referência de maior posição.

    Isso evita coletar faces internas de portas, janelas e pilares, como
    folhas, marcos, painéis e guarnições.

    Args:
        reference_data (list[dict]):
            Referências geométricas da família.

    Returns:
        list[dict]:
            No máximo duas referências extremas.
    """

    if not reference_data:
        return []

    valid_references = []

    for item in reference_data:

        if item is None:
            continue

        position = item.get("position")

        if position is None:
            continue

        valid_references.append(item)

    if not valid_references:
        return []

    sorted_references = sorted(
        valid_references,
        key=lambda item: item["position"],
    )

    first_reference = sorted_references[0]
    last_reference = sorted_references[-1]

    # Caso a família tenha espessura praticamente nula nessa direção.
    if abs(
        last_reference["position"]
        - first_reference["position"]
    ) <= POSITION_TOLERANCE:

        return [first_reference]

    return [
        first_reference,
        last_reference,
    ]


def get_family_instance_dimension_references(
    family_instance,
    view,
):
    """
    Obtém referências de portas, janelas e pilares.

    Prioridade:

    1. Referências nomeadas da família.
    2. Faces geométricas extremas como fallback.

    Faces geométricas internas não são utilizadas.
    """

    result = {
        REFERENCE_HORIZONTAL: [],
        REFERENCE_VERTICAL: [],
    }

    if not isinstance(family_instance, FamilyInstance):
        return result

    # ------------------------------------------------------------------
    # REFERÊNCIAS NOMEADAS
    # ------------------------------------------------------------------

    named_references = collect_named_family_references(
        family_instance=family_instance,
        view=view,
    )

    horizontal_named = named_references.get(
        REFERENCE_HORIZONTAL,
        [],
    )

    vertical_named = named_references.get(
        REFERENCE_VERTICAL,
        [],
    )

    if horizontal_named:

        result[REFERENCE_HORIZONTAL].extend(
            horizontal_named
        )

    if vertical_named:

        result[REFERENCE_VERTICAL].extend(
            vertical_named
        )

    # ------------------------------------------------------------------
    # FALLBACK GEOMÉTRICO
    # ------------------------------------------------------------------

    # A geometria só é processada se alguma direção não possuir
    # referências nomeadas.
    if not horizontal_named or not vertical_named:

        geometry_references = classify_element_faces(
            element=family_instance,
            view=view,
        )

        if not horizontal_named:

            horizontal_extremes = select_extreme_references(
                geometry_references.get(
                    REFERENCE_HORIZONTAL,
                    [],
                )
            )

            result[REFERENCE_HORIZONTAL].extend(
                horizontal_extremes
            )

        if not vertical_named:

            vertical_extremes = select_extreme_references(
                geometry_references.get(
                    REFERENCE_VERTICAL,
                    [],
                )
            )

            result[REFERENCE_VERTICAL].extend(
                vertical_extremes
            )

    # ------------------------------------------------------------------
    # REMOÇÃO DE DUPLICIDADES
    # ------------------------------------------------------------------

    document = family_instance.Document

    result[REFERENCE_HORIZONTAL] = (
        remove_duplicate_references(
            reference_data=result[REFERENCE_HORIZONTAL],
            document=document,
        )
    )

    result[REFERENCE_VERTICAL] = (
        remove_duplicate_references(
            reference_data=result[REFERENCE_VERTICAL],
            document=document,
        )
    )

    return result

# ----------------------------------------------------------------------
# REFERÊNCIAS DE EIXOS
# ----------------------------------------------------------------------

def get_grid_reference(grid, view):
    """
    Obtém a referência e a posição de um eixo.
    """

    if not isinstance(grid, Grid):
        return None

    try:
        curve = grid.Curve
    except Exception:
        curve = None

    if curve is None:
        return None

    curve_orientation = geometry.classify_curve(
        curve=curve,
        view=view,
    )

    try:
        reference = Reference(grid)
    except Exception:
        reference = None

    if reference is None:
        return None

    try:
        start_point = curve.GetEndPoint(0)
        end_point = curve.GetEndPoint(1)

        midpoint = XYZ(
            (start_point.X + end_point.X) / 2.0,
            (start_point.Y + end_point.Y) / 2.0,
            (start_point.Z + end_point.Z) / 2.0,
        )
    except Exception:
        return None

    u, v, unused_w = geometry.project_point_to_view(
        midpoint,
        view,
    )

    # Eixo vertical é medido por uma cota horizontal.
    if curve_orientation == geometry.ORIENTATION_VERTICAL:

        orientation = REFERENCE_HORIZONTAL
        position = u

    # Eixo horizontal é medido por uma cota vertical.
    elif curve_orientation == geometry.ORIENTATION_HORIZONTAL:

        orientation = REFERENCE_VERTICAL
        position = v

    else:
        return None

    return {
        "reference": reference,
        "position": position,
        "origin": midpoint,
        "normal": None,
        "element": grid,
        "element_id": grid.Id,
        "source": "grid",
        "orientation": orientation,
    }


# ----------------------------------------------------------------------
# REFERÊNCIAS POR ELEMENTO
# ----------------------------------------------------------------------

def get_element_dimension_references(element, view):
    """
    Obtém referências conforme o tipo do elemento.
    """

    result = {
        REFERENCE_HORIZONTAL: [],
        REFERENCE_VERTICAL: [],
    }

    if element is None:
        return result

    # --------------------------------------------------------------
    # EIXOS
    # --------------------------------------------------------------

    if isinstance(element, Grid):

        grid_data = get_grid_reference(
            grid=element,
            view=view,
        )

        if grid_data is None:
            return result

        orientation = grid_data["orientation"]
        result[orientation].append(grid_data)

        return result

    # --------------------------------------------------------------
    # PAREDES
    # --------------------------------------------------------------

    if is_category(
        element,
        BuiltInCategory.OST_Walls,
    ):
        return get_wall_side_references(
            wall=element,
            view=view,
        )

    # --------------------------------------------------------------
    # PORTAS, JANELAS E PILARES
    # --------------------------------------------------------------

    if isinstance(element, FamilyInstance):
        return get_family_instance_dimension_references(
            family_instance=element,
            view=view,
        )

    # --------------------------------------------------------------
    # OUTROS ELEMENTOS
    # --------------------------------------------------------------

    return classify_element_faces(
        element=element,
        view=view,
    )


# ----------------------------------------------------------------------
# ORDENAÇÃO E LIMPEZA
# ----------------------------------------------------------------------

def sort_references(reference_data):
    """
    Ordena as referências pela posição na vista.
    """

    return sorted(
        reference_data,
        key=lambda item: item.get("position", 0.0),
    )


def remove_references_at_same_position(
    reference_data,
    tolerance=POSITION_TOLERANCE,
):
    """
    Remove referências coincidentes geometricamente.

    Mantém somente uma referência em cada coordenada para impedir segmentos
    de dimensão com comprimento zero.
    """

    if not reference_data:
        return []

    sorted_data = sort_references(reference_data)

    cleaned_references = []
    previous_position = None

    for item in sorted_data:

        position = item.get("position")

        if position is None:
            continue

        if previous_position is None:

            cleaned_references.append(item)
            previous_position = position
            continue

        if abs(position - previous_position) <= tolerance:
            continue

        cleaned_references.append(item)
        previous_position = position

    return cleaned_references


def prepare_reference_data(
    reference_data,
    document,
):
    """
    Prepara as referências para criação da dimensão.

    Etapas:

    1. Remove referências idênticas.
    2. Ordena pela posição.
    3. Remove referências na mesma coordenada.
    """

    result = remove_duplicate_references(
        reference_data=reference_data,
        document=document,
    )

    result = sort_references(result)

    result = remove_references_at_same_position(
        reference_data=result,
    )

    return result


# ----------------------------------------------------------------------
# COLETA COMPLETA ORGANIZADA POR CATEGORIA
# ----------------------------------------------------------------------

REFERENCE_CATEGORIES = (
    "walls",
    "doors",
    "windows",
    "columns",
    "grids",
)


def create_empty_reference_group():
    """
    Cria a estrutura padrão de referências para uma categoria.

    Returns:
        dict:
            Estrutura com listas horizontais e verticais.
    """

    return {
        REFERENCE_HORIZONTAL: [],
        REFERENCE_VERTICAL: [],
    }


def get_document_from_element_groups(element_groups):
    """
    Obtém o documento a partir do primeiro elemento válido encontrado.

    Args:
        element_groups (dict or list):
            Grupos retornados pelo collector.py ou uma lista de elementos.

    Returns:
        Document or None:
            Documento do Revit.
    """

    if element_groups is None:
        return None

    if isinstance(element_groups, dict):

        for category_name in element_groups:

            elements = element_groups.get(category_name, [])

            for element in elements:

                if element is None:
                    continue

                try:
                    return element.Document
                except Exception:
                    continue

        return None

    for element in element_groups:

        if element is None:
            continue

        try:
            return element.Document
        except Exception:
            continue

    return None


def collect_category_references(
    elements,
    view,
    document,
):
    """
    Coleta e prepara as referências de uma única categoria.

    Args:
        elements (list):
            Elementos pertencentes à categoria.

        view (View):
            Vista ativa.

        document (Document):
            Documento atual.

    Returns:
        dict:
            Referências horizontais e verticais da categoria.
    """

    result = create_empty_reference_group()

    if not elements:
        return result

    for element in elements:

        if element is None:
            continue

        element_references = get_element_dimension_references(
            element=element,
            view=view,
        )

        result[REFERENCE_HORIZONTAL].extend(
            element_references.get(
                REFERENCE_HORIZONTAL,
                [],
            )
        )

        result[REFERENCE_VERTICAL].extend(
            element_references.get(
                REFERENCE_VERTICAL,
                [],
            )
        )

    result[REFERENCE_HORIZONTAL] = prepare_reference_data(
        reference_data=result[REFERENCE_HORIZONTAL],
        document=document,
    )

    result[REFERENCE_VERTICAL] = prepare_reference_data(
        reference_data=result[REFERENCE_VERTICAL],
        document=document,
    )

    return result


def combine_grouped_references(
    grouped_references,
    document,
    category_names=None,
):
    """
    Combina referências de várias categorias.

    Essa função é útil para:

    - gerar uma cota geral;
    - manter compatibilidade com o script de teste anterior;
    - combinar paredes, portas e janelas em uma mesma linha.

    Args:
        grouped_references (dict):
            Referências organizadas por categoria.

        document (Document):
            Documento atual.

        category_names (list or tuple or None):
            Categorias que serão combinadas. Quando None, combina todas
            as categorias conhecidas.

    Returns:
        dict:
            Referências horizontais e verticais combinadas.
    """

    result = create_empty_reference_group()

    if not grouped_references:
        return result

    if category_names is None:
        category_names = REFERENCE_CATEGORIES

    for category_name in category_names:

        category_data = grouped_references.get(category_name)

        if not isinstance(category_data, dict):
            continue

        result[REFERENCE_HORIZONTAL].extend(
            category_data.get(
                REFERENCE_HORIZONTAL,
                [],
            )
        )

        result[REFERENCE_VERTICAL].extend(
            category_data.get(
                REFERENCE_VERTICAL,
                [],
            )
        )

    result[REFERENCE_HORIZONTAL] = prepare_reference_data(
        reference_data=result[REFERENCE_HORIZONTAL],
        document=document,
    )

    result[REFERENCE_VERTICAL] = prepare_reference_data(
        reference_data=result[REFERENCE_VERTICAL],
        document=document,
    )

    return result


def collect_dimension_references(element_groups, view):
    """
    Coleta as referências da planta e organiza o resultado por categoria.

    Estrutura retornada:

        {
            "walls": {
                "horizontal": [...],
                "vertical": [...]
            },
            "doors": {
                "horizontal": [...],
                "vertical": [...]
            },
            "windows": {
                "horizontal": [...],
                "vertical": [...]
            },
            "columns": {
                "horizontal": [...],
                "vertical": [...]
            },
            "grids": {
                "horizontal": [...],
                "vertical": [...]
            },

            # Agregados mantidos para compatibilidade:
            "horizontal": [...],
            "vertical": [...]
        }

    As chaves horizontais e verticais no nível principal permitem que o
    script de teste anterior continue funcionando. Os próximos módulos
    devem preferir os grupos por categoria.
    """

    grouped_result = {}

    for category_name in REFERENCE_CATEGORIES:
        grouped_result[category_name] = create_empty_reference_group()

    if element_groups is None:
        grouped_result[REFERENCE_HORIZONTAL] = []
        grouped_result[REFERENCE_VERTICAL] = []
        return grouped_result

    document = get_document_from_element_groups(
        element_groups
    )

    if isinstance(element_groups, dict):

        for category_name in REFERENCE_CATEGORIES:

            category_elements = element_groups.get(
                category_name,
                [],
            )

            grouped_result[category_name] = (
                collect_category_references(
                    elements=category_elements,
                    view=view,
                    document=document,
                )
            )

    else:
        # Compatibilidade com chamadas que forneçam uma lista simples.
        grouped_result["others"] = collect_category_references(
            elements=element_groups,
            view=view,
            document=document,
        )

    combined = combine_grouped_references(
        grouped_references=grouped_result,
        document=document,
    )

    # Compatibilidade com o formato antigo.
    grouped_result[REFERENCE_HORIZONTAL] = combined[
        REFERENCE_HORIZONTAL
    ]

    grouped_result[REFERENCE_VERTICAL] = combined[
        REFERENCE_VERTICAL
    ]

    return grouped_result


def get_reference_group(
    grouped_references,
    category_name,
):
    """
    Retorna o grupo de uma categoria com estrutura segura.

    Args:
        grouped_references (dict):
            Resultado de collect_dimension_references().

        category_name (str):
            Nome da categoria.

    Returns:
        dict:
            Referências horizontais e verticais.
    """

    if not grouped_references:
        return create_empty_reference_group()

    category_data = grouped_references.get(category_name)

    if not isinstance(category_data, dict):
        return create_empty_reference_group()

    return {
        REFERENCE_HORIZONTAL: category_data.get(
            REFERENCE_HORIZONTAL,
            [],
        ),
        REFERENCE_VERTICAL: category_data.get(
            REFERENCE_VERTICAL,
            [],
        ),
    }


def get_reference_summary(grouped_references):
    """
    Retorna a quantidade de referências por categoria e orientação.

    Args:
        grouped_references (dict):
            Resultado de collect_dimension_references().

    Returns:
        dict:
            Resumo numérico por categoria.
    """

    summary = {}

    for category_name in REFERENCE_CATEGORIES:

        category_data = get_reference_group(
            grouped_references,
            category_name,
        )

        horizontal_count = len(
            category_data[REFERENCE_HORIZONTAL]
        )

        vertical_count = len(
            category_data[REFERENCE_VERTICAL]
        )

        summary[category_name] = {
            REFERENCE_HORIZONTAL: horizontal_count,
            REFERENCE_VERTICAL: vertical_count,
            "total": horizontal_count + vertical_count,
        }

    summary["all"] = {
        REFERENCE_HORIZONTAL: len(
            grouped_references.get(
                REFERENCE_HORIZONTAL,
                [],
            )
        ),
        REFERENCE_VERTICAL: len(
            grouped_references.get(
                REFERENCE_VERTICAL,
                [],
            )
        ),
    }

    summary["all"]["total"] = (
        summary["all"][REFERENCE_HORIZONTAL]
        + summary["all"][REFERENCE_VERTICAL]
    )

    return summary


# ----------------------------------------------------------------------
# EXTRAÇÃO DOS OBJETOS REFERENCE
# ----------------------------------------------------------------------

def get_raw_references(reference_data):
    """
    Retorna somente os objetos Reference.
    """

    raw_references = []

    for item in reference_data:

        if item is None:
            continue

        reference = item.get("reference")

        if reference is not None:
            raw_references.append(reference)

    return raw_references