"""Build the dataset folder that train.py needs.

Put your Normal X-ray images in one folder and your Abnormal X-ray images in another, then run:

    python make_dataset.py --normal C:/xrays/normal --abnormal C:/xrays/abnormal --out data

It creates (70% train / 15% val / 15% test, images are COPIED, originals are untouched):

    data/train/0_Normal/    data/train/1_Abnormal/
    data/val/0_Normal/      data/val/1_Abnormal/
    data/test/0_Normal/     data/test/1_Abnormal/

The folder names start with 0_ and 1_ on purpose: train.py sorts class folders alphabetically,
and model.py expects class 0 = Normal, class 1 = Abnormal.
Then train:   python train.py --data ./data --epochs 5
"""
import argparse, os, random, shutil

EXT = (".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--normal", required=True, help="folder with NORMAL images")
    ap.add_argument("--abnormal", required=True, help="folder with ABNORMAL images")
    ap.add_argument("--out", default="data", help="output folder (default: data)")
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    random.seed(a.seed)
    for cls, src in (("0_Normal", a.normal), ("1_Abnormal", a.abnormal)):
        files = [os.path.join(r, f) for r, _, fs in os.walk(src) for f in fs if f.lower().endswith(EXT)]
        if len(files) < 10:
            raise SystemExit(f"Only {len(files)} images found in {src}. You need at least a few hundred per class for a useful model.")
        random.shuffle(files)
        n = len(files); n_tr = int(n * 0.70); n_va = int(n * 0.15)
        parts = {"train": files[:n_tr], "val": files[n_tr:n_tr + n_va], "test": files[n_tr + n_va:]}
        for split, fl in parts.items():
            d = os.path.join(a.out, split, cls); os.makedirs(d, exist_ok=True)
            for i, f in enumerate(fl):
                shutil.copy2(f, os.path.join(d, f"{i:05d}_" + os.path.basename(f)))
        print(f"{cls}: {n} images -> train {len(parts['train'])}, val {len(parts['val'])}, test {len(parts['test'])}")
    print(f"\nDone. Now run:  python train.py --data {a.out} --epochs 5")

if __name__ == "__main__":
    main()