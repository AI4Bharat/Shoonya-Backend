def filter_using_request_and_model(request, model=None):
    """
    Filter from model and return queryset.

    Input:
        request: request object (available in Django and DRF)
        model: model object (Not an instance of model)

    Output:
        queryset: queryset object after applying the filter on the model
    """

    if model is None:
        raise Exception("model is None. Please specify a model to apply the filter on.")

    # Get all parameters from request.
    params = request.GET.dict()
    return filter_using_dict_and_model(params, model)


def filter_using_dict_and_model(query_params, model=None):
    """
    Filter from model and return queryset.

    Input:
        query_params: Dict of all the filter query params
        model: model object (Not an instance of model)

    Output:
        queryset: queryset object after applying the filter on the model
    """

    if model is None:
        raise Exception("model is None. Please specify a model to apply the filter on.")

    # Filter the model to get the queryset
    try:
        return model.objects.filter(**query_params)
    except Exception as e:
        raise Exception(
            "Error in filtering the model. Error: {}. Check the fields of the query string.".format(
                e
            )
        )


def filter_using_dict_and_queryset(query_params, queryset=None):
    """
    Filter from model and return queryset.

    Input:
        query_params: Dict of all the filter query params
        model: model object (Not an instance of model)

    Output:
        queryset: queryset object after applying the filter on the model
    """

    if queryset is None:
        raise Exception(
            "Queryset is None. Please specify a queryset to apply the filter on."
        )

    # Filter the model to get the queryset
    try:
        return queryset.filter(**query_params).order_by("id")
    except Exception as e:
        raise Exception(
            "Error in filtering the queryset. Error: {}. Check the fields of the query string.".format(
                e
            )
        )


def fix_booleans_in_dict(d):
    for k, v in d.items():
        if v == "true":
            d[k] = True
        elif v == "false":
            d[k] = False
    return d
