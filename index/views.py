from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from djangoProject import settings
from .models import *
from users.models import UserInfo
from django.http import HttpResponse, HttpResponseRedirect, FileResponse
from django.core.files.storage import default_storage
import os
from django.http import JsonResponse
from .task import process


@login_required
def index(request):
    if request.method == "GET":
        return render(request, 'index.html')
    elif request.method == "POST":
        _id = request.session['id']
        marker = request.POST.get('text')
        if Image.objects.filter(marker=str(_id) + '-' + marker).count() > 0:
            return JsonResponse({'status': 'fail'})
        else:
            uploaded_images = request.FILES.getlist('image')
            current_user = UserInfo.objects.get(id=_id)
            image_instances = [
                Image(user=current_user, image_path=image, marker=(str(_id) + '-' + marker))
                for image in uploaded_images
            ]
            Image.objects.bulk_create(image_instances)

            return JsonResponse({'status': 'success'})


@login_required
def image_gallery(request):
    user_id = request.session.get('id')

    if user_id is not None:
        images_by_marker = {}
        images = Image.objects.filter(user_id=user_id).order_by('id')
        for image in images:
            if image.marker.split('-')[1] not in images_by_marker:
                images_by_marker[image.marker.split('-')[1]] = {
                    'is_processed': image.is_processed,
                    'processing': image.processing,
                    'count': Image.objects.filter(marker=image.marker).count(),
                    'data_name': image.marker
                }

        context = {'images_by_marker': images_by_marker}
        return render(request, 'zhanshi.html', context)
    else:
        return HttpResponse("请先登录")


def detect_marker_images(request, marker):
    images = Image.objects.filter(marker=marker).order_by('marker')
    images.update(processing=True)
    process.delay(marker)
    return JsonResponse({'status': 'success'})


def download_marker_images(request, marker):
    if marker is not None:
        zip_dir = os.path.join(settings.BASE_DIR, 'temp_zip')
        zip_filename = f'{marker}_data'
        zip_path = os.path.join(zip_dir, zip_filename)
        response = FileResponse(open(zip_path + '.zip', 'rb'), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{zip_filename}.zip"'

        return response
    else:
        return HttpResponse("Marker parameter is missing.", status=400)


def delete_marker_images(request, marker):
    records_to_delete = Image.objects.filter(marker=marker).order_by('marker')
    for record in records_to_delete:
        image_path = record.image_path.path
        if default_storage.exists(image_path):
            default_storage.delete(image_path)
    records_to_delete.delete()

    txt_to_delete = MarkerTxtPath.objects.filter(marker=marker).order_by('marker')
    for record in txt_to_delete:
        txt_path = record.txt_path.path
        if default_storage.exists(txt_path):
            default_storage.delete(txt_path)
    txt_to_delete.delete()

    zip_filename = f'{marker}_data'
    zip_dir = os.path.join(settings.BASE_DIR, 'temp_zip')
    zip_path = os.path.join(zip_dir, zip_filename)
    if default_storage.exists(zip_path + '.zip'):
        default_storage.delete(zip_path + '.zip')
    return JsonResponse({'status': 'success'})
