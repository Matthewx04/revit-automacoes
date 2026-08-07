# -*- coding: utf-8 -*-

"""
renumber.py

Motor de renumeração dos elementos.

Responsabilidades:
- gerar valores de numeração;
- escrever valores em parâmetros de instância;
- escrever códigos definidos pelo usuário em parâmetros de tipo;
- agrupar instâncias pelo tipo;
- reiniciar a sequência para cada tipo.

Este módulo NÃO:
- seleciona elementos;
- ordena elementos;
- abre formulários;
- inicia Transaction.

Essas responsabilidades pertencem ao script.py
e aos outros módulos.
"""

from lib.parameters import (
    get_instance_parameter,
    get_type_element,
    is_parameter_writable,
    parameter_accepts_text,
    set_parameter_value
)


# ============================================================
# RESULTADOS
# ============================================================

def create_result():
    """
    Cria a estrutura padrão retornada pelas operações.
    """

    return {
        "updated": 0,
        "skipped": 0,
        "errors": [],
        "items": []
    }


def get_element_id_value(element):
    """
    Retorna o Id numérico do elemento de forma segura.
    """

    if element is None:
        return "?"

    try:
        element_id = element.Id
    except Exception:
        return "?"

    try:
        return element_id.Value
    except Exception:
        pass

    try:
        return element_id.IntegerValue
    except Exception:
        return "?"

def get_type_id_value(type_element):
    """
    Retorna o valor numérico do ElementId do tipo.

    Compatível com versões novas e antigas
    da API do Revit.
    """

    if type_element is None:
        return None

    try:
        element_id = type_element.Id
    except Exception:
        return None

    # Revit mais recente
    try:
        return element_id.Value
    except Exception:
        pass

    # Compatibilidade com versões anteriores
    try:
        return element_id.IntegerValue
    except Exception:
        return None


def add_error(result, element, message):
    """
    Adiciona um erro ao resultado.
    """

    result["errors"].append(
        "Elemento {}: {}".format(
            get_element_id_value(element),
            message
        )
    )


# ============================================================
# VALIDAÇÃO DE CONFIGURAÇÕES
# ============================================================

def validate_start_number(start_number):
    """
    Valida o número inicial.
    """

    try:
        value = int(start_number)
    except Exception:
        raise ValueError(
            "O número inicial deve ser inteiro."
        )

    if value < 0:
        raise ValueError(
            "O número inicial não pode ser negativo."
        )

    return value


def validate_digits(digits):
    """
    Valida a quantidade mínima de dígitos.
    """

    try:
        value = int(digits)
    except Exception:
        raise ValueError(
            "A quantidade de dígitos deve ser inteira."
        )

    if value < 1:
        raise ValueError(
            "A quantidade de dígitos deve ser maior que zero."
        )

    return value


def validate_increment(increment):
    """
    Valida o incremento.
    """

    try:
        value = int(increment)
    except Exception:
        raise ValueError(
            "O incremento deve ser inteiro."
        )

    if value == 0:
        raise ValueError(
            "O incremento não pode ser zero."
        )

    return value


# ============================================================
# FORMATAÇÃO
# ============================================================

def format_sequence_number(number, digits=1):
    """
    Formata somente a parte numérica.

    Exemplos:

        number=1, digits=1 -> "1"
        number=1, digits=2 -> "01"
        number=5, digits=3 -> "005"
    """

    digits = validate_digits(digits)

    return str(int(number)).zfill(digits)


def build_instance_mark(
    type_code,
    number,
    separator="-",
    digits=1
):
    """
    Monta a Marca final da instância.

    Exemplos:

        type_code="TP1"
        number=1

        -> TP1-1


        type_code="PILAR-A"
        number=3

        -> PILAR-A-3


        type_code="X"
        number=2
        digits=2

        -> X-02
    """

    if type_code is None:
        raise ValueError(
            "O código do tipo não pode ser None."
        )

    type_code = str(type_code).strip()

    if not type_code:
        raise ValueError(
            "O código do tipo não pode estar vazio."
        )

    number_text = format_sequence_number(
        number,
        digits
    )

    if separator:
        return "{}{}{}".format(
            type_code,
            separator,
            number_text
        )

    return "{}{}".format(
        type_code,
        number_text
    )


# ============================================================
# IDENTIFICAÇÃO DOS TIPOS
# ============================================================

def get_unique_types(doc, elements):
    """
    Retorna os tipos únicos encontrados.

    Mantém a ordem em que o primeiro elemento
    de cada tipo aparece na lista.

    Exemplo:

        elemento A -> 20x40
        elemento B -> 20x40
        elemento C -> 25x30
        elemento D -> 20x40
        elemento E -> 30x50

    Retorna:

        20x40
        25x30
        30x50
    """

    unique_types = []
    seen_ids = set()

    for element in elements:

        type_element = get_type_element(
            doc,
            element
        )

        if type_element is None:
            continue

        type_id = get_type_id_value(
            type_element
        )

        if type_id is None:
            continue

        if type_id in seen_ids:
            continue

        seen_ids.add(type_id)
        unique_types.append(type_element)

    return unique_types


def group_elements_by_type(doc, elements):
    """
    Agrupa as instâncias por tipo.

    IMPORTANTE:
    mantém a ordem recebida em 'elements'.

    Isso significa que o sorting.py deve ordenar
    a lista antes desta função ser chamada.

    Retorno:

    [
        {
            "type": type_element,
            "type_id": 123,
            "elements": [...]
        },
        ...
    ]
    """

    groups = []
    groups_by_id = {}

    for element in elements:

        type_element = get_type_element(
            doc,
            element
        )

        if type_element is None:
            continue

        type_id = get_type_id_value(
            type_element
        )

        if type_id is None:
            continue

        if type_id not in groups_by_id:

            group = {
                "type": type_element,
                "type_id": type_id,
                "elements": []
            }

            groups_by_id[type_id] = group
            groups.append(group)

        groups_by_id[type_id]["elements"].append(
            element
        )

    return groups


# ============================================================
# LEITURA DE CÓDIGOS
# ============================================================

def normalize_type_codes(type_codes):
    """
    Normaliza o dicionário recebido pelo script.py.

    Aceita chaves como:

        int
        ElementId

    E converte tudo para:

        {
            12345: "TP1",
            67890: "P2"
        }
    """

    normalized = {}

    if not type_codes:
        return normalized

    for key, value in type_codes.items():

        # --------------------------------------------
        # CHAVE
        # --------------------------------------------

        try:
            key_value = key.IntegerValue
        except Exception:
            try:
                key_value = int(key)
            except Exception:
                continue

        # --------------------------------------------
        # VALOR
        # --------------------------------------------

        if value is None:
            continue

        code = str(value).strip()

        if not code:
            continue

        normalized[key_value] = code

    return normalized


def get_code_for_type(
    type_element,
    type_codes
):
    """
    Obtém o código escolhido pelo usuário
    para determinado tipo.

    Exemplo:

        type_codes = {
            12345: "TP1",
            67890: "PILAR-A"
        }
    """

    type_id = get_type_id_value(
        type_element
    )

    if type_id is None:
        return None

    return type_codes.get(type_id)


# ============================================================
# RENUMERAÇÃO SIMPLES
# ============================================================

def renumber_instances(
    elements,
    parameter_name="Marca",
    prefix="",
    start_number=1,
    digits=2,
    suffix="",
    separator="",
    increment=1,
    only_text_parameters=True
):
    """
    Renumeração simples.

    Mantemos esta função para outros usos do plugin.

    Exemplos:

        P01
        P02
        P03

    Essa função NÃO considera tipos.
    """

    result = create_result()

    if not elements:
        return result

    start_number = validate_start_number(
        start_number
    )

    digits = validate_digits(
        digits
    )

    increment = validate_increment(
        increment
    )

    current_number = start_number

    for element in elements:

        parameter = get_instance_parameter(
            element,
            parameter_name
        )

        if parameter is None:

            result["skipped"] += 1

            add_error(
                result,
                element,
                "parâmetro '{}' não encontrado.".format(
                    parameter_name
                )
            )

            continue

        if not is_parameter_writable(
            parameter
        ):

            result["skipped"] += 1

            add_error(
                result,
                element,
                "parâmetro '{}' é somente leitura.".format(
                    parameter_name
                )
            )

            continue

        if (
            only_text_parameters
            and not parameter_accepts_text(parameter)
        ):

            result["skipped"] += 1

            add_error(
                result,
                element,
                "parâmetro '{}' não é texto.".format(
                    parameter_name
                )
            )

            continue

        number_text = format_sequence_number(
            current_number,
            digits
        )

        parts = []

        if prefix:
            parts.append(str(prefix))

        parts.append(number_text)

        if suffix:
            parts.append(str(suffix))

        value = separator.join(parts)

        if set_parameter_value(
            parameter,
            value
        ):

            result["updated"] += 1

            result["items"].append({
                "element": element,
                "element_id": element.Id,
                "value": value,
                "number": current_number
            })

            current_number += increment

        else:

            result["skipped"] += 1

            add_error(
                result,
                element,
                "não foi possível escrever '{}'.".format(
                    value
                )
            )

    return result


# ============================================================
# ESCREVER CÓDIGOS NOS TIPOS
# ============================================================

def apply_type_codes(
    doc,
    elements,
    type_codes,
    parameter_name="Marca de tipo",
    only_text_parameters=True
):
    """
    Escreve no parâmetro de tipo os códigos
    escolhidos pelo usuário.

    Exemplo:

        20x40 -> "TP1"
        25x30 -> "P2"
        30x50 -> "ESPECIAL"

    O renumber.py NÃO cria esses códigos.
    Ele apenas recebe o dicionário do script.py.
    """

    result = create_result()

    if not elements:
        return result

    type_codes = normalize_type_codes(
        type_codes
    )

    unique_types = get_unique_types(
        doc,
        elements
    )

    for type_element in unique_types:

        type_id = get_type_id_value(
            type_element
        )

        code = type_codes.get(
            type_id
        )

        if code is None:

            result["skipped"] += 1

            add_error(
                result,
                type_element,
                "nenhum código foi definido para este tipo."
            )

            continue

        try:
            parameter = type_element.LookupParameter(
                parameter_name
            )
        except Exception:
            parameter = None

        if parameter is None:

            result["skipped"] += 1

            add_error(
                result,
                type_element,
                "parâmetro de tipo '{}' não encontrado.".format(
                    parameter_name
                )
            )

            continue

        if not is_parameter_writable(
            parameter
        ):

            result["skipped"] += 1

            add_error(
                result,
                type_element,
                "parâmetro de tipo '{}' é somente leitura.".format(
                    parameter_name
                )
            )

            continue

        if (
            only_text_parameters
            and not parameter_accepts_text(parameter)
        ):

            result["skipped"] += 1

            add_error(
                result,
                type_element,
                "parâmetro de tipo '{}' não é texto.".format(
                    parameter_name
                )
            )

            continue

        if set_parameter_value(
            parameter,
            code
        ):

            result["updated"] += 1

            result["items"].append({
                "type": type_element,
                "type_id": type_element.Id,
                "code": code,
                "value": code
            })

        else:

            result["skipped"] += 1

            add_error(
                result,
                type_element,
                "não foi possível escrever o código '{}'.".format(
                    code
                )
            )

    return result


# ============================================================
# RENUMERAÇÃO PRINCIPAL POR TIPO
# ============================================================

def renumber_instances_by_type(
    doc,
    elements,
    type_codes,
    instance_parameter_name="Marca",
    start_number=1,
    digits=1,
    separator="-",
    increment=1,
    only_text_parameters=True
):
    """
    Renumera as instâncias utilizando o código
    definido pelo usuário para cada tipo.

    Esta é a função principal para a nova lógica.

    Exemplo:

    Tipos encontrados:

        20x40
        25x30

    Usuário define:

        20x40 -> TP1
        25x30 -> PILAR-B

    O script.py fornece:

        type_codes = {
            id_20x40: "TP1",
            id_25x30: "PILAR-B"
        }

    Resultado:

        TP1-1
        TP1-2
        TP1-3

        PILAR-B-1
        PILAR-B-2

    IMPORTANTE:
    a sequência reinicia em cada tipo.
    """

    result = create_result()

    # Informação adicional útil para relatório
    result["groups"] = []

    if not elements:
        return result

    start_number = validate_start_number(
        start_number
    )

    digits = validate_digits(
        digits
    )

    increment = validate_increment(
        increment
    )

    type_codes = normalize_type_codes(
        type_codes
    )

    groups = group_elements_by_type(
        doc,
        elements
    )

    for group in groups:

        type_element = group["type"]
        type_id = group["type_id"]
        group_elements = group["elements"]

        # ----------------------------------------------------
        # CÓDIGO ESCOLHIDO PARA O TIPO
        # ----------------------------------------------------

        type_code = type_codes.get(
            type_id
        )

        if not type_code:

            for element in group_elements:

                result["skipped"] += 1

                add_error(
                    result,
                    element,
                    "nenhum código foi definido para o tipo."
                )

            continue

        # ----------------------------------------------------
        # CADA TIPO COMEÇA NOVAMENTE NO NÚMERO INICIAL
        # ----------------------------------------------------

        current_number = start_number

        group_result = {
            "type": type_element,
            "type_id": type_element.Id,
            "type_code": type_code,
            "updated": 0,
            "skipped": 0,
            "items": []
        }

        # ----------------------------------------------------
        # INSTÂNCIAS
        # ----------------------------------------------------

        for element in group_elements:

            parameter = get_instance_parameter(
                element,
                instance_parameter_name
            )

            if parameter is None:

                result["skipped"] += 1
                group_result["skipped"] += 1

                add_error(
                    result,
                    element,
                    "parâmetro de instância '{}' não encontrado.".format(
                        instance_parameter_name
                    )
                )

                continue

            if not is_parameter_writable(
                parameter
            ):

                result["skipped"] += 1
                group_result["skipped"] += 1

                add_error(
                    result,
                    element,
                    "parâmetro '{}' é somente leitura.".format(
                        instance_parameter_name
                    )
                )

                continue

            if (
                only_text_parameters
                and not parameter_accepts_text(parameter)
            ):

                result["skipped"] += 1
                group_result["skipped"] += 1

                add_error(
                    result,
                    element,
                    "parâmetro '{}' não é texto.".format(
                        instance_parameter_name
                    )
                )

                continue

            # ------------------------------------------------
            # VALOR FINAL
            # ------------------------------------------------

            value = build_instance_mark(
                type_code=type_code,
                number=current_number,
                separator=separator,
                digits=digits
            )

            # ------------------------------------------------
            # ESCREVER
            # ------------------------------------------------

            if set_parameter_value(
                parameter,
                value
            ):

                result["updated"] += 1
                group_result["updated"] += 1

                item = {
                    "element": element,
                    "element_id": element.Id,
                    "type": type_element,
                    "type_id": type_element.Id,
                    "type_code": type_code,
                    "number": current_number,
                    "value": value
                }

                result["items"].append(item)
                group_result["items"].append(item)

                current_number += increment

            else:

                result["skipped"] += 1
                group_result["skipped"] += 1

                add_error(
                    result,
                    element,
                    "não foi possível escrever '{}'.".format(
                        value
                    )
                )

        result["groups"].append(
            group_result
        )

    return result


# ============================================================
# OPERAÇÃO COMPLETA
# ============================================================

def apply_codes_and_renumber(
    doc,
    elements,
    type_codes,
    type_parameter_name="Marca de tipo",
    instance_parameter_name="Marca",
    start_number=1,
    digits=1,
    separator="-",
    increment=1
):
    """
    Executa as duas partes da nova lógica:

    1. grava o código escolhido no tipo;
    2. utiliza esse código para numerar as instâncias.

    Exemplo:

        20x40 -> código digitado "TP1"
        25x30 -> código digitado "A"

    Marca de tipo:

        20x40 = TP1
        25x30 = A

    Marca das instâncias:

        TP1-1
        TP1-2
        TP1-3

        A-1
        A-2

    ATENÇÃO:
    esta função NÃO inicia Transaction.
    O script.py deve chamá-la dentro da Transaction.
    """

    type_result = apply_type_codes(
        doc=doc,
        elements=elements,
        type_codes=type_codes,
        parameter_name=type_parameter_name
    )

    instance_result = renumber_instances_by_type(
        doc=doc,
        elements=elements,
        type_codes=type_codes,
        instance_parameter_name=instance_parameter_name,
        start_number=start_number,
        digits=digits,
        separator=separator,
        increment=increment
    )

    return {
        "types": type_result,
        "instances": instance_result
    }