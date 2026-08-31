# Model weights

Drop your trained checkpoints here:

- `yolov8_dental.pt` - YOLOv8 model trained on the 8-class dental label set
- `yolov12_dental.pt` - YOLOv12 model trained on the same label set

Class order must match `backend/app/ml/labels.py::LABELS`:

```
0 healthy_tooth
1 cavity
2 gum_inflammation
3 plaque
4 tartar
5 tooth_discoloration
6 cracked_tooth
7 missing_tooth
```

Once both files are present, set `USE_MOCK_MODEL=false` in `.env` (or
`docker-compose.yml`) and restart the backend. Until then, the API runs in
mock mode: it returns deterministic, realistic-looking detections so the
rest of the stack (dashboard, patient records, prevention plans, KNN
recommender) is fully testable without waiting on training.
