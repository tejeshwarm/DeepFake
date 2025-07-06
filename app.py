import os
import tempfile
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import cv2
import numpy as np
from keras.models import load_model
import warnings
import tensorflow as tf
import logging

# Disable unnecessary logs
warnings.filterwarnings("ignore")
tf.get_logger().setLevel('ERROR')
logging.getLogger('tensorflow').setLevel(logging.ERROR)
logging.getLogger('absl').setLevel(logging.ERROR)

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# Load models
vgg_model = load_model("vgg_model.h5")
vgg_model.compile(loss='binary_crossentropy', optimizer='adam', metrics=['accuracy'])

resnet_model = load_model("resnet_model.h5")
resnet_model.compile(loss='binary_crossentropy', optimizer='adam', metrics=['accuracy'])

def extract_frames(video_path, num_frames=10):
    frames = []
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames == 0:
        cap.release()
        return []

    interval = max(1, total_frames // num_frames)
    frame_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_count % interval == 0:
            frame = cv2.resize(frame, (224, 224))
            frame = frame / 255.0
            frame = np.expand_dims(frame, axis=0)
            frames.append(frame)
        frame_count += 1

    cap.release()
    return np.concatenate(frames, axis=0) if frames else []

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/predict', methods=['POST'])
def predict():
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400

    video_file = request.files['video']

    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
        video_path = tmp.name
        video_file.save(video_path)

    try:
        input_frames = extract_frames(video_path)
        if len(input_frames) == 0:
            return jsonify({'error': 'Video processing failed'}), 400

        vgg_pred = vgg_model.predict(input_frames, verbose=0)
        resnet_pred = resnet_model.predict(input_frames, verbose=0)

        votes = [np.argmax(vgg_pred), np.argmax(resnet_pred)]
        final_result = np.argmax(np.bincount(votes))

        return jsonify({'prediction': 'real' if final_result == 0 else 'fake'})

    finally:
        os.remove(video_path)

if __name__ == '__main__':
    app.run(debug=True)
