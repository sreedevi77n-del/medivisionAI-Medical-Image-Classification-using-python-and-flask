"""AI layer. REAL mode = your trained PyTorch weights in backend/weights/model.pt
(ResNet-50 + Grad-CAM). Without weights it runs in DEMO mode and says so in every response."""
import os, io, base64, hashlib
import numpy as np
from PIL import Image

CLASSES = ["Normal", "Abnormal"]          # change to match YOUR training classes
WEIGHTS = os.path.join(os.path.dirname(__file__), "weights", "model.pt")
_model = None

try:
    import torch, torchvision
    from torchvision import transforms
    if os.path.exists(WEIGHTS):
        _model = torchvision.models.resnet50(num_classes=len(CLASSES))
        _model.load_state_dict(torch.load(WEIGHTS, map_location="cpu"))
        _model.eval()
        _tf = transforms.Compose([transforms.Resize((224, 224)), transforms.ToTensor(),
              transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])
        _store = {}
        layer = _model.layer4[-1]   # last conv block = Grad-CAM target
        layer.register_forward_hook(lambda m, i, o: _store.__setitem__("a", o))
        layer.register_full_backward_hook(lambda m, gi, go: _store.__setitem__("g", go[0]))
except ImportError:
    pass

def is_real(): return _model is not None

def _b64(img, fmt="PNG"):
    buf = io.BytesIO(); img.save(buf, fmt)
    return "data:image/%s;base64,%s" % (fmt.lower(), base64.b64encode(buf.getvalue()).decode())

def _overlay(img, cam):
    """Blend a 0-1 attention map (jet-like colours) over the original image."""
    cam = np.asarray(Image.fromarray((cam * 255).astype("uint8")).resize(img.size, Image.BILINEAR)) / 255.0
    r, g, b = [np.clip(1.5 - np.abs(4 * cam - k), 0, 1) for k in (3, 2, 1)]
    heat = (np.stack([r, g, b], -1) * 255).astype("uint8")
    return Image.blend(img.convert("RGB"), Image.fromarray(heat), 0.45)

def predict(img):
    img = img.convert("RGB")
    if is_real():
        x = _tf(img).unsqueeze(0)
        out = _model(x); p = out.softmax(1)[0]; idx = int(p.argmax())
        _model.zero_grad(); out[0, idx].backward()          # Grad-CAM
        w = _store["g"].mean((2, 3), keepdim=True)
        cam = torch.relu((w * _store["a"]).sum(1))[0].detach().numpy()
        cam = (cam - cam.min()) / (cam.max() - cam.min() + 1e-8)
        probs = p.detach().numpy().tolist(); mode = "model"
    else:  # DEMO: fixed sample numbers + synthetic blob. NOT a prediction.
        h = int(hashlib.md5(img.tobytes()[:5000]).hexdigest(), 16)
        yy, xx = np.mgrid[0:56, 0:56]
        cx, cy = 14 + h % 28, 14 + (h >> 8) % 28
        cam = np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / 90.0)
        probs, idx, mode = [0.964, 0.036], 0, "demo"
    thumb = img.copy(); thumb.thumbnail((512, 512))
    return {"mode": mode, "label": CLASSES[idx], "confidence": round(probs[idx] * 100, 1),
            "probabilities": {c: round(q * 100, 1) for c, q in zip(CLASSES, probs)},
            "thumb": _b64(img.resize((160, 160)), "JPEG"), "original": _b64(thumb, "JPEG"), "heatmap": _b64(_overlay(thumb, cam))}