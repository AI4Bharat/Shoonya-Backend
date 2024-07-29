# from .decorators import is_admin
# from rest_framework.response import Response
# from rest_framework import status
# from rest_framework.decorators import action, api_view
# from .models import Organization
#
#
# @api_view(['GET'])
# def read_project_permission(request):
#     org = Organization.objects.get(id=request.user.organization.id)
#     project_permissions = org.permission_json["PROJECT_PERMISSIONS"]
#     permission_name = request.query_params.get("permission_name")
#     if permission_name is None:
#         return Response(
#             {"message": "Permission name is required"},
#             status=status.HTTP_400_BAD_REQUEST,
#         )
#     pm = project_permissions.get(permission_name)
#     if pm is None:
#         return Response(
#             {"message": "Permission not found"}, status=status.HTTP_404_NOT_FOUND
#         )
#     return Response({"permission": list(pm)}, status=status.HTTP_200_OK)
#
# @is_admin
# @api_view(['POST'])
# def delete_project_permission(request):
#     org = Organization.objects.get(id=request.user.organization.id)
#     project_permissions = org.permission_json["PROJECT_PERMISSIONS"]
#     permission_name = request.query_params.get("permission_name")
#     if permission_name is None:
#         return Response(
#             {"message": "Permission name is required"},
#             status=status.HTTP_400_BAD_REQUEST,
#         )
#     if permission_name in project_permissions:
#         del project_permissions[permission_name]
#     else:
#         print(f"Permission '{permission_name}' not found")
#     org["PROJECT_PERMISSIONS"] = project_permissions
#     org.save()
#     return Response(
#         {"message": "Permission deleted"},
#         status=status.HTTP_200_OK,
#     )
#
#
# @api_view(['POST'])
# @is_admin
# def update_project_permission(request):
#     org = Organization.objects.get(id=request.user.organization.id)
#     project_permissions = org.permission_json["PROJECT_PERMISSIONS"]
#     permission_name = request.query_params.get("permission_name")
#     new_roles = request.data.get("new_roles")
#     if permission_name is None:
#         return Response(
#             {"message": "Permission name is required"},
#             status=status.HTTP_400_BAD_REQUEST,
#         )
#     if not new_roles:
#         return Response(
#             {"message": "New Roles is required"},
#             status=status.HTTP_400_BAD_REQUEST,
#         )
#     if permission_name in project_permissions:
#         project_permissions[permission_name] = new_roles
#     else:
#         print(f"Permission '{permission_name}' not found")
#     return Response(
#         {"message": "Permission updated"},
#         status=status.HTTP_200_OK,
#     )
#
#
# @api_view(['GET'])
# def read_dataset_permission(request):
#     org = Organization.objects.get(id=request.user.organization.id)
#     dataset_permissions = org.permission_json["DATASET_PERMISSIONS"]
#     permission_name = request.query_params.get("permission_name")
#     if permission_name is None:
#         return Response(
#             {"message": "Permission name is required"},
#             status=status.HTTP_400_BAD_REQUEST,
#         )
#     pm = dataset_permissions.get(permission_name)
#     if pm is None:
#         return Response(
#             {"message": "Permission not found"}, status=status.HTTP_404_NOT_FOUND
#         )
#     return Response({"permission": list(pm)}, status=status.HTTP_200_OK)
#
#
# @api_view(['POST'])
# @is_admin
# def delete_dataset_permission(request):
#     org = Organization.objects.get(id=request.user.organization.id)
#     dataset_permissions = org.permission_json["DATASET_PERMISSIONS"]
#     permission_name = request.query_params.get("permission_name")
#     if permission_name is None:
#         return Response(
#             {"message": "Permission name is required"},
#             status=status.HTTP_400_BAD_REQUEST,
#         )
#     if permission_name in dataset_permissions:
#         del dataset_permissions[permission_name]
#     else:
#         print(f"Permission '{permission_name}' not found")
#     return Response(
#         {"message": "Permission deleted"},
#         status=status.HTTP_200_OK,
#     )
#
#
# @api_view(['POST'])
# @is_admin
# def update_dataset_permission(request):
#     org = Organization.objects.get(id=request.user.organization.id)
#     dataset_permissions = org.permission_json["DATASET_PERMISSIONS"]
#     permission_name = request.query_params.get("permission_name")
#     new_roles = request.data.get("new_roles")
#     if permission_name is None:
#         return Response(
#             {"message": "Permission name is required"},
#             status=status.HTTP_400_BAD_REQUEST,
#         )
#     if not new_roles:
#         return Response(
#             {"message": "New Roles is required"},
#             status=status.HTTP_400_BAD_REQUEST,
#         )
#     if permission_name in dataset_permissions:
#         dataset_permissions[permission_name] = new_roles
#     else:
#         print(f"Permission '{permission_name}' not found")
#     return Response(
#         {"message": "Permission updated"},
#         status=status.HTTP_200_OK,
#     )


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Organization
from .decorators import is_admin


class ProjectPermissionView(APIView):
    def get(self, request, *args, **kwargs):
        org = Organization.objects.get(id=request.user.organization.id)
        project_permissions = org.permission_json["PROJECT_PERMISSIONS"]
        permission_name = request.query_params.get("permission_name")
        if permission_name is None:
            return Response(
                {"message": "Permission name is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        pm = project_permissions.get(permission_name)
        if pm is None:
            return Response(
                {"message": "Permission not found"}, status=status.HTTP_404_NOT_FOUND
            )
        return Response({"permission": list(pm)}, status=status.HTTP_200_OK)

    @is_admin
    def post(self, request, *args, **kwargs):
        org = Organization.objects.get(id=request.user.organization.id)
        project_permissions = org.permission_json["PROJECT_PERMISSIONS"]
        permission_name = request.query_params.get("permission_name")
        if permission_name is None:
            return Response(
                {"message": "Permission name is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        new_roles = request.data.get("new_roles")
        if not new_roles:
            return Response(
                {"message": "New Roles are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if permission_name in project_permissions:
            project_permissions[permission_name].append(new_roles)
        else:
            project_permissions[permission_name] = [new_roles]
        org.permission_json["PROJECT_PERMISSIONS"] = project_permissions
        org.save()
        return Response(
            {"message": "Permission updated"},
            status=status.HTTP_200_OK,
        )

    @is_admin
    def delete(self, request, *args, **kwargs):
        org = Organization.objects.get(id=request.user.organization.id)
        project_permissions = org.permission_json["PROJECT_PERMISSIONS"]
        permission_name = request.query_params.get("permission_name")
        if permission_name is None:
            return Response(
                {"message": "Permission name is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if permission_name in project_permissions:
            del project_permissions[permission_name]
        else:
            print(f"Permission '{permission_name}' not found")
        org.permission_json["PROJECT_PERMISSIONS"] = project_permissions
        org.save()
        return Response(
            {"message": "Permission deleted"},
            status=status.HTTP_200_OK,
        )


class DatasetPermissionView(APIView):
    def get(self, request, *args, **kwargs):
        org = Organization.objects.get(id=request.user.organization.id)
        dataset_permissions = org.permission_json["DATASET_PERMISSIONS"]
        permission_name = request.query_params.get("permission_name")
        if permission_name is None:
            return Response(
                {"message": "Permission name is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        pm = dataset_permissions.get(permission_name)
        if pm is None:
            return Response(
                {"message": "Permission not found"}, status=status.HTTP_404_NOT_FOUND
            )
        return Response({"permission": list(pm)}, status=status.HTTP_200_OK)

    @is_admin
    def post(self, request, *args, **kwargs):
        org = Organization.objects.get(id=request.user.organization.id)
        dataset_permissions = org.permission_json["DATASET_PERMISSIONS"]
        permission_name = request.query_params.get("permission_name")
        if permission_name is None:
            return Response(
                {"message": "Permission name is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        new_roles = request.data.get("new_roles")
        if not new_roles:
            return Response(
                {"message": "New Roles are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if permission_name in dataset_permissions:
            dataset_permissions[permission_name].append(new_roles)
        else:
            dataset_permissions[permission_name] = [new_roles]
        org.permission_json["DATASET_PERMISSIONS"] = dataset_permissions
        org.save()
        return Response(
            {"message": "Permission updated"},
            status=status.HTTP_200_OK,
        )

    @is_admin
    def delete(self, request, *args, **kwargs):
        org = Organization.objects.get(id=request.user.organization.id)
        dataset_permissions = org.permission_json["DATASET_PERMISSIONS"]
        permission_name = request.query_params.get("permission_name")
        if permission_name is None:
            return Response(
                {"message": "Permission name is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if permission_name in dataset_permissions:
            del dataset_permissions[permission_name]
        else:
            print(f"Permission '{permission_name}' not found")
        org.permission_json["DATASET_PERMISSIONS"] = dataset_permissions
        org.save()
        return Response(
            {"message": "Permission deleted"},
            status=status.HTTP_200_OK,
        )
