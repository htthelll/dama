# tasks.py
from celery import shared_task
from .models import Image, MarkerTxtPath, loaded_model, task_processor, input_shape
import torch
import cv2
from djangoProject import settings
import os
import shutil
import zipfile
from django.core.files.storage import default_storage


@shared_task
def process(marker):
    images = Image.objects.filter(marker=marker).order_by('marker')
    target_counts = []

    # process input image
    for image in images:
        img = cv2.imread(str(image.image_path))
        model_inputs, _ = task_processor.create_input(str(image.image_path), input_shape)

        # inference and calculate
        target_sum = 0
        with torch.no_grad():
            result = loaded_model.test_step(model_inputs)
        bbox = result[0].pred_instances.bboxes.numpy()
        label = result[0].pred_instances.labels.numpy()
        scores = result[0].pred_instances.scores.numpy()
        indices = [i for i in range(len(bbox))]
        for index, bbox, label_id, score in zip(indices, bbox, label, scores):
            [left, top, right, bottom], s = bbox.astype(int), score
            if (score < 0.3) | (label_id == 1):
                continue
            cv2.rectangle(img, (left, top), (right, bottom), (0, 0, 255), 3)
            cv2.imwrite(str(image.image_path), img)
            target_sum += 1
        target_counts.append(target_sum)

    # txt generate
    txt_path = f'static/txt/{marker}.txt'
    total_images = len(target_counts)
    total_targets = sum(target_counts)
    images_with_targets = sum(1 for count in target_counts if count > 0)

    os.makedirs(os.path.dirname(default_storage.path(txt_path)), exist_ok=True)
    with default_storage.open(txt_path, 'w') as file:
        file.write(f'总检测图片数: {total_images}\n')
        file.write(f'检测出雄蕊植株总数: {total_targets}\n')
        file.write(f'存在雄蕊植株的图片个数: {images_with_targets}\n')

        for index, count in enumerate(target_counts, start=1):
            if count > 0:
                file.write(f'第 {index} 图片存在 {count} 株雄蕊植株\n')
    marker_txt = MarkerTxtPath.objects.create(marker=marker, txt_path=txt_path)
    marker_txt.save()

    if marker is not None:
        image_records = images

        # 创建一个临时目录来存储文件
        temp_dir = os.path.join(settings.BASE_DIR, 'temp_download')
        zip_dir = os.path.join(settings.BASE_DIR, 'temp_zip')
        os.makedirs(temp_dir, exist_ok=True)
        os.makedirs(zip_dir, exist_ok=True)

        # 复制Image表中的文件到临时目录
        for record in image_records:
            image_path = record.image_path.path
            if os.path.exists(image_path):
                shutil.copy(image_path, temp_dir)

        # 复制MarkerTxtPath表中的txt文件到临时目录
        txt_path = marker_txt.txt_path.path
        if os.path.exists(txt_path):
            shutil.copy(txt_path, temp_dir)

        zip_filename = f'{marker}_data'
        zip_path = os.path.join(zip_dir, zip_filename)
        with zipfile.ZipFile(zip_path + '.zip', 'w') as zipf:
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    zipf.write(file_path, os.path.relpath(file_path, temp_dir))
        shutil.rmtree(temp_dir)

        images.update(is_processed=True)
        images.update(processing=False)
