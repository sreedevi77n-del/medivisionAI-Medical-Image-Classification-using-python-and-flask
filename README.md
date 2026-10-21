# MediVision AI (Flask + HTML/CSS/JS, 15 pages)
## Run
    cd backend
    pip install -r requirements.txt
    python app.py          # open http://localhost:5000
## Get a REAL model (otherwise every result is labelled DEMO)
    pip install torch torchvision
    # put a 2-class dataset in backend/data/train|val|test/<class>/ (e.g. Kaggle "Chest X-Ray Images (Pneumonia)")
    cd backend && python train.py --data ./data --epochs 5
    python app.py          # banner disappears; Model Insights shows real measured metrics
Decision support only; not a diagnostic device. Needs clinical validation before any real use.
