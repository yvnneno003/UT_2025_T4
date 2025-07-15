from mmengine.utils import ProgressBar
from pycocotools.coco import COCO
from mmengine.fileio import dump, load
from mmdet.models.utils import weighted_boxes_fusion
import json

def filter_val_label(val_label_path, thresh_hold = [0.445, 0.426, 0.433, 0.420, 0.401]):
    val_json_data = json.load(open(val_label_path))
    new_json_data = []
    for annotation in val_json_data:
        if annotation['score'] < thresh_hold[0] and annotation['category_id'] == 0: continue #bus
        if annotation['score'] < thresh_hold[1] and annotation['category_id'] == 1: continue #bike
        if annotation['score'] < thresh_hold[2] and annotation['category_id'] == 2: continue #car
        if annotation['score'] < thresh_hold[3] and annotation['category_id'] == 3: continue #pedestrian
        if annotation['score'] < thresh_hold[4] and annotation['category_id'] == 4: continue #truck
        new_json_data.append(annotation)
    return new_json_data

annotation = '../datasets/val.json'

pred_results = [
                'my/yolov10x_vfp_1280_train4_best_conf_0.5_iou_0.65.json',
                'ch/1-y13l_b57_495_50.json',
                'my/yolor_d64-92-1280SPP-gamma-e90-conf0.5-iou0.55.json',
                ]
out_file = 'final.json'
weights = [9,9,9]

fusion_iou_thr = 0.65#0.75
skip_box_thr = 0.15
# conf_type = 'avg'

cocoGT = COCO(annotation)

predicts_raw = []

models_name = ['model_' + str(i) for i in range(len(pred_results))]

for model_name, path in \
            zip(models_name, pred_results):
        pred = load(path)
        predicts_raw.append(pred)

predict = {
        str(image_id): {
            'bboxes_list': [[] for _ in range(len(predicts_raw))],
            'scores_list': [[] for _ in range(len(predicts_raw))],
            'labels_list': [[] for _ in range(len(predicts_raw))]
        }
        for image_id in cocoGT.getImgIds()
    }

for i, pred_single in enumerate(predicts_raw):
        for pred in pred_single:
            p = predict[str(pred['image_id'])]
            p['bboxes_list'][i].append([pred['bbox'][0], pred['bbox'][1], pred['bbox'][0] + pred['bbox'][2], pred['bbox'][1] + pred['bbox'][3]])
            # p['bboxes_list'][i].append(pred['bbox'])
            p['scores_list'][i].append(pred['score'])
            p['labels_list'][i].append(pred['category_id'])

result = []
prog_bar = ProgressBar(len(predict))
for image_id, res in predict.items():
    bboxes, scores, labels = weighted_boxes_fusion(
        res['bboxes_list'],
        res['scores_list'],
        res['labels_list'],
        weights=weights,
        iou_thr=fusion_iou_thr,
        skip_box_thr=skip_box_thr)

    for bbox, score, label in zip(bboxes, scores, labels):
        bbox_copy = bbox.numpy().tolist()
        bbox_copy[2] = bbox_copy[2] - bbox_copy[0]
        bbox_copy[3] = bbox_copy[3] - bbox_copy[1]
        result.append({
            'bbox': bbox_copy,
            'category_id': int(label),
            'image_id': int(image_id),
            'score': float(score)
        })
    prog_bar.update()
dump(result, file=out_file)

day_label = filter_val_label(out_file, [0.3, 0.3, 0.3, 0.3, 0.25])
night_label = filter_val_label(out_file, [0.1, 0.15, 0.2, 0.15, 0.2])

final_json_data = []
for annotation in day_label:
    image_id = annotation["image_id"]
   
    if not str(image_id).startswith("293"):
        final_json_data.append(annotation)

for annotation in night_label:
    image_id = annotation["image_id"]

    if str(image_id).startswith("293"):
        final_json_data.append(annotation)

json.dump(final_json_data, open(out_file, "w"))



