from django.db import models
from users.models import UserInfo
from mmdeploy.apis.utils import build_task_processor
from mmdeploy.utils import get_input_shape, load_config


# Create your models here.
class Image(models.Model):
    user = models.ForeignKey(UserInfo, on_delete=models.CASCADE)
    marker = models.CharField(max_length=100, default="undefined")
    is_processed = models.BooleanField(default=False)
    processing = models.BooleanField(default=False)

    def image_upload_path(self, filename):
        user_folder = f'user_{self.user.id}'
        return f'static/images/{user_folder}/{filename}'

    image_path = models.ImageField(upload_to=image_upload_path)

    def __str__(self):
        return f"User: {self.user.username}"


class MarkerTxtPath(models.Model):
    marker = models.CharField(max_length=100, default="undefined")
    txt_path = models.FileField(upload_to='static/txt/', null=True, blank=True)

    def __str__(self):
        return f"Txt: {self.txt_path}, Marker: {self.marker}"


loaded_model = None
task_processor = None
input_shape = None


def load_model():
    global loaded_model, task_processor, input_shape
    deploy_cfg = 'static/depends/detection_onnxruntime_dynamic.py'
    model_cfg = 'static/depends/test2.py'
    device = 'cuda'
    backend_model = ['static/depends/end2end.onnx']
    deploy_cfg, model_cfg = load_config(deploy_cfg, model_cfg)
    task_processor = build_task_processor(model_cfg, deploy_cfg, device)
    loaded_model = task_processor.build_backend_model(backend_model)
    input_shape = get_input_shape(deploy_cfg)
