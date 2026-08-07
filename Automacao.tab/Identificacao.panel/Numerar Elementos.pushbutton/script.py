# -*- coding: utf-8 -*-

"""
Renumerar Elementos

Fluxo:
1. Coleta os elementos
2. Valida
3. Escolhe parâmetro de instância
4. Escolhe parâmetro de tipo
5. Escolhe direção
6. Ordena
7. Identifica os tipos
8. Usuário define o código de cada tipo
9. Configura sequência
10. Mostra prévia
11. Grava os códigos
12. Renumera as instâncias por tipo
"""

from pyrevit import revit, forms, DB

from lib.collectors import pick_elements_by_rectangle
from lib.sorting import sort_elements

from lib.parameters import (
    get_writable_instance_parameters,
    get_writable_type_parameters,
    get_instance_parameter,
    get_type_parameter,
    parameter_accepts_text
)

from lib.validation import (
    validate_elements_detailed,
    validate_for_instance_renumber,
    validate_for_type_renumber
)

from lib.renumber import (
    get_unique_types,
    apply_codes_and_renumber
)

from lib.annotations import (
    annotate_elements,
    TEXT_TYPE_NAME
)


# ============================================================
# CONTEXTO
# ============================================================

doc = revit.doc
uidoc = revit.uidoc
active_view = uidoc.ActiveView


# ============================================================
# DIREÇÕES
# ============================================================

DIRECTION_OPTIONS = [
    "Esquerda -> Direita",
    "Direita -> Esquerda",
    "Cima -> Baixo",
    "Baixo -> Cima"
]

DIRECTION_MAP = {
    "Esquerda -> Direita": "left_to_right",
    "Direita -> Esquerda": "right_to_left",
    "Cima -> Baixo": "top_to_bottom",
    "Baixo -> Cima": "bottom_to_top"
}


# ============================================================
# IDS
# ============================================================

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


# ============================================================
# NOMES
# ============================================================

def safe_name(element):

    if element is None:
        return "Tipo desconhecido"

    try:

        name = element.Name

        if name:
            return name

    except Exception:
        pass

    try:

        parameter = element.get_Parameter(
            DB.BuiltInParameter.SYMBOL_NAME_PARAM
        )

        if parameter:

            value = parameter.AsString()

            if value:
                return value

    except Exception:
        pass

    try:

        return "Tipo {}".format(
            get_id_value(element.Id)
        )

    except Exception:

        return "Tipo desconhecido"


def get_family_name(type_element):

    if type_element is None:
        return ""

    try:

        family = type_element.Family

        if family:

            name = family.Name

            if name:
                return name

    except Exception:
        pass

    try:

        parameter = type_element.get_Parameter(
            DB.BuiltInParameter.SYMBOL_FAMILY_NAME_PARAM
        )

        if parameter:

            value = parameter.AsString()

            if value:
                return value

    except Exception:
        pass

    return ""


def get_category_name(element):

    try:

        if element.Category:

            name = element.Category.Name

            if name:
                return name

    except Exception:
        pass

    return ""


def get_type_display_name(type_element):

    type_name = safe_name(
        type_element
    )

    family_name = get_family_name(
        type_element
    )

    if family_name:

        return "{} - {}".format(
            family_name,
            type_name
        )

    category_name = get_category_name(
        type_element
    )

    if category_name:

        return "{} - {}".format(
            category_name,
            type_name
        )

    return type_name


# ============================================================
# PARÂMETROS COMUNS DE INSTÂNCIA
# ============================================================

def get_common_instance_text_parameters(elements):

    if not elements:
        return []

    common_names = None

    for element in elements:

        names = set()

        parameter_names = (
            get_writable_instance_parameters(
                element
            )
        )

        for name in parameter_names:

            parameter = get_instance_parameter(
                element,
                name
            )

            if parameter is None:
                continue

            if not parameter_accepts_text(
                parameter
            ):
                continue

            names.add(name)

        if common_names is None:

            common_names = names

        else:

            common_names = (
                common_names.intersection(
                    names
                )
            )

        if not common_names:
            return []

    return sorted(common_names)


# ============================================================
# PARÂMETROS COMUNS DE TIPO
# ============================================================

def get_common_type_text_parameters(elements):

    if not elements:
        return []

    common_names = None

    for element in elements:

        names = set()

        parameter_names = (
            get_writable_type_parameters(
                doc,
                element
            )
        )

        for name in parameter_names:

            parameter = get_type_parameter(
                doc,
                element,
                name
            )

            if parameter is None:
                continue

            if not parameter_accepts_text(
                parameter
            ):
                continue

            names.add(name)

        if common_names is None:

            common_names = names

        else:

            common_names = (
                common_names.intersection(
                    names
                )
            )

        if not common_names:
            return []

    return sorted(common_names)


# ============================================================
# ESCOLHA DE PARÂMETRO
# ============================================================

def ask_parameter(parameter_names, title):

    if not parameter_names:

        forms.alert(
            (
                "Nenhum parâmetro de texto editável "
                "comum aos elementos foi encontrado."
            ),
            title="Renumerar elementos",
            exitscript=True
        )

    selected = forms.SelectFromList.show(
        parameter_names,
        title=title,
        button_name="Confirmar"
    )

    if not selected:

        forms.alert(
            "Nenhum parâmetro foi selecionado.",
            title="Renumerar elementos",
            exitscript=True
        )

    return selected


# ============================================================
# DIREÇÃO
# ============================================================

def ask_direction():

    selected = forms.SelectFromList.show(
        DIRECTION_OPTIONS,
        title="Ordem da numeração",
        button_name="Confirmar"
    )

    if not selected:

        forms.alert(
            "Nenhuma direção foi selecionada.",
            title="Renumerar elementos",
            exitscript=True
        )

    return (
        DIRECTION_MAP[selected],
        selected
    )


# ============================================================
# NÚMERO INICIAL
# ============================================================

def ask_start_number():

    while True:

        value = forms.ask_for_string(
            default="1",
            prompt=(
                "Digite o número inicial.\n\n"
                "A sequência será reiniciada "
                "para cada tipo."
            ),
            title="Número inicial"
        )

        if value is None:

            forms.alert(
                "Operação cancelada.",
                title="Renumerar elementos",
                exitscript=True
            )

        try:

            number = int(value)

            if number < 0:
                raise ValueError

            return number

        except Exception:

            forms.alert(
                (
                    "Digite um número inteiro "
                    "igual ou maior que zero."
                ),
                title="Valor inválido"
            )


# ============================================================
# DÍGITOS
# ============================================================

def ask_digits():

    while True:

        value = forms.ask_for_string(
            default="1",
            prompt=(
                "Quantidade de dígitos:\n\n"
                "1 -> COD-1, COD-2\n"
                "2 -> COD-01, COD-02\n"
                "3 -> COD-001, COD-002"
            ),
            title="Dígitos"
        )

        if value is None:

            forms.alert(
                "Operação cancelada.",
                title="Renumerar elementos",
                exitscript=True
            )

        try:

            digits = int(value)

            if digits < 1:
                raise ValueError

            return digits

        except Exception:

            forms.alert(
                "Digite um inteiro maior que zero.",
                title="Valor inválido"
            )


# ============================================================
# SEPARADOR
# ============================================================

def ask_separator():

    value = forms.ask_for_string(
        default="-",
        prompt=(
            "Digite o separador.\n\n"
            "Exemplos:\n"
            "-  -> TP1-1\n"
            ".  -> TP1.1\n"
            "_  -> TP1_1\n"
            "vazio -> TP11"
        ),
        title="Separador"
    )

    if value is None:

        forms.alert(
            "Operação cancelada.",
            title="Renumerar elementos",
            exitscript=True
        )

    return value


# ============================================================
# VALOR ATUAL DO TIPO
# ============================================================

def get_current_type_code(
    type_element,
    type_parameter_name
):

    try:

        parameter = type_element.LookupParameter(
            type_parameter_name
        )

    except Exception:

        parameter = None

    if parameter is None:
        return ""

    try:

        value = parameter.AsString()

        if value:
            return value.strip()

    except Exception:
        pass

    return ""


# ============================================================
# CÓDIGO DE CADA TIPO
# ============================================================

def ask_type_codes(
    type_elements,
    type_parameter_name
):

    type_codes = {}

    total = len(type_elements)

    for index, type_element in enumerate(
        type_elements,
        start=1
    ):

        display_name = get_type_display_name(
            type_element
        )

        current_value = get_current_type_code(
            type_element,
            type_parameter_name
        )

        prompt = (
            "Tipo {}/{}\n\n"
            "{}\n\n"
            "Digite o código deste tipo.\n\n"
            "Exemplos:\n"
            "TP1\n"
            "P2\n"
            "A\n"
            "PILAR-A"
        ).format(
            index,
            total,
            display_name
        )

        while True:

            code = forms.ask_for_string(
                default=current_value,
                prompt=prompt,
                title="Código do tipo"
            )

            if code is None:

                forms.alert(
                    "Operação cancelada.",
                    title="Renumerar elementos",
                    exitscript=True
                )

            code = code.strip()

            if code:
                break

            forms.alert(
                "O código não pode ficar vazio.",
                title="Código inválido"
            )

        type_id = get_id_value(
            type_element.Id
        )

        if type_id is None:

            forms.alert(
                "Não foi possível identificar um dos tipos.",
                title="Erro",
                exitscript=True
            )

        type_codes[type_id] = code

    return type_codes


# ============================================================
# CÓDIGOS DUPLICADOS
# ============================================================

def find_duplicate_codes(type_codes):

    seen = {}
    duplicates = []

    for type_id, code in type_codes.items():

        normalized = (
            code.strip().lower()
        )

        if normalized in seen:

            if normalized not in duplicates:

                duplicates.append(
                    normalized
                )

        else:

            seen[normalized] = type_id

    return duplicates


# ============================================================
# CONTAGEM POR TIPO
# ============================================================

def count_elements_by_type(elements):

    counts = {}

    for element in elements:

        try:

            type_id = get_id_value(
                element.GetTypeId()
            )

        except Exception:

            type_id = None

        if type_id is None:
            continue

        counts[type_id] = (
            counts.get(type_id, 0) + 1
        )

    return counts


# ============================================================
# PREVIEW
# ============================================================

def build_preview(
    selected_count,
    process_count,
    type_elements,
    type_codes,
    type_counts,
    start_number,
    digits,
    separator,
    direction_label,
    instance_parameter_name,
    type_parameter_name
):

    lines = []

    lines.append(
        "CONFIGURAÇÃO DA RENUMERAÇÃO"
    )

    lines.append("")

    lines.append(
        "Selecionados: {}".format(
            selected_count
        )
    )

    lines.append(
        "Processados: {}".format(
            process_count
        )
    )

    lines.append(
        "Tipos encontrados: {}".format(
            len(type_elements)
        )
    )

    lines.append("")

    lines.append(
        "Parâmetro do tipo: {}".format(
            type_parameter_name
        )
    )

    lines.append(
        "Parâmetro da instância: {}".format(
            instance_parameter_name
        )
    )

    lines.append(
        "Ordem: {}".format(
            direction_label
        )
    )

    lines.append(
        "Número inicial: {}".format(
            start_number
        )
    )

    lines.append(
        "Dígitos: {}".format(
            digits
        )
    )

    if separator:

        lines.append(
            "Separador: '{}'".format(
                separator
            )
        )

    else:

        lines.append(
            "Separador: nenhum"
        )

    lines.append("")
    lines.append("TIPOS:")

    for type_element in type_elements:

        type_id = get_id_value(
            type_element.Id
        )

        code = type_codes.get(
            type_id,
            "?"
        )

        count = type_counts.get(
            type_id,
            0
        )

        lines.append(
            "{} -> {} ({} elemento(s))".format(
                get_type_display_name(
                    type_element
                ),
                code,
                count
            )
        )

    return "\n".join(lines)


# ============================================================
# RELATÓRIO
# ============================================================

def build_result_message(
    selected_count,
    process_count,
    type_result,
    instance_result
):

    lines = []

    lines.append("Concluído!")
    lines.append("")

    lines.append(
        "{} elemento(s) selecionado(s).".format(
            selected_count
        )
    )

    lines.append(
        "{} elemento(s) processado(s).".format(
            process_count
        )
    )

    lines.append(
        "{} tipo(s) atualizado(s).".format(
            type_result.get(
                "updated",
                0
            )
        )
    )

    lines.append(
        "{} instância(s) renumerada(s).".format(
            instance_result.get(
                "updated",
                0
            )
        )
    )

    groups = instance_result.get(
        "groups",
        []
    )

    if groups:

        lines.append("")
        lines.append("Resultado por tipo:")

        for group in groups:

            lines.append(
                "{} -> {} elemento(s)".format(
                    group.get(
                        "type_code",
                        "?"
                    ),
                    group.get(
                        "updated",
                        0
                    )
                )
            )

    errors = []

    errors.extend(
        type_result.get(
            "errors",
            []
        )
    )

    errors.extend(
        instance_result.get(
            "errors",
            []
        )
    )

    if errors:

        lines.append("")

        lines.append(
            "{} aviso(s)/erro(s):".format(
                len(errors)
            )
        )

        for error in errors[:10]:

            lines.append(
                "- {}".format(error)
            )

        if len(errors) > 10:

            lines.append(
                "... e mais {}.".format(
                    len(errors) - 10
                )
            )

    return "\n".join(lines)


# ============================================================
# MAIN
# ============================================================

def main():

    # --------------------------------------------------------
    # 1. COLETA
    # --------------------------------------------------------

    elements = pick_elements_by_rectangle()

    if not elements:

        forms.alert(
            "Nenhum elemento foi selecionado.",
            title="Renumerar elementos",
            exitscript=True
        )


    # --------------------------------------------------------
    # 2. VALIDAÇÃO GERAL
    # --------------------------------------------------------

    validation = validate_elements_detailed(
        elements
    )

    valid_elements = validation.get(
        "valid_elements",
        []
    )

    if not valid_elements:

        forms.alert(
            (
                "Nenhum dos elementos selecionados "
                "pode ser utilizado."
            ),
            title="Renumerar elementos",
            exitscript=True
        )


    # --------------------------------------------------------
    # 3. PARÂMETRO DE INSTÂNCIA
    # --------------------------------------------------------

    instance_parameters = (
        get_common_instance_text_parameters(
            valid_elements
        )
    )

    instance_parameter_name = ask_parameter(
        instance_parameters,
        (
            "Parâmetro de instância "
            "que receberá a numeração"
        )
    )


    # --------------------------------------------------------
    # 4. VALIDAR INSTÂNCIAS
    # --------------------------------------------------------

    instance_validation = (
        validate_for_instance_renumber(
            valid_elements,
            instance_parameter_name
        )
    )

    process_elements = (
        instance_validation.get(
            "valid_elements",
            []
        )
    )

    if not process_elements:

        forms.alert(
            (
                "Nenhum elemento pode receber "
                "a numeração no parâmetro '{}'."
            ).format(
                instance_parameter_name
            ),
            title="Renumerar elementos",
            exitscript=True
        )


    # --------------------------------------------------------
    # 5. PARÂMETRO DE TIPO
    # --------------------------------------------------------

    type_parameters = (
        get_common_type_text_parameters(
            process_elements
        )
    )

    type_parameter_name = ask_parameter(
        type_parameters,
        (
            "Parâmetro de tipo "
            "que receberá o código"
        )
    )


    # --------------------------------------------------------
    # 6. VALIDAR TIPOS
    # --------------------------------------------------------

    type_validation = (
        validate_for_type_renumber(
            doc,
            process_elements,
            type_parameter_name
        )
    )

    process_elements = (
        type_validation.get(
            "valid_elements",
            []
        )
    )

    if not process_elements:

        forms.alert(
            (
                "Nenhum elemento possui o parâmetro "
                "de tipo '{}' disponível."
            ).format(
                type_parameter_name
            ),
            title="Renumerar elementos",
            exitscript=True
        )


    # --------------------------------------------------------
    # 7. DIREÇÃO
    # --------------------------------------------------------

    direction, direction_label = (
        ask_direction()
    )


    # --------------------------------------------------------
    # 8. ORDENAR
    # --------------------------------------------------------

    ordered_elements = sort_elements(
        process_elements,
        direction=direction
    )

    if not ordered_elements:

        forms.alert(
            "Não foi possível ordenar os elementos.",
            title="Renumerar elementos",
            exitscript=True
        )


    # --------------------------------------------------------
    # 9. TIPOS ÚNICOS
    # --------------------------------------------------------

    unique_types = get_unique_types(
        doc,
        ordered_elements
    )

    if not unique_types:

        forms.alert(
            "Nenhum tipo válido foi encontrado.",
            title="Renumerar elementos",
            exitscript=True
        )


    # --------------------------------------------------------
    # 10. CÓDIGOS DOS TIPOS
    # --------------------------------------------------------

    type_codes = ask_type_codes(
        unique_types,
        type_parameter_name
    )


    # --------------------------------------------------------
    # 11. DUPLICADOS
    # --------------------------------------------------------

    duplicates = find_duplicate_codes(
        type_codes
    )

    if duplicates:

        forms.alert(
            (
                "Dois ou mais tipos receberam "
                "o mesmo código:\n\n{}\n\n"
                "Cada tipo deve possuir "
                "um código diferente."
            ).format(
                ", ".join(duplicates)
            ),
            title="Código duplicado",
            exitscript=True
        )


    # --------------------------------------------------------
    # 12. CONFIGURAÇÃO
    # --------------------------------------------------------

    start_number = ask_start_number()

    digits = ask_digits()

    separator = ask_separator()


    # --------------------------------------------------------
    # 13. CONTAGEM
    # --------------------------------------------------------

    type_counts = count_elements_by_type(
        ordered_elements
    )


    # --------------------------------------------------------
    # 14. PREVIEW
    # --------------------------------------------------------

    preview = build_preview(
        selected_count=len(elements),
        process_count=len(ordered_elements),
        type_elements=unique_types,
        type_codes=type_codes,
        type_counts=type_counts,
        start_number=start_number,
        digits=digits,
        separator=separator,
        direction_label=direction_label,
        instance_parameter_name=instance_parameter_name,
        type_parameter_name=type_parameter_name
    )

    proceed = forms.alert(
        (
            preview
            + "\n\nDeseja aplicar esta renumeração?"
        ),
        title="Confirmar renumeração",
        yes=True,
        no=True
    )

    if not proceed:
        return


    # --------------------------------------------------------
    # 15. TRANSAÇÃO
    # --------------------------------------------------------

    try:

        with revit.Transaction(
            "Renumerar elementos por tipo"
        ):

            result = apply_codes_and_renumber(
                doc=doc,
                elements=ordered_elements,
                type_codes=type_codes,
                type_parameter_name=type_parameter_name,
                instance_parameter_name=instance_parameter_name,
                start_number=start_number,
                digits=digits,
                separator=separator,
                increment=1
            )

    except Exception as ex:

        forms.alert(
            (
                "Erro durante a renumeração:\n\n{}"
            ).format(
                str(ex)
            ),
            title="Erro",
            exitscript=True
        )


    # --------------------------------------------------------
    # 16. RESULTADOS DA RENUMERAÇÃO
    # --------------------------------------------------------

    type_result = result.get(
        "types",
        {}
    )

    instance_result = result.get(
        "instances",
        {}
    )


    # --------------------------------------------------------
    # 17. PERGUNTAR SE DESEJA CRIAR ANOTAÇÕES
    # --------------------------------------------------------

    create_annotations = forms.alert(
        (
            "A renumeração foi concluída com sucesso.\n\n"
            "Deseja criar as anotações dos elementos "
            "na vista ativa?\n\n"
            "Estilo: {}".format(
                TEXT_TYPE_NAME
            )
        ),
        title="Criar anotações",
        yes=True,
        no=True
    )

    annotation_result = None


    # --------------------------------------------------------
    # 18. CRIAR ANOTAÇÕES
    # --------------------------------------------------------

    if create_annotations:

        try:

            with revit.Transaction(
                "Criar anotações dos elementos"
            ):

                annotation_result = annotate_elements(
                    doc=doc,
                    view=active_view,
                    elements=ordered_elements,
                    parameter_name=instance_parameter_name
                )

        except Exception as ex:

            forms.alert(
                (
                    "A renumeração foi concluída normalmente, "
                    "mas ocorreu um erro ao criar as anotações.\n\n{}"
                ).format(
                    str(ex)
                ),
                title="Erro nas anotações"
            )


    # --------------------------------------------------------
    # 19. RELATÓRIO FINAL
    # --------------------------------------------------------

    message = build_result_message(
        selected_count=len(elements),
        process_count=len(ordered_elements),
        type_result=type_result,
        instance_result=instance_result
    )

    if annotation_result is not None:

        message += (
            "\n\nANOTAÇÕES\n"
            "{} anotação(ões) criada(s)."
        ).format(
            annotation_result.get(
                "created",
                0
            )
        )

        skipped_annotations = annotation_result.get(
            "skipped",
            0
        )

        if skipped_annotations:

            message += (
                "\n{} elemento(s) sem anotação."
            ).format(
                skipped_annotations
            )

        annotation_errors = annotation_result.get(
            "errors",
            []
        )

        if annotation_errors:

            message += (
                "\n\n{} aviso(s) nas anotações:"
            ).format(
                len(annotation_errors)
            )

            for error in annotation_errors[:5]:

                message += (
                    "\n- {}".format(
                        error
                    )
                )

            if len(annotation_errors) > 5:

                message += (
                    "\n... e mais {}."
                ).format(
                    len(annotation_errors) - 5
                )

    forms.alert(
        message,
        title="Renumerar elementos"
    )


# ============================================================
# EXECUTAR
# ============================================================

if __name__ == "__main__":
    main()