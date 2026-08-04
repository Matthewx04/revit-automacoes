# -*- coding: utf-8 -*-
"""
dimension.py

Responsável por:

1. Converter dados de referências em ReferenceArray.
2. Validar referências e linhas de dimensão.
3. Criar cotas lineares horizontais e verticais.
4. Criar cotas por categoria.
5. Criar cotas combinando várias categorias.
6. Controlar transações de criação de dimensões.

Compatível com pyRevit, IronPython e versões recentes do Revit.
"""

from Autodesk.Revit.DB import (
    DimensionType,
    Line,
    Reference,
    ReferenceArray,
    Transaction,
)

import references


# ----------------------------------------------------------------------
# CONSTANTES
# ----------------------------------------------------------------------

MINIMUM_REFERENCE_COUNT = 2

DIMENSION_HORIZONTAL = references.REFERENCE_HORIZONTAL
DIMENSION_VERTICAL = references.REFERENCE_VERTICAL


# ----------------------------------------------------------------------
# VALIDAÇÕES
# ----------------------------------------------------------------------

def validate_document(doc):
    """
    Verifica se o documento foi informado.
    """

    if doc is None:
        raise ValueError(
            "O documento do Revit não foi informado."
        )

    return True


def validate_view(view):
    """
    Verifica se a vista foi informada e se não é um template.
    """

    if view is None:
        raise ValueError(
            "A vista da dimensão não foi informada."
        )

    try:
        if view.IsTemplate:
            raise ValueError(
                "Não é possível criar dimensões em um template de vista."
            )
    except AttributeError:
        pass

    return True


def validate_dimension_line(dimension_line):
    """
    Valida a linha usada para posicionar a dimensão.

    Args:
        dimension_line (Line):
            Linha de dimensão.

    Returns:
        bool:
            True quando válida.
    """

    if dimension_line is None:
        raise ValueError(
            "A linha de dimensão não foi informada."
        )

    if not isinstance(dimension_line, Line):
        raise TypeError(
            "A linha de dimensão precisa ser um objeto Line."
        )

    try:
        length = dimension_line.Length
    except Exception:
        length = 0.0

    if length <= 0.0:
        raise ValueError(
            "A linha de dimensão possui comprimento inválido."
        )

    return True


def validate_orientation(orientation):
    """
    Verifica se a orientação é horizontal ou vertical.
    """

    valid_orientations = (
        DIMENSION_HORIZONTAL,
        DIMENSION_VERTICAL,
    )

    if orientation not in valid_orientations:
        raise ValueError(
            "Orientação de dimensão inválida: {0}".format(
                orientation
            )
        )

    return True


def validate_dimension_type(dimension_type):
    """
    Valida um tipo de dimensão opcional.
    """

    if dimension_type is None:
        return True

    if not isinstance(dimension_type, DimensionType):
        raise TypeError(
            "O tipo de dimensão informado não é um DimensionType."
        )

    return True


# ----------------------------------------------------------------------
# REFERÊNCIAS
# ----------------------------------------------------------------------

def extract_reference(item):
    """
    Extrai um objeto Reference.

    Aceita:

    - um objeto Reference diretamente;
    - um dicionário retornado pelo references.py.

    Args:
        item (Reference or dict):
            Item analisado.

    Returns:
        Reference or None:
            Referência encontrada.
    """

    if item is None:
        return None

    if isinstance(item, Reference):
        return item

    if isinstance(item, dict):

        reference = item.get("reference")

        if isinstance(reference, Reference):
            return reference

    return None


def create_reference_array(reference_data):
    """
    Cria um ReferenceArray a partir dos dados do references.py.

    Args:
        reference_data (list):
            Lista de referências ou dicionários com a chave "reference".

    Returns:
        ReferenceArray:
            Array pronto para NewDimension().

    Raises:
        ValueError:
            Quando existem menos de duas referências válidas.
    """

    reference_array = ReferenceArray()
    valid_count = 0

    if not reference_data:
        raise ValueError(
            "Nenhuma referência foi fornecida para a dimensão."
        )

    for item in reference_data:

        reference = extract_reference(item)

        if reference is None:
            continue

        reference_array.Append(reference)
        valid_count += 1

    if valid_count < MINIMUM_REFERENCE_COUNT:
        raise ValueError(
            "São necessárias pelo menos duas referências válidas "
            "para criar uma dimensão. Foram encontradas: {0}.".format(
                valid_count
            )
        )

    return reference_array


def count_valid_references(reference_data):
    """
    Conta quantas referências válidas existem em uma lista.
    """

    if not reference_data:
        return 0

    count = 0

    for item in reference_data:

        if extract_reference(item) is not None:
            count += 1

    return count


def can_create_dimension(reference_data):
    """
    Informa se uma lista possui referências suficientes.
    """

    return (
        count_valid_references(reference_data)
        >= MINIMUM_REFERENCE_COUNT
    )


# ----------------------------------------------------------------------
# CRIAÇÃO DE DIMENSÃO
# ----------------------------------------------------------------------

def create_dimension(
    doc,
    view,
    dimension_line,
    reference_data,
    dimension_type=None,
):
    """
    Cria uma dimensão linear.

    Esta função pressupõe que já existe uma Transaction aberta.

    Args:
        doc (Document):
            Documento atual.

        view (View):
            Vista em que a dimensão será criada.

        dimension_line (Line):
            Linha que controla a posição e a direção da dimensão.

        reference_data (list):
            Dados das referências.

        dimension_type (DimensionType or None):
            Tipo de dimensão opcional. Quando None, o Revit usa o tipo
            padrão atualmente configurado.

    Returns:
        Dimension:
            Dimensão criada.

    Raises:
        ValueError:
            Quando a dimensão não puder ser criada.
    """

    validate_document(doc)
    validate_view(view)
    validate_dimension_line(dimension_line)
    validate_dimension_type(dimension_type)

    reference_array = create_reference_array(
        reference_data
    )

    try:

        if dimension_type is None:

            created_dimension = doc.Create.NewDimension(
                view,
                dimension_line,
                reference_array,
            )

        else:

            created_dimension = doc.Create.NewDimension(
                view,
                dimension_line,
                reference_array,
                dimension_type,
            )

    except Exception as error:

        raise ValueError(
            "O Revit não conseguiu criar a dimensão.\n\n"
            "Detalhes: {0}".format(error)
        )

    if created_dimension is None:
        raise ValueError(
            "O método NewDimension retornou um resultado nulo."
        )

    return created_dimension


def create_dimension_in_transaction(
    doc,
    view,
    dimension_line,
    reference_data,
    dimension_type=None,
    transaction_name="Criar dimensão",
):
    """
    Cria uma única dimensão dentro de uma Transaction própria.

    Para criar várias dimensões de uma vez, prefira
    create_dimensions_in_transaction().
    """

    validate_document(doc)

    transaction = Transaction(
        doc,
        transaction_name,
    )

    try:
        transaction.Start()

        created_dimension = create_dimension(
            doc=doc,
            view=view,
            dimension_line=dimension_line,
            reference_data=reference_data,
            dimension_type=dimension_type,
        )

        transaction.Commit()

        return created_dimension

    except Exception:

        try:
            if transaction.HasStarted():
                transaction.RollBack()
        except Exception:
            pass

        raise


# ----------------------------------------------------------------------
# DADOS POR CATEGORIA
# ----------------------------------------------------------------------

def get_category_reference_data(
    grouped_references,
    category_name,
    orientation,
):
    """
    Obtém as referências de uma categoria e orientação.

    Args:
        grouped_references (dict):
            Resultado de references.collect_dimension_references().

        category_name (str):
            Nome da categoria, por exemplo "walls" ou "doors".

        orientation (str):
            horizontal ou vertical.

    Returns:
        list:
            Referências da categoria.
    """

    validate_orientation(orientation)

    if not grouped_references:
        return []

    category_data = grouped_references.get(
        category_name,
        {},
    )

    if not isinstance(category_data, dict):
        return []

    return category_data.get(
        orientation,
        [],
    )


def get_combined_reference_data(
    grouped_references,
    category_names,
    orientation,
):
    """
    Combina referências de várias categorias em uma orientação.

    O resultado passa novamente pela preparação do references.py para
    ordenar e remover posições coincidentes.

    Args:
        grouped_references (dict):
            Referências organizadas.

        category_names (list or tuple):
            Categorias que serão combinadas.

        orientation (str):
            horizontal ou vertical.

    Returns:
        list:
            Referências combinadas e preparadas.
    """

    validate_orientation(orientation)

    if not grouped_references:
        return []

    combined = []

    for category_name in category_names:

        category_references = get_category_reference_data(
            grouped_references=grouped_references,
            category_name=category_name,
            orientation=orientation,
        )

        combined.extend(category_references)

    document = None

    for item in combined:

        element = item.get("element") if isinstance(item, dict) else None

        if element is None:
            continue

        try:
            document = element.Document
            break
        except Exception:
            continue

    return references.prepare_reference_data(
        reference_data=combined,
        document=document,
    )


# ----------------------------------------------------------------------
# SOLICITAÇÕES DE DIMENSÃO
# ----------------------------------------------------------------------

def create_dimension_request(
    name,
    orientation,
    dimension_line,
    reference_data,
    dimension_type=None,
    category_name=None,
):
    """
    Cria uma estrutura que representa uma dimensão a ser criada.

    Args:
        name (str):
            Nome identificador da dimensão.

        orientation (str):
            horizontal ou vertical.

        dimension_line (Line):
            Linha de posicionamento.

        reference_data (list):
            Referências utilizadas.

        dimension_type (DimensionType or None):
            Tipo de dimensão opcional.

        category_name (str or None):
            Categoria associada.

    Returns:
        dict:
            Solicitação pronta para execução.
    """

    validate_orientation(orientation)

    return {
        "name": name,
        "orientation": orientation,
        "dimension_line": dimension_line,
        "reference_data": reference_data or [],
        "dimension_type": dimension_type,
        "category_name": category_name,
    }


def create_category_dimension_request(
    grouped_references,
    category_name,
    orientation,
    dimension_line,
    dimension_type=None,
    name=None,
):
    """
    Cria uma solicitação de dimensão para uma categoria.
    """

    reference_data = get_category_reference_data(
        grouped_references=grouped_references,
        category_name=category_name,
        orientation=orientation,
    )

    if name is None:
        name = "{0}_{1}".format(
            category_name,
            orientation,
        )

    return create_dimension_request(
        name=name,
        orientation=orientation,
        dimension_line=dimension_line,
        reference_data=reference_data,
        dimension_type=dimension_type,
        category_name=category_name,
    )


def create_combined_dimension_request(
    grouped_references,
    category_names,
    orientation,
    dimension_line,
    dimension_type=None,
    name=None,
):
    """
    Cria uma solicitação combinando várias categorias.
    """

    reference_data = get_combined_reference_data(
        grouped_references=grouped_references,
        category_names=category_names,
        orientation=orientation,
    )

    if name is None:
        name = "combined_{0}".format(
            orientation
        )

    return create_dimension_request(
        name=name,
        orientation=orientation,
        dimension_line=dimension_line,
        reference_data=reference_data,
        dimension_type=dimension_type,
        category_name=None,
    )


# ----------------------------------------------------------------------
# CRIAÇÃO EM LOTE
# ----------------------------------------------------------------------

def validate_dimension_request(request):
    """
    Valida uma solicitação antes da criação.
    """

    if not isinstance(request, dict):
        raise TypeError(
            "A solicitação de dimensão deve ser um dicionário."
        )

    dimension_line = request.get("dimension_line")
    reference_data = request.get("reference_data", [])
    orientation = request.get("orientation")
    dimension_type = request.get("dimension_type")

    validate_orientation(orientation)
    validate_dimension_line(dimension_line)
    validate_dimension_type(dimension_type)

    if not can_create_dimension(reference_data):
        raise ValueError(
            "A solicitação '{0}' não possui referências suficientes.".format(
                request.get("name", "sem nome")
            )
        )

    return True


def create_dimensions(
    doc,
    view,
    requests,
    skip_invalid=True,
):
    """
    Cria várias dimensões.

    Esta função pressupõe que já existe uma Transaction aberta.

    Args:
        doc (Document):
            Documento atual.

        view (View):
            Vista utilizada.

        requests (list[dict]):
            Solicitações criadas pelas funções deste módulo.

        skip_invalid (bool):
            Quando True, ignora solicitações inválidas e registra o erro.
            Quando False, interrompe a execução no primeiro erro.

    Returns:
        dict:
            Dimensões criadas, ignoradas e erros.
    """

    result = {
        "created": [],
        "skipped": [],
        "errors": [],
    }

    if not requests:
        return result

    for request in requests:

        request_name = "sem nome"

        if isinstance(request, dict):
            request_name = request.get(
                "name",
                "sem nome",
            )

        try:
            validate_dimension_request(request)

            created_dimension = create_dimension(
                doc=doc,
                view=view,
                dimension_line=request["dimension_line"],
                reference_data=request["reference_data"],
                dimension_type=request.get("dimension_type"),
            )

            result["created"].append({
                "name": request_name,
                "dimension": created_dimension,
                "request": request,
            })

        except Exception as error:

            error_data = {
                "name": request_name,
                "error": str(error),
                "request": request,
            }

            if skip_invalid:
                result["skipped"].append(error_data)
                continue

            result["errors"].append(error_data)
            raise

    return result


def create_dimensions_in_transaction(
    doc,
    view,
    requests,
    transaction_name="Dimensionar planta",
    skip_invalid=True,
):
    """
    Cria várias dimensões em uma única Transaction.

    Args:
        doc (Document):
            Documento atual.

        view (View):
            Vista utilizada.

        requests (list[dict]):
            Solicitações de dimensão.

        transaction_name (str):
            Nome exibido no histórico do Revit.

        skip_invalid (bool):
            Ignorar solicitações sem referências suficientes ou inválidas.

    Returns:
        dict:
            Resultado da criação.
    """

    validate_document(doc)
    validate_view(view)

    transaction = Transaction(
        doc,
        transaction_name,
    )

    try:
        transaction.Start()

        result = create_dimensions(
            doc=doc,
            view=view,
            requests=requests,
            skip_invalid=skip_invalid,
        )

        if not result["created"]:

            transaction.RollBack()

            result["transaction_committed"] = False
            result["transaction_message"] = (
                "Nenhuma dimensão válida foi criada."
            )

            return result

        transaction.Commit()

        result["transaction_committed"] = True
        result["transaction_message"] = (
            "Transação concluída com sucesso."
        )

        return result

    except Exception:

        try:
            if transaction.HasStarted():
                transaction.RollBack()
        except Exception:
            pass

        raise


# ----------------------------------------------------------------------
# RESUMO
# ----------------------------------------------------------------------

def get_creation_summary(result):
    """
    Retorna um resumo numérico do resultado da criação.
    """

    if not result:
        return {
            "created": 0,
            "skipped": 0,
            "errors": 0,
        }

    return {
        "created": len(result.get("created", [])),
        "skipped": len(result.get("skipped", [])),
        "errors": len(result.get("errors", [])),
    }
