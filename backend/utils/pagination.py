from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


def paginate_queryset(queryset, page_number, page_size):
    tasks_list = list(queryset.keys())
    if page_number:
        paginator = Paginator(tasks_list, page_size)
        try:
            page_obj = paginator.page(page_number)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        task_list = list(page_obj.object_list)
        result_dict = {}
        for i in task_list:
            result_dict[i] = queryset[i]
        data = {
            "page_number": page_obj.number,
            "page_size": page_size,
            "has_next": page_obj.has_next(),
            "has_previous": page_obj.has_previous(),
            "results": result_dict,
        }
    else:
        data = {"results": queryset}
    return data
