from django.db.models import Q


def search_response_by_keyword(keyword, key_values_list, queryset):
    if keyword is None:
        return queryset
    keyword = str(keyword).lower()
    # q_objects = Q()
    # for key in key_values_list:
    #     q_objects |= Q(**{f"{key}__icontains": keyword})
    filtered_queryset = [
        item
        for item in queryset
        if any(
            keyword in str(item[key]).lower() for key in key_values_list if key in item
        )
    ]
    return filtered_queryset
