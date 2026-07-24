import os
import numpy as np
from tensorflow.keras.preprocessing import image
from tensorflow.keras.models import load_model

#Import your working database router
#from logic_router import route_treatment

#Locate the brain
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, 'backend', 'final_skin_model.keras')

print("Loading AI Model into Memory...")
model = load_model(MODEL_PATH)

#Translation Dictionary: The ai only outputs numbers(0,1,2,3). We must translate those back to your folder names.
CLASS_MAPPING = {0: 'Acne_Mild', 1: 'Acne_Severe', 2: 'Clear_Skin', 3: 'Hyperpigmentation'}

def analyze_user_selfie(image_path):
    """
    Takes a raw photo and runs it through the AI.
    Returns the confidence score and the diagnosis string.
    """
    print(f"\n---Processing Image: {os.path.basename(image_path)}---")
    
    # Format the image mathematically
    img = image.load_img(image_path, target_size=(224, 224)) # Ensure this is 224
    img_array = image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0)
    img_array /= 255.0 
    
    # Make the Prediction
    predictions = model.predict(img_array, verbose=0)
    predicted_index = np.argmax(predictions[0])
    confidence = np.max(predictions[0]) * 100
    
    ai_diagnosis = CLASS_MAPPING[predicted_index]
    print(f"AI Diagnosis: {ai_diagnosis} ({confidence:.2f}% confidence)")
    
    # Return the raw numbers to the Streamlit frontend
    return float(confidence), ai_diagnosis