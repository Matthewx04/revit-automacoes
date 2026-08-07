# -*- coding: utf-8 -*-

"""
parameters.py

Funções utilitárias para trabalhar com parâmetros
de instância e de tipo no Revit.
"""

from pyrevit import DB


def get_type_element(doc, element):
    """
    Retorna o elemento de tipo associado a uma instância.

    Funciona com FamilyInstance e outros elementos
    que possuem GetTypeId().

    Retorna None quando o elemento realmente
    não possui tipo válido.
    """

    if element is None:
        return None

    try:
        type_id = element.GetTypeId()
    except Exception:
        return None

    if type_id is None:
        return None

    # --------------------------------------------------------
    # VERIFICAR SE O ID É INVÁLIDO
    # Compatibilidade entre versões do Revit
    # --------------------------------------------------------

    try:
        type_id_value = type_id.Value
    except Exception:
        try:
            type_id_value = type_id.IntegerValue
        except Exception:
            type_id_value = None

    try:
        invalid_id = DB.ElementId.InvalidElementId

        try:
            invalid_value = invalid_id.Value
        except Exception:
            invalid_value = invalid_id.IntegerValue

        if type_id_value == invalid_value:
            return None

    except Exception:
        pass

    # --------------------------------------------------------
    # OBTER O TIPO
    # --------------------------------------------------------

    try:
        type_element = doc.GetElement(type_id)
    except Exception:
        type_element = None

    if type_element is None:
        return None

    return type_element


def get_instance_parameter(element, parameter_name):
    """
    Procura um parâmetro de instância pelo nome.
    """

    try:
        return element.LookupParameter(parameter_name)
    except Exception:
        return None


def get_type_parameter(doc, element, parameter_name):
    """
    Procura um parâmetro no tipo do elemento.
    """

    type_element = get_type_element(doc, element)

    if type_element is None:
        return None

    try:
        return type_element.LookupParameter(parameter_name)
    except Exception:
        return None


def is_parameter_writable(parameter):
    """
    Verifica se um parâmetro existe e pode ser alterado.
    """

    if parameter is None:
        return False

    if parameter.IsReadOnly:
        return False

    return True


def parameter_accepts_text(parameter):
    """
    Verifica se o parâmetro aceita texto diretamente.

    Para nosso renumerador, o ideal é trabalhar inicialmente
    somente com parâmetros do tipo String.
    """

    if parameter is None:
        return False

    return parameter.StorageType == DB.StorageType.String


def set_parameter_value(parameter, value):
    """
    Define um valor em um parâmetro.

    Retorna:
        True  -> valor definido
        False -> não foi possível definir
    """

    if not is_parameter_writable(parameter):
        return False

    try:
        parameter.Set(str(value))
        return True

    except Exception:
        return False


def set_instance_parameter(element, parameter_name, value):
    """
    Define um valor em um parâmetro de instância.
    """

    parameter = get_instance_parameter(
        element,
        parameter_name
    )

    if not is_parameter_writable(parameter):
        return False

    return set_parameter_value(
        parameter,
        value
    )


def set_type_parameter(doc, element, parameter_name, value):
    """
    Define um valor em um parâmetro de tipo.
    """

    parameter = get_type_parameter(
        doc,
        element,
        parameter_name
    )

    if not is_parameter_writable(parameter):
        return False

    return set_parameter_value(
        parameter,
        value
    )


def get_writable_instance_parameters(element):
    """
    Retorna uma lista com os nomes dos parâmetros
    de instância que podem ser editados.
    """

    parameter_names = []

    try:
        for parameter in element.Parameters:

            if parameter.Definition is None:
                continue

            if parameter.IsReadOnly:
                continue

            name = parameter.Definition.Name

            if name:
                parameter_names.append(name)

    except Exception:
        pass

    return sorted(set(parameter_names))


def get_writable_type_parameters(doc, element):
    """
    Retorna uma lista com os nomes dos parâmetros
    editáveis do tipo do elemento.
    """

    type_element = get_type_element(
        doc,
        element
    )

    if type_element is None:
        return []

    parameter_names = []

    try:
        for parameter in type_element.Parameters:

            if parameter.Definition is None:
                continue

            if parameter.IsReadOnly:
                continue

            name = parameter.Definition.Name

            if name:
                parameter_names.append(name)

    except Exception:
        pass

    return sorted(set(parameter_names))


def get_available_parameters(doc, element):
    """
    Retorna parâmetros de instância e tipo separados.

    Exemplo:

    {
        "instance": ["Marca", "Comentários"],
        "type": ["Marca de tipo", "Descrição"]
    }
    """

    return {
        "instance": get_writable_instance_parameters(element),
        "type": get_writable_type_parameters(doc, element)
    }