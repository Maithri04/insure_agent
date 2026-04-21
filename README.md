# 🏥 Insure Agent  
AI-powered healthcare insurance approval system for doctors.InsureMind AI helps doctors generate SOAP notes and predict insurance approval using AI.

## 🎯 Problem Statement
Doctors often face insurance approval delays due to incomplete documentation, incorrect ICD coding, and weak clinical justification.
This leads to higher rejection rates and delays in patient treatment.
There is a need for an intelligent system that can generate structured reports, validate data, and predict approval outcomes.

## 💡 **Solution**
InsureMind AI assists doctors in preparing accurate pre-authorization reports by:
- Converting raw notes into structured SOAP format  
- Validating ICD-10 codes and procedure mappings  
- Detecting missing clinical evidence  
- Improving justification using AI  
- Predicting insurance approval probability  

## ⚙️ **Features**
- 📝 SOAP Note Generation  
- 🤖 Hybrid AI Agent (LLM + Rules + ML)  
- ⚠️ Risk & Missing Evidence Detection  
- 📊 Approval Probability Score (color-based)  
- 💬 Chatbot Assistant  
- 📄 PDF Report Download  
- 📚 Case History Tracking<img width="1613" height="768" alt="Screenshot 2026-04-21 135624" src="https://github.com/user-attachments/assets/e064a9e7-f603-4d56-9bef-2d94e125efab" />
<img width="1892" height="908" alt="Screenshot 2026-04-21 135712" src="https://github.com/user-attachments/assets/edea304b-eb3d-40a8-9edd-5386a29690a1" />
<img width="1895" height="899" alt="Screenshot 2026-04-21 135835" src="https://github.com/user-attachments/assets/663b9a7d-4fce-408a-a865-918d974687a7" />
<img width="1784" height="785" alt="Screenshot 2026-04-21 135909" src="https://github.com/user-attachments/assets/1feb3051-f099-4a40-b45e-e103f981c22e" />
<img width="1227" height="582" alt="Screenshot 2026-04-21 135920" src="https://github.com/user-attachments/assets/83f9bd93-9fc9-4a3a-9ee3-25beeca7a0ce" />
<img width="1878" height="881" alt="Screenshot 2026-04-21 135929" src="https://github.com/user-attachments/assets/13b95e05-1a5f-4b53-8fa3-42ac612e3f11" />
<img width="1804" height="796" alt="Screenshot 2026-04-21 140029" src="https://github.com/user-attachments/assets/0e01a9b6-ad67-401a-8066-cf470e53ceed" />
<img width="1867" height="880" alt="Screenshot 2026-04-21 140045" src="https://github.com/user-attachments/assets/a13491e6-1c65-48a4-bc5a-e6d0a4493f71" />


## 🤖 **Agent Workflow**

The InsureMind AI agent follows a structured 6-step pipeline:

### 1️⃣ Understand Patient (LLM)
- Takes raw doctor input (symptoms, notes, medications)
- Converts it into structured medical format (SOAP)
- Extracts key clinical entities

### 2️⃣ Validate Clinical Data (Rules + DB)
- Checks ICD-10 code correctness  
- Maps procedures with diagnosis  
- Ensures medical consistency  

### 3️⃣ Detect Issues & Missing Evidence
- Identifies missing clinical details:
  - Duration  
  - Severity  
  - Investigations  
  - Prior treatment  
- Flags incomplete or weak documentation  

### 4️⃣ Improve Justification (LLM Loop)
- Rewrites clinical justification for clarity  
- Strengthens medical reasoning  
- Iteratively improves (1–2 passes if needed)  

### 5️⃣ Risk Analysis
- Assigns risk levels:
  - 🔴 High  
  - 🟡 Medium  
  - 🟢 Low  
- Detects approval risks (missing data, conflicts)  

### 6️⃣ Approval Prediction (ML)
- Predicts insurance approval probability (0–100%)  
- Classifies:
  - Low approval chance  
  - Moderate  
  - High

### 📦 Final Output
- SOAP Report  
- Approval Score  
- Risk Flags  
- Missing Evidence Suggestions  
- Downloadable PDF

## 🛠️ **Tech Stack**
**Frontend**  
- React.js → Component-based UI development  
- Tailwind CSS → Clean, responsive styling  
- React Router → Navigation and routing  

**Backend**  
- FastAPI (Python) → High-performance API framework  
- Pydantic → Data validation and schema management  

**AI & ML**  
- Groq (LLaMA models) → Natural language processing (SOAP, justification)  
- Rule-based Engine → ICD validation, conflict detection  
- ML Model → Insurance approval prediction  

**Database**  
- PostgreSQL → Structured data (cases, reports)  
- MongoDB → Audit logs and activity tracking  

**DevOps**  
- Docker → Containerization  
- Docker Compose → Multi-service orchestration

**API Communication**  
- REST APIs → Frontend ↔ Backend integration

HOW TO RUN-
docker-compose up --build
MANUAL WAY-
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
cd frontend
npm install
npm run dev

🌐 API Endpoints
POST/soapGenerate- SOAP note
POST/agent-run-Run AI agent pipeline
GET/case/{id}-Fetch report
GET/history-Get all reports
POST/chat-Chatbot

Why This Project is Unique
Hybrid AI system (LLM + Rules + ML)
End-to-end workflow (input → analysis → prediction)
Explainable outputs (risk flags, missing evidence)
Real-world healthcare problem solving
Human-in-the-loop improvement capability
Full-stack system with AI + backend + frontend
