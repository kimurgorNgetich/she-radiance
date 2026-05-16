import os
import numpy as np
from tensorflow.keras.preprocessing import image
from tensorflow.keras.models import load_model

#Import your working database router
from logic_router import route_treatment

#Locate the brain
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, 'backend', 'final_skin_model.keras')

print("Loading AI Model into Memory...")
model = load_model(MODEL_PATH)

#Translation Dictionary: The ai only outputs numbers(0,1,2,3). We must translate those back to your folder names.
CLASS_MAPPING = {0: 'Acne_Mild', 1: 'Acne_Severe', 2: 'Clear_Skin', 3: 'Hyperpigmentation'}

def analyze_user_selfie(image_path):
    """
    Takes a raw photo, runs it through the AI, and pulls the database routine.
    """
    print(f"\n---Processing Image: {os.path.basename(image_path)}---")
    
    #Format the image mathematically
    img = image.load_img(image_path, target_size=(224, 224))
    img_array = image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0)
    img_array /= 255.0 #Normalize to 0-1 range exactly like in the train_model
    
    #Make the Prediction
    predictions = model.predict(img_array, verbose=0)
    predicted_index = np.argmax(predictions[0])# Get the highest percentage
    confidence = np.max(predictions[0]) * 100
    
    ai_diagnosis = CLASS_MAPPING[predicted_index]
    print(f"AI Diagnosis: {ai_diagnosis} ({confidence:.2f}% confidence)")
    
    #The Integration; Pass the AI diagnosis into your databse logic router
    final_prescription = route_treatment(ai_diagnosis)
    
    return final_prescription

if __name__ == "__main__":
    #test simulation(grabs  a random image from my training data to prove loop works)
    test_image_path = os.path.join(BASE_DIR, 'AI_TRAINING_DATA', 'Acne_Mild', 'levle0_62.jpg')
    
    if os.path.exists(test_image_path):
        result = analyze_user_selfie(test_image_path)
        
        print("\n---FINAL SYSTEM OUTPUT---")
        if result['status'] == 'success':
            for step in result['routine']:
                print(f"{step['treatment_phase']}: {step['active_compound']} - {step['dermatological_logic']}")
        else:
            print(result['message'])
    else:
        print(f"Test image not found at: {test_image_path}")