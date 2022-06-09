from urllib.parse import unquote


def parse_for_data_types(string: str):
    """
    Convert variables to their appropriate type
    """

    # Need to implement datetime field as well to implement datetime-based filters
    try:  # Try to convert to a int
        return int(string)
    except Exception:
        pass

    try:  # Try to convert to a float
        return float(string)
    except Exception:
        pass

    if string.lower() in ["true", "false"]:
        return bool(string)

    return string  # If none work, return a string


def extract_search_params(query_dict: dict) -> dict:
    """
    Extract the parameters from the request params that start with ```search_```
    """
    new_dict: dict = {}
    for i in query_dict.items():
        if "search_" in i[0]:
            new_dict[i[0][7:]] = unquote(i[1])

    return new_dict


def flatten(to_flatten: dict, sep: str = "__") -> dict:
    new_dict = {}
    for i, j in to_flatten.items():
        if isinstance(j, dict):
            flat_dict = flatten(j)
            for k, l in flat_dict.items():
                new_dict[f"{i}{sep}{k}"] = l
        else:
            new_dict[i] = j

    return new_dict


def process_search_query(
    query_dict: dict, search_field_name: str, searchable_fields: list
) -> dict:
    """
    Extract the query params into a queryset dictionary.
    """
    parsed_value: any = None
    queryset_dict: dict = {}

    print(query_dict)

    try:
        for i, j in flatten(extract_search_params(query_dict)).items():
            parsed_value = parse_for_data_types(j)
            print({i: j})
            if i in searchable_fields:
                if type(parsed_value) == str:
                    queryset_dict[
                        f"{search_field_name}__{i}__icontains"
                    ] = parsed_value  # Unaccent doesn't work as intended.
                else:
                    queryset_dict[f"{search_field_name}__{i}"] = parsed_value
            else:
                if type(parsed_value) != str:
                    queryset_dict[i] = parse_for_data_types(j)
                else:
                    queryset_dict[
                        f"{i}__icontains"
                    ] = parsed_value  # Unaccent is not supported for CharField
    except Exception as e:
        print(f"\033[1mError found while processing query dictionary. In: {e}\033[0m")

    return queryset_dict
