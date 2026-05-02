import warnings
import os
import re

# Suppression spécifique du warning pkg_resources
warnings.filterwarnings("ignore", category=UserWarning, module="face_recognition_models")
# Suppression également des autres warnings FutureWarning
warnings.filterwarnings("ignore", category=FutureWarning)

import cv2
import numpy as np
import face_recognition
from ultralytics import YOLO
from collections import defaultdict
from datetime import datetime
import time
import streamlit as st
from PIL import Image
import tempfile

# ===========================
# 🔊 MEMBRE 3 - ALERTES VOCALES (CORRIGÉ POUR STREAMLIT)
# ===========================
import pyttsx3
import threading

def dire(message):
    """Joue un message vocal sans bloquer le programme principal et sans crasher Streamlit"""
    print(f"🔊 [MEMBRE 3] {message}")
    
    def _jouer():
        try:
            # IMPORTANT: Sur Windows, l'utilisation de pyttsx3 dans un nouveau thread (comme le fait Streamlit)
            # nécessite d'initialiser COM pour éviter les plantages ou les blocages.
            import pythoncom
            pythoncom.CoInitialize()
            
            engine = pyttsx3.init()
            engine.setProperty('rate', 160)
            engine.setProperty('volume', 1.0)
            
            # Chercher une voix française
            voices = engine.getProperty('voices')
            for voice in voices:
                if 'fr' in voice.id.lower() or 'french' in voice.name.lower():
                    engine.setProperty('voice', voice.id)
                    break
                    
            engine.say(message)
            engine.runAndWait()
            
            pythoncom.CoUninitialize()
        except Exception as e:
            print(f"⚠️ Erreur audio: {e}")
    
    # Démarrer dans un thread séparé
    threading.Thread(target=_jouer, daemon=True).start()

# ── Variables globales Membre 3 ──────────────────────────
if 'alerte_limite_jouee' not in st.session_state:
    st.session_state.alerte_limite_jouee = False
if 'derniere_alerte_temps' not in st.session_state:
    st.session_state.derniere_alerte_temps = 0.0

# ── Blacklist — dossier persistant ────────────────────────
BLACKLIST_DOSSIER = "blacklist"

def charger_blacklist():
    """Charge les encodages depuis le dossier blacklist/ au demarrage."""
    encodings, names = [], []
    if not os.path.exists(BLACKLIST_DOSSIER):
        os.makedirs(BLACKLIST_DOSSIER)
        return encodings, names
    for fichier in os.listdir(BLACKLIST_DOSSIER):
        if fichier.lower().endswith(('.jpg', '.jpeg', '.png')):
            nom_f = os.path.splitext(fichier)[0]
            chemin = os.path.join(BLACKLIST_DOSSIER, fichier)
            try:
                img = face_recognition.load_image_file(chemin)
                encs = face_recognition.face_encodings(img)
                if encs:
                    encodings.append(encs[0])
                    names.append(nom_f)
            except:
                pass
    return encodings, names

# ── Variables globales Mode Securite ──────────────────────
if 'blacklist_encodings' not in st.session_state:
    _encs, _nms = charger_blacklist()
    st.session_state.blacklist_encodings = _encs
    st.session_state.blacklist_names     = _nms
if 'security_log' not in st.session_state:
    st.session_state.security_log = []
if 'securite_alertes_temps' not in st.session_state:
    st.session_state.securite_alertes_temps = {}
if 'derniere_alerte_limite_temps' not in st.session_state:
    st.session_state.derniere_alerte_limite_temps = 0.0

LIMITE_PERSONNES = 1

def membre3_alerte_personne_trouvee(nom, confiance):
    """Appeler quand la personne recherchee est detectee (camera mode 2)"""
    maintenant = time.time()
    if maintenant - st.session_state.derniere_alerte_temps >= 5:
        st.session_state.derniere_alerte_temps = maintenant
        dire(f"{nom} detectee, confiance {confiance:.0%}")

def membre3_alerte_nouveau_comptage(compteur, nom=""):
    if compteur > LIMITE_PERSONNES and not st.session_state.alerte_limite_jouee:
        st.session_state.alerte_limite_jouee = True
        msg_limite = f"Attention ! Vous avez depasse la limite de {LIMITE_PERSONNES} personnes !"
        print(f"[MEMBRE 3] {msg_limite}")
        dire(msg_limite)

def membre3_reset():
    st.session_state.alerte_limite_jouee = False
    st.session_state.derniere_alerte_limite_temps = 0.0
    st.session_state.derniere_alerte_temps = 0.0
    dire("Compteur remis a zero.")

# ===========================
# 1. CHARGER LES IMAGES DE REFERENCE
# ===========================
def normaliser_nom(nom):
    """Supprime le suffixe _N pour regrouper plusieurs images d'une meme personne.
    Exemples : Ahmed_1 -> Ahmed  |  Ali_2 -> Ali  |  Sara -> Sara
    """
    return re.sub(r'_\d+$', '', nom)

@st.cache_data
def charger_references_face_recognition():
    known_encodings = []
    known_names = []
    
    dossier = "personnes_reference"
    
    if not os.path.exists(dossier):
        os.makedirs(dossier)
        return known_encodings, known_names
    
    for fichier in os.listdir(dossier):
        if fichier.lower().endswith(('.jpg', '.jpeg', '.png')):
            nom_brut = os.path.splitext(fichier)[0]
            nom      = normaliser_nom(nom_brut)   # Ahmed_1 -> Ahmed
            chemin   = os.path.join(dossier, fichier)
            
            try:
                image    = face_recognition.load_image_file(chemin)
                encodings = face_recognition.face_encodings(image)
                
                if encodings:
                    known_encodings.append(encodings[0])
                    known_names.append(nom)
            except Exception:
                pass
    
    return known_encodings, known_names

# ===========================
# 2. ANALYSE D'UNE IMAGE
# ===========================
def analyser_image(uploaded_file):
    if uploaded_file is None:
        st.error("Veuillez sélectionner une image")
        return
    
    known_encodings, known_names = charger_references_face_recognition()
    
    if not known_encodings:
        st.error("AUCUNE RÉFÉRENCE CHARGÉE! Ajoutez des photos dans le dossier 'personnes_reference'.")
        return
    
    # Sauvegarder l'image temporairement
    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        chemin_image = tmp_file.name
    
    image = cv2.imread(chemin_image)
    if image is None:
        st.error("Impossible de charger l'image")
        return
    
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    with st.spinner("Analyse en cours..."):
        face_locations = face_recognition.face_locations(rgb_image)
        face_encodings = face_recognition.face_encodings(rgb_image, face_locations)
    
    compteur_reconnus = 0
    compteur_inconnus = 0
    stats_personnes = defaultdict(int)
    
    for i, (face_encoding, (top, right, bottom, left)) in enumerate(zip(face_encodings, face_locations)):
        matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=0.5)
        name = "Inconnu"
        couleur = (255, 0, 0) # RGB Red
        
        if any(matches):
            face_distances = face_recognition.face_distance(known_encodings, face_encoding)
            best_match_index = np.argmin(face_distances)
            if matches[best_match_index]:
                name = known_names[best_match_index]
                confidence = 1 - face_distances[best_match_index]
                couleur = (0, 255, 0) # RGB Green
                compteur_reconnus += 1
                stats_personnes[name] += 1
            else:
                compteur_inconnus += 1
        else:
            compteur_inconnus += 1
        
        cv2.rectangle(rgb_image, (left, top), (right, bottom), couleur, 3)
        cv2.putText(rgb_image, name, (left, top-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, couleur, 2)
    
    # Afficher les résultats
    col1, col2 = st.columns([2, 1])
    with col1:
        st.image(rgb_image, caption="Résultat", use_container_width=True)
    with col2:
        st.subheader("📊 Statistiques")
        st.metric("Total visages", len(face_locations))
        st.metric("Visages reconnus", compteur_reconnus)
        st.metric("Visages inconnus", compteur_inconnus)
        
        if stats_personnes:
            st.write("**Personnes identifiées:**")
            for personne, count in stats_personnes.items():
                st.write(f"- {personne}: {count} fois")
    
    # Nettoyer
    os.unlink(chemin_image)

# ===========================
# 3. RECHERCHE D'UNE PERSONNE EN MODE CAMÉRA
# ===========================
def rechercher_personne_camera_avec_image(uploaded_file, nom_personne):
    if uploaded_file is None:
        st.error("Veuillez sélectionner une image de référence")
        return
    
    if not nom_personne:
        st.error("Veuillez entrer un nom pour la personne")
        return
    
    # Sauvegarder l'image temporairement
    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        chemin_image_recherche = tmp_file.name
    
    with st.spinner("Analyse de l'image fournie..."):
        image_recherche = face_recognition.load_image_file(chemin_image_recherche)
        encodings_recherche = face_recognition.face_encodings(image_recherche)
    
    if not encodings_recherche:
        st.error("Aucun visage détecté dans l'image fournie!")
        dire("Aucun visage détecté dans l'image fournie")
        os.unlink(chemin_image_recherche)
        return
    
    encodage_cible = encodings_recherche[0]
    
    SEUIL_RECONNAISSANCE = 0.5
    TAUX_REDUCTION = 0.5
    
    st.info(f"🔍 Recherche de '{nom_personne}' en cours... Décochez la case pour arrêter.")
    
    run_camera = st.checkbox("🎥 Démarrer la recherche", value=True)
    frame_placeholder = st.empty()
    
    if run_camera:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            st.error("Impossible d'ouvrir la caméra !")
            os.unlink(chemin_image_recherche)
            return
        
        alerte_sonore = True
        
        while run_camera:
            ret, frame = cap.read()
            if not ret:
                break
            
            small_frame = cv2.resize(frame, (0, 0), fx=TAUX_REDUCTION, fy=TAUX_REDUCTION)
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            
            face_locations = face_recognition.face_locations(rgb_small_frame)
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations, num_jitters=0)
            personne_trouvee = False
            
            for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                match = face_recognition.compare_faces([encodage_cible], face_encoding, tolerance=SEUIL_RECONNAISSANCE)
                
                top = int(top / TAUX_REDUCTION)
                right = int(right / TAUX_REDUCTION)
                bottom = int(bottom / TAUX_REDUCTION)
                left = int(left / TAUX_REDUCTION)
                
                if match[0]:
                    personne_trouvee = True
                    distances = face_recognition.face_distance([encodage_cible], face_encoding)
                    confiance = 1 - distances[0]
                    
                    cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 3)
                    cv2.putText(frame, f"{nom_personne} ({confiance:.1%})", (left, top-10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                    cv2.putText(frame, "!!! PERSONNE DETECTEE !!!", (50, 100), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
                    
                    if alerte_sonore:
                        membre3_alerte_personne_trouvee(nom_personne, confiance)
                else:
                    cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
                    cv2.putText(frame, "Autre personne", (left, top-10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            
            status = "TROUVEE" if personne_trouvee else "RECHERCHE EN COURS"
            couleur_status = (0, 255, 0) if personne_trouvee else (0, 0, 255)
            
            cv2.rectangle(frame, (10, 10), (450, 150), (0, 0, 0), -1)
            cv2.putText(frame, f"RECHERCHE: {nom_personne}", (20, 40), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(frame, f"Statut: {status}", (20, 70), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, couleur_status, 2)
            
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_placeholder.image(frame_rgb, channels="RGB", use_container_width=True)
            
        cap.release()
    
    try:
        os.unlink(chemin_image_recherche)
    except:
        pass

# ===========================
# 4. RECHERCHER UNE PERSONNE DANS UNE VIDÉO
# ===========================
def rechercher_personne_dans_video(image_uploaded, video_uploaded, nom_personne):
    if image_uploaded is None:
        st.error("Veuillez sélectionner une image de référence")
        return
    
    if video_uploaded is None:
        st.error("Veuillez sélectionner une vidéo")
        return
    
    if not nom_personne:
        st.error("Veuillez entrer un nom pour la personne")
        return
    
    # Sauvegarder les fichiers temporairement
    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_img:
        tmp_img.write(image_uploaded.getvalue())
        chemin_image_recherche = tmp_img.name
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_vid:
        tmp_vid.write(video_uploaded.getvalue())
        chemin_video = tmp_vid.name
    
    with st.spinner("Analyse de l'image..."):
        image_recherche = face_recognition.load_image_file(chemin_image_recherche)
        encodings_recherche = face_recognition.face_encodings(image_recherche)
    
    if not encodings_recherche:
        st.error("Aucun visage détecté dans l'image!")
        dire("Aucun visage détecté dans l'image fournie")
        os.unlink(chemin_image_recherche)
        os.unlink(chemin_video)
        return
    
    encodage_cible = encodings_recherche[0]
    
    SEUIL_RECONNAISSANCE = 0.5
    TAUX_REDUCTION = 0.5
    
    cap = cv2.VideoCapture(chemin_video)
    if not cap.isOpened():
        st.error("Impossible d'ouvrir la vidéo!")
        return
    
    FPS = int(cap.get(cv2.CAP_PROP_FPS))
    if FPS == 0: FPS = 30
    frame_count = 0
    extraction_interval = max(1, FPS // 4)
    
    personne_trouvee = False
    progress_bar = st.progress(0)
    status_text = st.empty()
    video_placeholder = st.empty()
    
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    run_video = st.checkbox("▶️ Démarrer l'analyse de la vidéo", value=True)
    
    if run_video:
        while run_video:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            if total_frames > 0:
                progress = min(frame_count / total_frames, 1.0)
                progress_bar.progress(progress)
            
            if frame_count % extraction_interval == 0:
                small_frame = cv2.resize(frame, (0, 0), fx=TAUX_REDUCTION, fy=TAUX_REDUCTION)
                rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
                
                face_locations = face_recognition.face_locations(rgb_small_frame)
                face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
                
                temps_actuel = frame_count / FPS
                
                for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                    match = face_recognition.compare_faces([encodage_cible], face_encoding, tolerance=SEUIL_RECONNAISSANCE)
                    
                    if match[0]:
                        if not personne_trouvee:
                            personne_trouvee = True
                            minutes = int(temps_actuel // 60)
                            secondes = int(temps_actuel % 60)
                            status_text.success(f"✅ {nom_personne} TROUVÉ(E) à {minutes:02d}:{secondes:02d} !")
                            dire(f"{nom_personne} trouvée dans la vidéo")
                        
                        top = int(top / TAUX_REDUCTION)
                        right = int(right / TAUX_REDUCTION)
                        bottom = int(bottom / TAUX_REDUCTION)
                        left = int(left / TAUX_REDUCTION)
                        cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 3)
                        cv2.putText(frame, f"{nom_personne} (TROUVEE!)", (left, top-10), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            video_placeholder.image(frame_rgb, channels="RGB", use_container_width=True)
        
        cap.release()
        
        # Résultats finaux
        st.markdown("---")
        st.subheader("📊 RAPPORT DE RECHERCHE")
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**👤 Personne recherchée:** {nom_personne}")
        with col2:
            if personne_trouvee:
                st.success(f"✅ RÉSULTAT: {nom_personne} a été trouvé(e) dans la vidéo !")
            else:
                st.error(f"❌ RÉSULTAT: {nom_personne} n'a PAS été trouvé(e) dans la vidéo")
                dire(f"{nom_personne} non trouvée dans la vidéo")
        
        try:
            os.unlink(chemin_image_recherche)
            os.unlink(chemin_video)
        except:
            pass

# ===========================
# 5. MODE CAMERA AVEC FACE_RECOGNITION ET COMPTAGE
# ===========================
@st.cache_resource
def load_yolo():
    return YOLO("yolov8n.pt")

def mode_camera_face_recognition():
    st.info("🔍 DÉMARRAGE DE LA RECONNAISSANCE FACIALE")
    
    with st.spinner("Chargement YOLO..."):
        model = load_yolo()
    
    known_encodings, known_names = charger_references_face_recognition()
    
    if not known_encodings:
        st.error("AUCUNE RÉFÉRENCE CHARGÉE! Ajoutez des photos dans le dossier 'personnes_reference'.")
        return
    
    SEUIL_RECONNAISSANCE = 0.5
    TAUX_REDUCTION = 0.5
    
    if 'personnes_deja_comptees' not in st.session_state:
        st.session_state.personnes_deja_comptees = set()
    if 'compteur_total' not in st.session_state:
        st.session_state.compteur_total = 0
    if 'derniere_frame_par_personne' not in st.session_state:
        st.session_state.derniere_frame_par_personne = {}
    if 'temps_debut' not in st.session_state:
        st.session_state.temps_debut = datetime.now()
        
    FRAME_TIMEOUT = 60
    frame_count = 0
    
    run_camera = st.checkbox("🎥 Démarrer la caméra", value=True)
    reset_button = st.button("🔄 Réinitialiser le compteur")
    
    if reset_button:
        st.session_state.personnes_deja_comptees.clear()
        st.session_state.derniere_frame_par_personne.clear()
        st.session_state.compteur_total = 0
        st.session_state.temps_debut = datetime.now()
        membre3_reset()
    
    frame_placeholder = st.empty()
    stats_placeholder = st.empty()
    
    if run_camera:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            st.error("Impossible d'ouvrir la caméra !")
            return
        
        while run_camera:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            
            # YOLO detection
            results = model.predict(frame, verbose=False, imgsz=320)
            personnes_yolo = 0
            
            for r in results:
                for box in r.boxes:
                    cls = int(box.cls[0])
                    if cls == 0 and float(box.conf[0]) > 0.5:
                        personnes_yolo += 1
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 128, 0), 1)
            
            # Face recognition
            small_frame = cv2.resize(frame, (0, 0), fx=TAUX_REDUCTION, fy=TAUX_REDUCTION)
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            
            face_locations = face_recognition.face_locations(rgb_small_frame)
            
            blacklist_alerte_frame = False

            if face_locations:
                face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
                
                for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                    matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=SEUIL_RECONNAISSANCE)
                    
                    name = "Inconnu"
                    couleur = (0, 165, 255)  # BGR Orange pour inconnu
                    security_status = ""  # "", "AUTORISÉ", ou "INTERDIT"
                    
                    if any(matches):
                        face_distances = face_recognition.face_distance(known_encodings, face_encoding)
                        best_match_index = np.argmin(face_distances)
                        if matches[best_match_index]:
                            name = known_names[best_match_index]
                            couleur = (0, 255, 0)  # BGR Green — reconnu
                            
                            if name not in st.session_state.personnes_deja_comptees:
                                st.session_state.personnes_deja_comptees.add(name)
                                st.session_state.compteur_total += 1
                                membre3_alerte_nouveau_comptage(st.session_state.compteur_total, nom=name)
                            
                            st.session_state.derniere_frame_par_personne[name] = frame_count
                    else:
                        face_hash = hash(tuple(np.round(face_encoding[:10], 3)))
                        inconnu_id = f"inconnu_{face_hash}"
                        
                        if inconnu_id not in st.session_state.personnes_deja_comptees:
                            st.session_state.personnes_deja_comptees.add(inconnu_id)
                            st.session_state.compteur_total += 1
                            membre3_alerte_nouveau_comptage(st.session_state.compteur_total)
                        
                        st.session_state.derniere_frame_par_personne[inconnu_id] = frame_count
                    
                    # ── Vérification Blacklist ──────────────────────────────
                    if st.session_state.blacklist_encodings:
                        m_bl = face_recognition.compare_faces(
                            st.session_state.blacklist_encodings, face_encoding, tolerance=0.50)
                        if any(m_bl):
                            d_bl = face_recognition.face_distance(
                                st.session_state.blacklist_encodings, face_encoding)
                            i_bl = int(np.argmin(d_bl))
                            if m_bl[i_bl]:
                                bl_name = st.session_state.blacklist_names[i_bl]
                                if name == "Inconnu":
                                    name = bl_name
                                security_status = "INTERDIT"
                                couleur = (0, 0, 220)  # rouge vif BGR
                                blacklist_alerte_frame = True
                                # Alerte vocale anti-spam 8 s
                                now_t = time.time()
                                key_v = f"cam_sec_{name}"
                                if now_t - st.session_state.securite_alertes_temps.get(key_v, 0) >= 8:
                                    st.session_state.securite_alertes_temps[key_v] = now_t
                                    dire(f"Alerte ! {name} est une personne interdite !")

                    # ── Remise à l'échelle originale ────────────────────────
                    top    = int(top    / TAUX_REDUCTION)
                    right  = int(right  / TAUX_REDUCTION)
                    bottom = int(bottom / TAUX_REDUCTION)
                    left   = int(left   / TAUX_REDUCTION)

                    # ── Dessin du rectangle + nom ───────────────────────────
                    thickness = 3 if security_status else 2
                    cv2.rectangle(frame, (left, top), (right, bottom), couleur, thickness)
                    cv2.putText(frame, name, (left, top - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, couleur, 2)

                    # ── Badge sécurité sous le rectangle ────────────────────
                    if security_status:
                        badge_txt = f"{'INTERDIT' if security_status == 'INTERDIT' else 'AUTORISE'}"
                        (bw, bh), _ = cv2.getTextSize(badge_txt, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
                        cv2.rectangle(frame,
                                      (left, bottom + 2),
                                      (left + bw + 10, bottom + bh + 14),
                                      couleur, -1)
                        cv2.putText(frame, badge_txt,
                                    (left + 5, bottom + bh + 8),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
            
            # ── Overlay blacklist alerte ──
            if blacklist_alerte_frame:
                overlay = frame.copy()
                cv2.rectangle(overlay, (0, 0), (frame.shape[1], 60), (0, 0, 180), -1)
                frame = cv2.addWeighted(overlay, 0.55, frame, 0.45, 0)
                cv2.putText(frame, "!! ALERTE SECURITE - PERSONNE INTERDITE !!",
                            (10, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (255, 255, 255), 2)

            # ── Alerte vocale limite depassee (basee sur personnes visibles actuellement) ──
            if personnes_yolo > LIMITE_PERSONNES:
                now_lim = time.time()
                if now_lim - st.session_state.derniere_alerte_limite_temps >= 10:
                    st.session_state.derniere_alerte_limite_temps = now_lim
                    dire(f"Attention ! {personnes_yolo} personnes detectees en ce moment, limite est {LIMITE_PERSONNES} !")


            # Mise a jour des statistiques
            temps_ecoule = (datetime.now() - st.session_state.temps_debut).seconds
            nb_bl = len(st.session_state.blacklist_names)

            with stats_placeholder.container():
                col1, col2, col3, col4, col5 = st.columns(5)
                col1.metric("Personnes uniques", st.session_state.compteur_total)
                col2.metric("Visages detectes", len(face_locations))
                col3.metric("YOLO personnes", personnes_yolo)
                col4.metric("Duree", f"{temps_ecoule}s")
                col5.metric("Blacklist", f"{nb_bl}")

            # Dessiner les stats sur l'image
            h, w = frame.shape[:2]
            top_box = 70 if blacklist_alerte_frame else 10
            cv2.rectangle(frame, (w - 310, top_box), (w - 10, top_box + 100), (0, 0, 0), -1)
            cv2.putText(frame, f"UNIQUES: {st.session_state.compteur_total}",
                        (w - 300, top_box + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.putText(frame, f"Refs: {len(known_names)}",
                        (w - 300, top_box + 55), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            if nb_bl:
                cv2.putText(frame, f"Blacklist: {nb_bl}",
                            (w - 300, top_box + 78), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 220), 1)
            
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_placeholder.image(frame_rgb, channels="RGB", use_container_width=True)
            
        cap.release()

# ===========================
# 6. MODE SECURITE — BLACKLIST
# ===========================
def ajouter_a_blacklist(uploaded_file, nom):
    """Sauvegarde la photo dans blacklist/ et encode le visage."""
    if uploaded_file is None or not nom:
        return False, "Veuillez fournir une image et un nom."
    os.makedirs(BLACKLIST_DOSSIER, exist_ok=True)
    chemin = os.path.join(BLACKLIST_DOSSIER, f"{nom}.jpg")
    with open(chemin, 'wb') as f:
        f.write(uploaded_file.getvalue())
    try:
        img = face_recognition.load_image_file(chemin)
        encs = face_recognition.face_encodings(img)
        if not encs:
            os.unlink(chemin)
            return False, "Aucun visage detecte dans cette image."
        if nom in st.session_state.blacklist_names:
            idx = st.session_state.blacklist_names.index(nom)
            st.session_state.blacklist_encodings[idx] = encs[0]
            return True, f"Encodage mis a jour pour '{nom}'."
        st.session_state.blacklist_encodings.append(encs[0])
        st.session_state.blacklist_names.append(nom)
        return True, f"'{nom}' ajoute a la blacklist."
    except Exception as e:
        try: os.unlink(chemin)
        except: pass
        return False, f"Erreur : {e}"


def supprimer_de_blacklist(nom):
    """Supprime une personne de la blacklist (session + fichier)."""
    if nom in st.session_state.blacklist_names:
        idx = st.session_state.blacklist_names.index(nom)
        st.session_state.blacklist_names.pop(idx)
        st.session_state.blacklist_encodings.pop(idx)
    chemin = os.path.join(BLACKLIST_DOSSIER, f"{nom}.jpg")
    if os.path.exists(chemin):
        os.unlink(chemin)


def mode_securite():
    """Mode Securite : gestion de la blacklist — sauvegarde sur disque."""

    st.markdown("""<div style='background:linear-gradient(135deg,#2d0a0a,#1a0505);
        border-radius:16px;padding:24px;margin-bottom:24px;
        border:2px solid #dc2626;'>
        <h3 style='color:#f87171;margin:0 0 6px 0;'>🚫 Gestion de la Blacklist</h3>
        <p style='color:#94A3B8;margin:0;font-size:.9rem;'>Ajoutez les personnes
        <b style='color:#f87171;'>non autorisees</b>.
        Les photos sont sauvegardees dans le dossier <code>blacklist/</code>.
        Toute autre personne est autorisee par defaut.</p>
        </div>""", unsafe_allow_html=True)

    col_form, col_list = st.columns([1, 1])

    with col_form:
        bl_img  = st.file_uploader("📸 Photo de la personne interdite",
                                   type=['jpg','jpeg','png'], key="bl_img")
        bl_name = st.text_input("🏷️ Nom", placeholder="Ex: Suspect_001", key="bl_name")
        if st.button("🚫 Ajouter a la Blacklist", key="btn_bl"):
            ok, msg = ajouter_a_blacklist(bl_img, bl_name)
            if ok:
                st.success(msg)
            else:
                st.error(msg)

    with col_list:
        st.markdown("**Personnes interdites :**")
        if st.session_state.blacklist_names:
            for n in list(st.session_state.blacklist_names):
                c1, c2 = st.columns([4, 1])
                c1.markdown(
                    f"<div style='background:#3b0d0d;border-left:4px solid #dc2626;"
                    f"padding:6px 12px;border-radius:6px;margin:4px 0;color:#f87171;'"
                    f">🚫 {n}</div>",
                    unsafe_allow_html=True
                )
                if c2.button("❌", key=f"del_{n}"):
                    supprimer_de_blacklist(n)
                    st.rerun()
        else:
            st.info("Aucune personne interdite enregistree.")

        if st.session_state.blacklist_names:
            if st.button("🗑️ Vider toute la Blacklist", key="clear_bl"):
                for n in list(st.session_state.blacklist_names):
                    supprimer_de_blacklist(n)
                st.rerun()


# ===========================
# CSS PERSONNALISÉ
# ===========================
def set_custom_css():
    st.markdown("""
        <style>
        /* Fond global */
        .stApp {
            background-color: #0F172A;
            color: #F8FAFC;
        }
        
        /* Titres */
        h1 {
            color: #38BDF8 !important;
            text-align: center;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
            padding-bottom: 10px;
        }
        h2 {
            color: #10B981 !important;
            border-bottom: 2px solid #1E293B;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }
        h3 {
            color: #94A3B8 !important;
        }
        
        /* Boutons */
        div.stButton > button {
            background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%);
            color: white;
            border-radius: 8px;
            border: none;
            padding: 12px 24px;
            font-weight: 600;
            transition: all 0.3s ease;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.5);
            width: 100%;
        }
        div.stButton > button:hover {
            background: linear-gradient(135deg, #60A5FA 0%, #3B82F6 100%);
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5);
        }
        
        /* Checkbox style button (Démarrer la caméra) */
        .stCheckbox > label > div[role="checkbox"] {
            border-radius: 4px;
            border-color: #38BDF8;
        }
        
        /* Sidebar styling */
        [data-testid="stSidebar"] {
            background-color: #1E293B;
            border-right: 1px solid #334155;
        }
        [data-testid="stSidebar"] .stRadio label {
            font-size: 1.1rem;
            padding: 5px 0;
            cursor: pointer;
        }
        
        /* File uploader styling */
        .stFileUploader > div > div {
            background-color: #1E293B;
            border-radius: 12px;
            border: 2px dashed #38BDF8;
            padding: 20px;
            transition: all 0.3s;
        }
        .stFileUploader > div > div:hover {
            border-color: #10B981;
            background-color: #334155;
        }
        
        /* Metrics / Statistiques cards */
        [data-testid="stMetricValue"] {
            color: #38BDF8;
            font-weight: 800;
        }
        [data-testid="stMetricLabel"] {
            color: #94A3B8;
            font-size: 1rem;
            font-weight: 600;
        }
        
        /* Alertes / Messages info */
        .stAlert {
            border-radius: 10px;
            border: none;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }
        
        /* Hide default Streamlit footer and menu */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {background-color: transparent;}
        </style>
    """, unsafe_allow_html=True)

# ===========================
# INTERFACE STREAMLIT PRINCIPALE
# ===========================
def main():
    st.set_page_config(
        page_title="Reconnaissance Faciale",
        page_icon="👁️",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    set_custom_css()
    
    st.markdown("<h1>👁️ Système de Reconnaissance Faciale Avancé</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #94A3B8; font-size: 1.2rem; margin-bottom: 30px;'>Projet de Vision par Ordinateur</p>", unsafe_allow_html=True)
    
    # Sidebar pour la navigation
    st.sidebar.title("📋 Menu Principal")
    choix = st.sidebar.radio(
        "Choisissez une option:",
        [
            "🏠 Accueil",
            "🎥 Mode Caméra",
            "🔍 Recherche avec Image",
            "🖼️ Analyser Image",
            "🎬 Recherche dans Vidéo",
            "🔐 Mode Sécurité",
        ]
    )
    
    if choix == "🏠 Accueil":
        st.header("Bienvenue sur la plateforme d'analyse faciale")
        
        st.markdown("""
        ### 🚀 Fonctionnalités disponibles:
        
        * **🎥 Mode Caméra** : Détection et comptage de personnes en temps réel.
        * **🔍 Recherche avec Image** : Traque d'une personne spécifique dans un flux vidéo en direct.
        * **🖼️ Analyser Image** : Analyse détaillée des visages sur une photo statique.
        * **🎬 Recherche dans Vidéo** : Traitement post-enregistrement pour retrouver une personne cible.
        * **🔐 Mode Sécurité** : Gestion de la blacklist — alerte vocale et visuelle en cas de détection.
        """)
        
        # Afficher les références existantes
        known_encodings, known_names = charger_references_face_recognition()
        if known_names:
            st.success(f"✅ {len(known_names)} personne(s) de référence chargée(s): {', '.join(known_names)}")
        else:
            st.warning("⚠️ Aucune référence chargée. Ajoutez des photos dans 'personnes_reference'")
    
    elif choix == "🎥 Mode Caméra":
        st.header("🎥 Mode Caméra - Reconnaissance en temps réel")
        st.warning("⚠️ Assurez-vous d'avoir des références dans 'personnes_reference'")
        mode_camera_face_recognition()
    
    elif choix == "🔍 Recherche avec Image":
        st.header("🔍 Rechercher une personne avec votre image")
        
        col1, col2 = st.columns(2)
        with col1:
            uploaded_file = st.file_uploader("📸 Image de la personne à rechercher", type=['jpg', 'jpeg', 'png'])
        with col2:
            nom_personne = st.text_input("🏷️ Nom de la personne", placeholder="Ex: Jean Dupont")
        
        if uploaded_file and nom_personne:
            rechercher_personne_camera_avec_image(uploaded_file, nom_personne)
    
    elif choix == "🖼️ Analyser Image":
        st.header("🖼️ Analyse d'image statique")
        
        uploaded_file = st.file_uploader("Sélectionnez une image à analyser", type=['jpg', 'jpeg', 'png'])
        
        if uploaded_file:
            if st.button("🔍 Analyser l'image", type="primary"):
                analyser_image(uploaded_file)
    
    elif choix == "🎬 Recherche dans Vidéo":
        st.header("🎬 Rechercher une personne dans une vidéo")
        
        col1, col2 = st.columns(2)
        with col1:
            image_file = st.file_uploader("📸 Image de référence", type=['jpg', 'jpeg', 'png'], key="img_ref")
            nom_personne = st.text_input("🏷️ Nom de la personne", key="nom_video", placeholder="Ex: Jean Dupont")
        with col2:
            video_file = st.file_uploader("🎬 Vidéo à analyser", type=['mp4', 'avi', 'mov', 'mkv'], key="video_file")
        
        if image_file and video_file and nom_personne:
            rechercher_personne_dans_video(image_file, video_file, nom_personne)

    elif choix == "🔐 Mode Sécurité":
        st.header("🔐 Mode Sécurité — Contrôle d'accès Whitelist / Blacklist")
        st.markdown(
            "<p style='color:#94A3B8;'>Gérez les personnes <b style='color:#4ade80;'>autorisées</b> "
            "et <b style='color:#f87171;'>interdites</b>, puis activez la surveillance caméra "
            "pour un contrôle d'accès en temps réel.</p>",
            unsafe_allow_html=True
        )
        mode_securite()

if __name__ == "__main__":
    main()