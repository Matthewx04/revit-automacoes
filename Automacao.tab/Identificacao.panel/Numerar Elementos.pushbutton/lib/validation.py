# -*- coding: utf-8 -*-

"""
validation.py

Responsável por validar os elementos antes da renumeração.

Este módulo NÃO:
- seleciona elementos;
- ordena elementos;
- altera parâmetros;
- abre formulários;
- inicia transações.

Ele apenas verifica se os elementos podem seguir
para as próximas etapas do plugin.
"""

from pyrevit import DB


def get_element_id_value(element):
    """
    Retorna o Id do elemento de forma segura.
    """

    try:
        return element.Id.IntegerValue
    except Exception:
        return "?"


def has_valid_category(element):
    """
    Verifica se o elemento possui uma categoria válida.
    """

    try:
        return element.Category is not None
    except Exception:
        return False


def has_valid_location(element):
    """
    Verifica se o elemento possui uma localização que
    possa ser utilizada para ordenação.

    Aceita:
    - LocationPoint
    - LocationCurve

    Caso contrário, ainda considera válido se possuir
    uma BoundingBox utilizável.
    """

    try:
        location = element.Location

        if isinstance(location, DB.LocationPoint):
            return True

        if isinstance(location, DB.LocationCurve):
            return True

    except Exception:
        pass

    # fallback:
    # alguns elementos não possuem LocationPoint/LocationCurve,
    # mas ainda possuem BoundingBox.
    try:
        bbox = element.get_BoundingBox(None)

        if bbox is not None:
            return True

    except Exception:
        pass

    return False


def has_valid_type(element):
    """
    Verifica se o elemento possui um tipo válido.

    Importante principalmente quando desejarmos
    trabalhar com parâmetros de tipo.
    """

    try:
        type_id = element.GetTypeId()

        if type_id == DB.ElementId.InvalidElementId:
            return False

        return True

    except Exception:
        return False


def validate_element(element):
    """
    Faz validações básicas em um único elemento.

    Retorna:

    {
        "valid": True/False,
        "element": element,
        "errors": [],
        "warnings": []
    }
    """

    result = {
        "valid": True,
        "element": element,
        "errors": [],
        "warnings": []
    }

    if element is None:
        result["valid"] = False
        result["errors"].append(
            "Elemento inválido ou inexistente."
        )
        return result

    if not has_valid_category(element):
        result["warnings"].append(
            "Elemento sem categoria definida."
        )

    if not has_valid_location(element):
        result["valid"] = False
        result["errors"].append(
            "Elemento sem localização válida para ordenação."
        )

    return result


def validate_elements(elements):
    """
    Valida uma lista de elementos.

    Mantém compatibilidade com o script.py atual,
    retornando apenas os elementos considerados válidos.

    Exemplo:

        valid_elements = validate_elements(elements)

    Returns
    -------
    list
        Elementos válidos.
    """

    if not elements:
        return []

    valid_elements = []

    for element in elements:

        result = validate_element(element)

        if result["valid"]:
            valid_elements.append(element)

    return valid_elements


def validate_elements_detailed(elements):
    """
    Versão detalhada da validação.

    Retorna informações que depois poderão ser
    apresentadas ao usuário pelo script.py.

    Returns
    -------
    dict

    {
        "valid_elements": [],
        "invalid_elements": [],
        "warnings": [],
        "errors": []
    }
    """

    result = {
        "valid_elements": [],
        "invalid_elements": [],
        "warnings": [],
        "errors": []
    }

    if not elements:
        return result

    for element in elements:

        element_result = validate_element(element)

        element_id = get_element_id_value(element)

        if element_result["valid"]:
            result["valid_elements"].append(element)
        else:
            result["invalid_elements"].append(element)

        for error in element_result["errors"]:
            result["errors"].append(
                "Elemento {}: {}".format(
                    element_id,
                    error
                )
            )

        for warning in element_result["warnings"]:
            result["warnings"].append(
                "Elemento {}: {}".format(
                    element_id,
                    warning
                )
            )

    return result


def validate_instance_parameter(
    element,
    parameter_name,
    require_text=True
):
    """
    Verifica se determinado parâmetro de instância
    pode ser utilizado na renumeração.

    Retorna:

    {
        "valid": True/False,
        "parameter": Parameter ou None,
        "message": ""
    }
    """

    result = {
        "valid": False,
        "parameter": None,
        "message": ""
    }

    try:
        parameter = element.LookupParameter(
            parameter_name
        )
    except Exception:
        parameter = None

    if parameter is None:
        result["message"] = (
            "Parâmetro '{}' não encontrado."
            .format(parameter_name)
        )
        return result

    result["parameter"] = parameter

    if parameter.IsReadOnly:
        result["message"] = (
            "Parâmetro '{}' é somente leitura."
            .format(parameter_name)
        )
        return result

    if (
        require_text
        and parameter.StorageType != DB.StorageType.String
    ):
        result["message"] = (
            "Parâmetro '{}' não é do tipo texto."
            .format(parameter_name)
        )
        return result

    result["valid"] = True

    return result


def validate_type_parameter(
    doc,
    element,
    parameter_name,
    require_text=True
):
    """
    Verifica se determinado parâmetro de tipo
    pode ser utilizado na renumeração.
    """

    result = {
        "valid": False,
        "parameter": None,
        "type_element": None,
        "message": ""
    }

    if not has_valid_type(element):

        result["message"] = (
            "Elemento não possui um tipo válido."
        )

        return result

    try:
        type_element = doc.GetElement(
            element.GetTypeId()
        )
    except Exception:
        type_element = None

    if type_element is None:

        result["message"] = (
            "Não foi possível obter o tipo do elemento."
        )

        return result

    result["type_element"] = type_element

    try:
        parameter = type_element.LookupParameter(
            parameter_name
        )
    except Exception:
        parameter = None

    if parameter is None:

        result["message"] = (
            "Parâmetro de tipo '{}' não encontrado."
            .format(parameter_name)
        )

        return result

    result["parameter"] = parameter

    if parameter.IsReadOnly:

        result["message"] = (
            "Parâmetro de tipo '{}' é somente leitura."
            .format(parameter_name)
        )

        return result

    if (
        require_text
        and parameter.StorageType != DB.StorageType.String
    ):

        result["message"] = (
            "Parâmetro de tipo '{}' não é do tipo texto."
            .format(parameter_name)
        )

        return result

    result["valid"] = True

    return result


def validate_for_instance_renumber(
    elements,
    parameter_name
):
    """
    Valida previamente uma lista de elementos para
    renumeração de INSTÂNCIA.

    Não altera nada no modelo.
    """

    result = {
        "valid_elements": [],
        "invalid_elements": [],
        "errors": []
    }

    if not elements:
        return result

    for element in elements:

        check = validate_instance_parameter(
            element,
            parameter_name
        )

        if check["valid"]:

            result["valid_elements"].append(element)

        else:

            result["invalid_elements"].append(element)

            result["errors"].append(
                "Elemento {}: {}".format(
                    get_element_id_value(element),
                    check["message"]
                )
            )

    return result


def validate_for_type_renumber(
    doc,
    elements,
    parameter_name
):
    """
    Valida previamente uma lista de elementos para
    renumeração de TIPO.

    Importante:
    ainda recebe instâncias, pois são elas que foram
    selecionadas pelo usuário.
    """

    result = {
        "valid_elements": [],
        "invalid_elements": [],
        "errors": []
    }

    if not elements:
        return result

    for element in elements:

        check = validate_type_parameter(
            doc,
            element,
            parameter_name
        )

        if check["valid"]:

            result["valid_elements"].append(element)

        else:

            result["invalid_elements"].append(element)

            result["errors"].append(
                "Elemento {}: {}".format(
                    get_element_id_value(element),
                    check["message"]
                )
            )

    return result