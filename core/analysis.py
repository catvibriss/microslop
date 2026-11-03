def iou(a, b):
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    intersection = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    aa = max(0.0, a[2] - a[0]) * max(0.0, a[3] - a[1])
    ab = max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])
    union = aa + ab - intersection
    return intersection / union if union > 0 else 0.0

def merge_passes(passes, match_iou=0.45, nms_iou=0.45, min_votes=2, cross_class_iou=0.55):
    clusters = []
    for pass_index, detections in enumerate(passes):
        for box in sorted(detections, key=lambda b: float(b[5]), reverse=True):
            if len(box) != 6 or float(box[5]) <= 0:
                continue
            best = None
            best_iou = match_iou
            for cluster in clusters:
                if pass_index in cluster['passes'] or cluster['label'] != box[4]:
                    continue
                overlap = iou(box, cluster['representative'])
                if overlap >= best_iou:
                    best_iou, best = overlap, cluster
            if best is None:
                clusters.append({'label': box[4], 'passes': {pass_index},
                                 'boxes': [box], 'representative': box})
            else:
                best['passes'].add(pass_index)
                best['boxes'].append(box)
                boxes = best['boxes']
                best['representative'] = (*(
                    sum(float(b[i]) for b in boxes) / len(boxes) for i in range(4)
                ), best['label'], sum(float(b[5]) for b in boxes) / len(boxes))

    candidates = []
    for group in clusters:
        if len(group['passes']) < min_votes:
            continue
        boxes = group['boxes']
        weights = [float(b[5]) for b in boxes]
        total = sum(weights)
        coords = [sum(float(b[i]) * w for b, w in zip(boxes, weights)) / total for i in range(4)]
        candidates.append((*coords, group['label'], sum(weights) / len(weights)))

    final = []
    for box in sorted(candidates, key=lambda b: b[5], reverse=True):
        if not any(box[4] == chosen[4] and iou(box, chosen) >= nms_iou
                   for chosen in final):
            final.append(box)

    result = []
    for box in final:
        if not any(box[4] != chosen[4] and iou(box, chosen) >= cross_class_iou
                   for chosen in result):
            result.append(box)
    return result
