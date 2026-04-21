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

def filter_by_language_status_domain(queryset, request):
    """
    Apply optional language / status / domain filters from query params.
    Composable — missing param = no change to queryset.
    Works for both Project and Task querysets.
    """
    from django.db.models import Q

    language = request.query_params.get("language")
    req_status = request.query_params.get("status")
    domain = request.query_params.get("domain")

    if language:
        # Project has src_language / tgt_language; Task inherits language
        # from its project — filter via project FK traversal as fallback
        model_fields = {f.name for f in queryset.model._meta.get_fields()}
        if "src_language" in model_fields or "tgt_language" in model_fields:
            queryset = queryset.filter(
                Q(src_language=language) | Q(tgt_language=language)
            )
        elif "project_id" in model_fields:
            # Task model — traverse to project language fields
            queryset = queryset.filter(
                Q(project_id__src_language=language)
                | Q(project_id__tgt_language=language)
            )

    if req_status:
        model_fields = {f.name for f in queryset.model._meta.get_fields()}
        if "task_status" in model_fields:
            queryset = queryset.filter(task_status=req_status)
        elif "annotation_status" in model_fields:
            queryset = queryset.filter(annotation_status=req_status)

    if domain:
        # Domain is stored inside metadata_json on Project
        # e.g. metadata_json = {"domain": "medical"}
        queryset = queryset.filter(metadata_json__domain=domain)

    return queryset