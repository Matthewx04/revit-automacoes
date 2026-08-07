# -*- coding: utf-8 -*-

"""
annotations.py

Responsável pelas anotações visuais dos elementos
depois da renumeração.

Exemplo:

Marca do elemento:
    TP1-1

Anotação criada na vista:
    TP1-1

Configuração padrão:
    Fonte: Lexend Extra Light
    Altura: 2 mm

IMPORTANTE:
Este módulo NÃO:
- seleciona elementos;
- renumera elementos;
- inicia Transaction;
- abre formulários.

O script.py continua responsável por coordenar
essas operações.
"""

from pyrevit import DB


# ============================================================
# CONFIGURAÇÃO PADRÃO
# ============================================================

TEXT_TYPE_NAME = "Lexend Extra Light - 2mm"

FONT_NAME = "Lexend Extra Light"

TEXT_HEIGHT_MM = 2.0

# Distância visual entre o elemento e a anotação,
# medida em milímetros no papel.
OFFSET_MM = 3.0


# ============================================================
# RESULTADOS
# ============================================================

def create_result():

    return {
        "created": 0,
        "skipped": 0,
        "errors": [],
        "items": []
    }


def get_id_value(element_id):

    if element_id is None:
        return None

    try:
        return element_id.Value
    except Exception:
        pass

    try:
        return element_id.IntegerValue
    except Exception:
        return None


def add_error(
    result,
    element,
    message
):

    try:
        element_id = get_id_value(
            element.Id
        )
    except Exception:
        element_id = "?"

    result["errors"].append(
        "Elemento {}: {}".format(
            element_id,
            message
        )
    )


# ============================================================
# CONVERSÃO DE UNIDADES
# ============================================================

def mm_to_internal(mm):
    """
    Converte milímetros para unidade interna do Revit.

    Revit usa pés internamente.
    """

    try:

        return DB.UnitUtils.ConvertToInternalUnits(
            float(mm),
            DB.UnitTypeId.Millimeters
        )

    except Exception:

        # Compatibilidade com versões antigas
        try:

            return DB.UnitUtils.ConvertToInternalUnits(
                float(mm),
                DB.DisplayUnitType.DUT_MILLIMETERS
            )

        except Exception:

            # Conversão matemática de emergência
            return (
                float(mm)
                / 304.8
            )


def paper_mm_to_model_internal(
    mm,
    view
):
    """
    Converte uma distância visual em milímetros no papel
    para distância no modelo considerando a escala.

    Exemplo:

        offset = 3 mm

    Em 1:50:
        deslocamento real equivalente = 150 mm

    Em 1:100:
        deslocamento real equivalente = 300 mm
    """

    try:

        scale = view.Scale

        if not scale:
            scale = 1

    except Exception:

        scale = 1

    return (
        mm_to_internal(mm)
        * scale
    )


# ============================================================
# TEXT NOTE TYPE
# ============================================================

def get_text_note_types(doc):
    """
    Retorna todos os estilos de TextNote do projeto.
    """

    try:

        return list(
            DB.FilteredElementCollector(doc)
            .OfClass(DB.TextNoteType)
            .ToElements()
        )

    except Exception:

        return []


def get_text_type_name(text_type):
    """
    Retorna o nome de um TextNoteType.
    """

    try:

        return text_type.Name

    except Exception:
        pass

    try:

        parameter = text_type.get_Parameter(
            DB.BuiltInParameter.SYMBOL_NAME_PARAM
        )

        if parameter:

            value = parameter.AsString()

            if value:
                return value

    except Exception:
        pass

    return ""


def find_text_type(
    doc,
    type_name
):
    """
    Procura um TextNoteType pelo nome.
    """

    for text_type in get_text_note_types(doc):

        if (
            get_text_type_name(text_type)
            == type_name
        ):

            return text_type

    return None


# ============================================================
# CONFIGURAÇÃO DO ESTILO
# ============================================================

def configure_text_type(
    text_type,
    font_name=FONT_NAME,
    height_mm=TEXT_HEIGHT_MM
):
    """
    Configura fonte e tamanho do estilo.

    Retorna True quando a configuração principal
    pôde ser aplicada.
    """

    if text_type is None:
        return False

    success = True


    # --------------------------------------------------------
    # FONTE
    # --------------------------------------------------------

    try:

        font_parameter = (
            text_type.get_Parameter(
                DB.BuiltInParameter.TEXT_FONT
            )
        )

        if (
            font_parameter
            and not font_parameter.IsReadOnly
        ):

            font_parameter.Set(
                str(font_name)
            )

        else:

            success = False

    except Exception:

        success = False


    # --------------------------------------------------------
    # TAMANHO
    # --------------------------------------------------------

    try:

        size_parameter = (
            text_type.get_Parameter(
                DB.BuiltInParameter.TEXT_SIZE
            )
        )

        if (
            size_parameter
            and not size_parameter.IsReadOnly
        ):

            size_parameter.Set(
                mm_to_internal(
                    height_mm
                )
            )

        else:

            success = False

    except Exception:

        success = False


    # --------------------------------------------------------
    # SEM NEGRITO
    # --------------------------------------------------------

    try:

        bold_parameter = (
            text_type.get_Parameter(
                DB.BuiltInParameter.TEXT_STYLE_BOLD
            )
        )

        if (
            bold_parameter
            and not bold_parameter.IsReadOnly
        ):

            bold_parameter.Set(0)

    except Exception:
        pass


    # --------------------------------------------------------
    # SEM ITÁLICO
    # --------------------------------------------------------

    try:

        italic_parameter = (
            text_type.get_Parameter(
                DB.BuiltInParameter.TEXT_STYLE_ITALIC
            )
        )

        if (
            italic_parameter
            and not italic_parameter.IsReadOnly
        ):

            italic_parameter.Set(0)

    except Exception:
        pass


    # --------------------------------------------------------
    # SEM SUBLINHADO
    # --------------------------------------------------------

    try:

        underline_parameter = (
            text_type.get_Parameter(
                DB.BuiltInParameter.TEXT_STYLE_UNDERLINE
            )
        )

        if (
            underline_parameter
            and not underline_parameter.IsReadOnly
        ):

            underline_parameter.Set(0)

    except Exception:
        pass


    return success


# ============================================================
# CRIAR / OBTER ESTILO
# ============================================================

def ensure_text_type(
    doc,
    type_name=TEXT_TYPE_NAME,
    font_name=FONT_NAME,
    height_mm=TEXT_HEIGHT_MM
):
    """
    Procura o estilo:

        Lexend Extra Light - 2mm

    Se não existir:
        duplica um TextNoteType existente.

    Depois configura:
        fonte;
        tamanho;
        negrito;
        itálico;
        sublinhado.

    IMPORTANTE:
    deve ser chamada dentro de Transaction.
    """

    existing = find_text_type(
        doc,
        type_name
    )

    if existing:

        configure_text_type(
            existing,
            font_name=font_name,
            height_mm=height_mm
        )

        return existing


    # --------------------------------------------------------
    # ESTILO BASE
    # --------------------------------------------------------

    existing_types = get_text_note_types(
        doc
    )

    if not existing_types:

        return None

    base_type = existing_types[0]


    # --------------------------------------------------------
    # DUPLICAR
    # --------------------------------------------------------

    try:

        new_type = base_type.Duplicate(
            type_name
        )

    except Exception:

        return None


    # --------------------------------------------------------
    # CONFIGURAR
    # --------------------------------------------------------

    configure_text_type(
        new_type,
        font_name=font_name,
        height_mm=height_mm
    )

    return new_type


# ============================================================
# TEXTO DO ELEMENTO
# ============================================================

def get_parameter_text(
    element,
    parameter_name="Marca"
):
    """
    Obtém o texto do parâmetro que será mostrado.

    Por padrão:
        Marca

    Exemplos:
        TP1-1
        TP1-2
        PX-1
    """

    if element is None:
        return None

    try:

        parameter = element.LookupParameter(
            parameter_name
        )

    except Exception:

        parameter = None

    if parameter is None:
        return None


    # --------------------------------------------------------
    # STRING
    # --------------------------------------------------------

    try:

        value = parameter.AsString()

        if value:

            value = value.strip()

            if value:
                return value

    except Exception:
        pass


    # --------------------------------------------------------
    # FALLBACK
    # --------------------------------------------------------

    try:

        value = parameter.AsValueString()

        if value:

            value = value.strip()

            if value:
                return value

    except Exception:
        pass

    return None


# ============================================================
# PONTO DO ELEMENTO
# ============================================================

def get_element_point(
    element,
    view=None
):
    """
    Retorna um ponto representativo do elemento.

    Prioridade:

    1. LocationPoint
    2. LocationCurve
    3. centro da BoundingBox
    """

    if element is None:
        return None


    # --------------------------------------------------------
    # LOCATION POINT
    # --------------------------------------------------------

    try:

        location = element.Location

        if isinstance(
            location,
            DB.LocationPoint
        ):

            return location.Point

    except Exception:
        pass


    # --------------------------------------------------------
    # LOCATION CURVE
    # --------------------------------------------------------

    try:

        location = element.Location

        if isinstance(
            location,
            DB.LocationCurve
        ):

            curve = location.Curve

            return curve.Evaluate(
                0.5,
                True
            )

    except Exception:
        pass


    # --------------------------------------------------------
    # BOUNDING BOX
    # --------------------------------------------------------

    try:

        bbox = element.get_BoundingBox(
            view
        )

        if bbox is None:

            bbox = element.get_BoundingBox(
                None
            )

        if bbox is None:
            return None

        local_center = DB.XYZ(
            (
                bbox.Min.X
                + bbox.Max.X
            ) / 2.0,

            (
                bbox.Min.Y
                + bbox.Max.Y
            ) / 2.0,

            (
                bbox.Min.Z
                + bbox.Max.Z
            ) / 2.0
        )

        try:

            return bbox.Transform.OfPoint(
                local_center
            )

        except Exception:

            return local_center

    except Exception:

        return None


# ============================================================
# CANTOS DA BOUNDING BOX
# ============================================================

def get_bbox_corners(
    element,
    view
):
    """
    Retorna os oito cantos da BoundingBox
    em coordenadas do modelo.
    """

    try:

        bbox = element.get_BoundingBox(
            view
        )

        if bbox is None:

            bbox = element.get_BoundingBox(
                None
            )

    except Exception:

        bbox = None

    if bbox is None:
        return []

    min_pt = bbox.Min
    max_pt = bbox.Max

    local_points = [
        DB.XYZ(min_pt.X, min_pt.Y, min_pt.Z),
        DB.XYZ(max_pt.X, min_pt.Y, min_pt.Z),
        DB.XYZ(min_pt.X, max_pt.Y, min_pt.Z),
        DB.XYZ(max_pt.X, max_pt.Y, min_pt.Z),

        DB.XYZ(min_pt.X, min_pt.Y, max_pt.Z),
        DB.XYZ(max_pt.X, min_pt.Y, max_pt.Z),
        DB.XYZ(min_pt.X, max_pt.Y, max_pt.Z),
        DB.XYZ(max_pt.X, max_pt.Y, max_pt.Z)
    ]

    points = []

    for point in local_points:

        try:

            world_point = (
                bbox.Transform.OfPoint(
                    point
                )
            )

        except Exception:

            world_point = point

        points.append(
            world_point
        )

    return points


# ============================================================
# POSIÇÃO DA ANOTAÇÃO
# ============================================================

def get_annotation_position(
    element,
    view,
    offset_mm=OFFSET_MM
):
    """
    Calcula uma posição à direita do elemento,
    respeitando a orientação da vista.

    Isso é mais robusto que simplesmente usar:

        bbox.Max.X

    pois também funciona melhor quando a vista
    não está alinhada com o eixo X global.
    """

    center = get_element_point(
        element,
        view
    )

    if center is None:
        return None


    # --------------------------------------------------------
    # DIREÇÃO PARA A DIREITA DA VISTA
    # --------------------------------------------------------

    try:

        right_direction = (
            view.RightDirection.Normalize()
        )

    except Exception:

        right_direction = DB.XYZ.BasisX


    # --------------------------------------------------------
    # OFFSET NO MODELO
    # --------------------------------------------------------

    offset = paper_mm_to_model_internal(
        offset_mm,
        view
    )


    # --------------------------------------------------------
    # TENTAR USAR A BORDA DO ELEMENTO
    # --------------------------------------------------------

    corners = get_bbox_corners(
        element,
        view
    )

    if corners:

        try:

            center_projection = (
                center.DotProduct(
                    right_direction
                )
            )

            max_projection = max(
                point.DotProduct(
                    right_direction
                )
                for point in corners
            )

            half_width = (
                max_projection
                - center_projection
            )

            if half_width < 0:
                half_width = 0

            distance = (
                half_width
                + offset
            )

            return (
                center
                + right_direction.Multiply(
                    distance
                )
            )

        except Exception:
            pass


    # --------------------------------------------------------
    # FALLBACK
    # --------------------------------------------------------

    return (
        center
        + right_direction.Multiply(
            offset
        )
    )


# ============================================================
# VERIFICAR VISTA
# ============================================================

def can_create_text_notes(view):
    """
    Faz uma validação básica da vista.

    TextNotes não são adequadas para alguns
    tipos de vista.
    """

    if view is None:
        return False

    try:

        if view.IsTemplate:
            return False

    except Exception:
        pass

    try:

        view_type = view.ViewType

        blocked_types = [
            DB.ViewType.Schedule,
            DB.ViewType.DrawingSheet,
            DB.ViewType.Report,
            DB.ViewType.ProjectBrowser,
            DB.ViewType.SystemBrowser
        ]

        if view_type in blocked_types:
            return False

    except Exception:
        pass

    return True


# ============================================================
# CRIAR UMA ANOTAÇÃO
# ============================================================

def create_annotation(
    doc,
    view,
    element,
    text,
    text_type_id,
    offset_mm=OFFSET_MM
):
    """
    Cria uma TextNote para um único elemento.

    Retorna:
        TextNote ou None
    """

    if not text:
        return None

    position = get_annotation_position(
        element,
        view,
        offset_mm=offset_mm
    )

    if position is None:
        return None

    try:

        return DB.TextNote.Create(
            doc,
            view.Id,
            position,
            str(text),
            text_type_id
        )

    except Exception:

        return None


# ============================================================
# ANOTAR ELEMENTOS
# ============================================================

def annotate_elements(
    doc,
    view,
    elements,
    parameter_name="Marca",
    text_type=None,
    offset_mm=OFFSET_MM
):
    """
    Cria uma anotação para cada elemento.

    O texto é lido do parâmetro informado.

    Padrão:
        Marca

    Exemplo:

        Marca = TP1-1
        anotação = TP1-1

    IMPORTANTE:
    esta função deve ser chamada dentro
    de uma Transaction.
    """

    result = create_result()

    if not elements:
        return result

    if not can_create_text_notes(
        view
    ):

        result["errors"].append(
            "A vista ativa não aceita as anotações deste tipo."
        )

        return result


    # --------------------------------------------------------
    # ESTILO
    # --------------------------------------------------------

    if text_type is None:

        text_type = ensure_text_type(
            doc
        )

    if text_type is None:

        result["errors"].append(
            (
                "Não foi possível encontrar ou criar "
                "o estilo de texto '{}'."
            ).format(
                TEXT_TYPE_NAME
            )
        )

        return result

    text_type_id = text_type.Id


    # --------------------------------------------------------
    # ELEMENTOS
    # --------------------------------------------------------

    for element in elements:

        text = get_parameter_text(
            element,
            parameter_name
        )

        if not text:

            result["skipped"] += 1

            add_error(
                result,
                element,
                (
                    "o parâmetro '{}' está vazio "
                    "ou não existe."
                ).format(
                    parameter_name
                )
            )

            continue


        annotation = create_annotation(
            doc=doc,
            view=view,
            element=element,
            text=text,
            text_type_id=text_type_id,
            offset_mm=offset_mm
        )


        if annotation is None:

            result["skipped"] += 1

            add_error(
                result,
                element,
                "não foi possível criar a anotação."
            )

            continue


        result["created"] += 1

        result["items"].append({
            "element": element,
            "element_id": element.Id,
            "annotation": annotation,
            "annotation_id": annotation.Id,
            "text": text
        })


    return result