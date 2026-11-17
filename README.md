# MediVision AI – Explainable AI for Medical Imaging

<p align="center">
  <strong>AI-Powered Medical Image Classification & Explainable AI Platform</strong>
</p>

MediVision AI is a web-based medical imaging decision-support platform designed to assist healthcare professionals in reviewing medical images using Artificial Intelligence and Explainable AI (XAI).

The platform allows clinicians to upload X-ray, CT scan, and MRI images, process them using a Gemini vision model, view AI-generated classification results, explore attention heatmaps, manage patient records, and generate printable medical reports.

**Important:** MediVision AI is an AI-assisted decision-support system, not a certified medical diagnostic device. All results must be reviewed by qualified healthcare professionals.

---

## 🚀 Key Features

- Secure user registration and login.
- Interactive medical imaging dashboard.
- Medical image upload and processing.
- X-ray, CT scan, and MRI support.
- AI-based Normal / Abnormal classification.
- Confidence scores and classification probabilities.
- AI-generated medical findings and impressions.
- Explainable AI attention heatmap visualization.
- Ranked regions of influence.
- Patient record management.
- Medical image gallery.
- Scan history with search and filters.
- Analytics dashboard with interactive charts.
- AI model performance insights.
- Printable medical reports.
- User profile and password management.
- Help and support system.
- Responsive user interface.

## 📄 Website Pages (15 Pages)

| No. | Page | Description |
|---|---|---|
| 1 | Home | Project introduction and platform overview |
| 2 | Login | Secure user authentication |
| 3 | Sign Up | New user registration |
| 4 | Dashboard | Scan activity and statistics |
| 5 | Upload | Upload medical images |
| 6 | History | View previous scan records |
| 7 | Classification | View AI prediction results |
| 8 | Explainable AI | Visualize AI attention heatmaps |
| 9 | Gallery | Browse uploaded medical images |
| 10 | Patients | Manage patient records |
| 11 | Analytics | Visualize scan statistics |
| 12 | Model Insights | View model analysis insights |
| 13 | Reports | View and print scan reports |
| 14 | Profile | Manage user information |
| 15 | Support | Submit support requests |

## 🧠 AI Workflow

1. User creates an account and logs in.
2. User uploads an X-ray, CT, or MRI image.
3. The application validates and stores the uploaded image.
4. The backend creates a scan record with processing status.
5. The Gemini vision model analyzes the image.
6. The application receives classification results and findings.
7. The user views the prediction and confidence score.
8. Explainable AI visualizes influential image regions.
9. The user reviews the generated report.
10. The report can be printed or saved as PDF through the browser.

## 🔍 Explainable AI

MediVision AI includes an attention heatmap visualization to help users understand which image regions influenced the model output.

- Red and yellow areas indicate higher model influence.
- Heatmap opacity can be adjusted.
- Original and attention-overlay images can be compared.
- Ranked regions of influence are displayed.

**Note:** The attention overlay is generated from model-returned region coordinates. It is not a validated Grad-CAM explanation unless the underlying model specifically implements Grad-CAM.

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| Frontend | HTML5, CSS3, JavaScript |
| UI | Responsive CSS Design |
| Charts | Chart.js |
| Backend | Netlify Server |
| API Framework | Hono |
| Programming Language | TypeScript |
| Database | PostgreSQL |
| ORM | Drizzle ORM |
| Image Storage | Netlify Blobs |
| Image Optimization | Netlify Image CDN |
| AI Integration | Google Gemini Vision |
| Authentication | Scrypt Password Hashing |
| Session Management | Secure Opaque Session Tokens |

## 📂 Project Structure

```text
MediVision-AI/
│
├── public/
│   ├── index.html
│   ├── login.html
│   ├── signup.html
│   ├── dashboard.html
│   ├── upload.html
│   ├── history.html
│   ├── classification.html
│   ├── explainable-ai.html
│   ├── gallery.html
│   ├── patients.html
│   ├── analytics.html
│   ├── model-insights.html
│   ├── report.html
│   ├── profile.html
│   ├── support.html
│   │
│   ├── css/
│   │   └── style.css
│   │
│   ├── js/
│   │   └── app.js
│   │
│   └── img/
│
├── netlify/
│   ├── server/
│   │   └── index.ts
│   └── database/
│       └── migrations/
│
├── server/
│   ├── auth.ts
│   ├── analyze.ts
│   └── storage.ts
│
├── db/
│   ├── index.ts
│   └── schema.ts
│
├── drizzle.config.ts
├── netlify.toml
├── package.json
├── package-lock.json
└── README.md
```

## ⚙️ Installation and Setup

### 1. Clone the Repository

```bash
https://github.com/sreedevi77n-del/medivisionAI-Medical-Image-Classification-using-python-and-flask.git
```

### 2. Open the Project

```bash
cd MediVision-AI
```

### 3. Install Dependencies

```bash
npm install
```

### 4. Run the Application

```bash
npx netlify dev --port 8889
```

### 5. Open in Browser

```text
http://localhost:8889
```

Create an account and log in to access the application.

**Prerequisites:**
- Node.js and npm
- Netlify CLI
- Netlify Database configuration
- Netlify Blobs configuration
- Netlify AI Gateway access

For local development, ensure your Netlify project and required services are configured.

## 🔐 Security

- Passwords are hashed using scrypt.
- Session tokens are stored as hashes.
- API endpoints require authentication.
- Database queries are scoped to the authenticated user.
- Uploaded images use random UUID-based storage keys.
- Image uploads have a 10 MB size limit.

## 📊 Database Tables

The application uses PostgreSQL with Drizzle ORM.

| Table | Purpose |
|---|---|
| users | User accounts |
| sessions | Authentication sessions |
| scans | Medical scan records and AI results |
| patients | Patient information |
| support_messages | User support requests |

## 🔮 Future Enhancements

- Password reset through email.
- Multi-user healthcare organizations.
- Shared patient records.
- DICOM image upload support.
- Dedicated administrator dashboard.
- Integration with validated medical imaging models.
- Clinician review and approval workflow.

## ⚠️ Medical Disclaimer

MediVision AI is an academic and AI-assisted medical imaging project. Its predictions, confidence scores, findings, and visual explanations are a substitute for professional medical advice, diagnosis, or treatment.

A qualified healthcare professional must independently review all results before making clinical decisions.

## 👩‍💻 Project Information

**Project Name:** MediVision AI

**Project Title:** Deep Learning-Based Medical Image Classification with Explainable AI

**Project Category:** Artificial Intelligence / Machine Learning / Healthcare

**Application Type:** Web-Based Medical Imaging Decision-Support Platform

---

<p align="center">
  <strong>MediVision AI – Making Medical Imaging Analysis More Explainable.</strong>
</p>

 
  
       
