# 🎯 Advanced Face Recognition System with Real-Time Detection, People Counting and Access Control

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10-blue?style=for-the-badge&logo=python">
  <img src="https://img.shields.io/badge/OpenCV-Computer%20Vision-green?style=for-the-badge&logo=opencv">
  <img src="https://img.shields.io/badge/AI-Deep%20Learning-red?style=for-the-badge">
</p>

---

# 📌 1. Project Overview

This project is an **Advanced Face Recognition System** that uses Artificial Intelligence and Computer Vision techniques to:

- Detect faces in real-time using a webcam
- Recognize known individuals
- Identify unknown persons
- Count the number of people present
- Control access using a blacklist system
- Trigger alerts for unauthorized persons

👉 This system can be used in **security, surveillance, smart buildings, and IoT applications**.

---

# 🧠 2. Key Features

## 🎥 Real-Time Face Detection
The system captures video from a webcam and detects faces instantly using OpenCV.

## 🧑 Face Recognition
It compares detected faces with a dataset of known individuals using the `face_recognition` library.

## 🚫 Blacklist Access Control
If a detected person belongs to a blacklist:
- Access is denied
- Alert is triggered

## 🔢 People Counting
Counts how many people appear in the camera frame.

## 🔊 Alert System
Audio or visual alerts are triggered when:
- Unknown person is detected
- Blacklisted person is detected

---

# 🛠️ 3. Technologies Used

| Technology | Role |
|----------|------|
| Python | Main programming language |
| OpenCV | Image & video processing |
| face_recognition | Face encoding & comparison |
| NumPy | Data processing |
| YOLO (Ultralytics) | Object detection (optional) |
| pyttsx3 | Audio alerts |

---

# 📂 4. Project Structure

```
Face-Recognition-System/
│── main.py                # Main application
│── dataset/               # Images of known people
│── models/                # Trained models (if any)
│── utils/                 # Helper functions
│── requirements.txt       # Dependencies
│── README.md              # Documentation
```

---

# ⚙️ 5. How the System Works

1. Start webcam
2. Capture video frames
3. Detect faces in each frame
4. Encode faces
5. Compare with known dataset
6. Identify person:
   - Known → display name
   - Unknown → alert
7. Check blacklist
8. Count number of people
9. Display results in real-time

---

# ▶️ 6. Installation Guide

## Step 1: Clone the repository
```
git clone https://github.com/BAIHA-Fatima-Ezzahrae/Face-Recognition-System-with-Real-Time-Detection-and-Access-Control.git
```

## Step 2: Navigate to project
```
cd Face-Recognition-System-with-Real-Time-Detection-and-Access-Control
```

## Step 3: Install dependencies
```
pip install -r requirements.txt
```

## Step 4: Run the project
```
python main.py
```

---

# 📸 7. Screenshots (Add yours)

Create a folder called `images/` and add:

- detection.png
- alert.png
- counting.png

Then display them like this:

```
![Detection](images/detection.png)
![Alert](images/alert.png)
![Counting](images/counting.png)
```

---

# 🎯 8. Use Cases

- 🏢 Company security systems
- 🏫 School attendance tracking
- 🚗 Smart parking systems
- 🛑 Surveillance and monitoring
- 🏠 Smart home security

---

# 🚀 9. Future Improvements

- Mobile application integration
- Cloud database support
- Multi-camera system
- Face mask detection
- Web dashboard

---

# 👩‍💻 10. Author

**BAIHA Fatima Ezzahrae**  
Master's Student in Data Analyst and AI 

**Boubker Fatima**  
Master's Student in Data Analyst and AI 

**Aya Jaouher**  
Master's Student in Data Analyst and AI 

---

# 📜 11. License

This project is developed for educational purposes.

---

# ⭐ 12. Support

If you like this project:
- ⭐ Star the repository
- 🍴 Fork it
- 💬 Share it

