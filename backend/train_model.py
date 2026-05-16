import os
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.layers import Dense, GlobalAveragePooling2D, Dropout
from tensorflow.keras.models import Model
from tensorflow.keras.callbacks import ModelCheckpoint, EarlyStopping
import tensorflow as tf


#Define the absolute path to your training data
#use os.path to dynamically find the folder regardless of whose computer this runs on
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'AI_TRAINING_DATA')

#Set Architectural Constants
IMG_WIDTH, IMG_HEIGHT = 224, 224 # MobileNetV2 requires 224*224 pixels
BATCH_SIZE = 16 #process 16 images at a time so computer doesnt crash
EPOCHS = 10 # The amount of times the ai will review the entire dataset

def create_data_generators():
    print("---Initializing Data Augmentation Pipeline---")

    #Augmentation engine(fixing Bias and small Data)
    #We split 20% of the images off to test the AI and use 80% to train it.
    datagen = ImageDataGenerator(
        rescale=1./255,  #Normalize pixel values from 0-255 down to 0-1
        rotation_range=20,  #Randomly rotate faces up to 20 degrees
        width_shift_range=0.2,  #Shifts faces left?right
        height_shift_range=0.2,  #Shifts faces up/down
        horizontal_flip=True,  #Flips faces like a mirror
        zoom_range=0.2, # Zoom in to focus on texture
        validation_split=0.2  #Reserves 20% of data for the final exam
    )

    #The Training Pipeline (80%)
    print("\nLoading Training Data...")
    train_generator = datagen.flow_from_directory(
        DATA_DIR,
        target_size=(IMG_WIDTH, IMG_HEIGHT),
        batch_size=BATCH_SIZE,
        class_mode='categorical',  #we have 4 distinct classes
        subset='training'
    )

    #The validation pipeline(20%)
    print("Loading Validation Data...")
    validation_generator = datagen.flow_from_directory(
        DATA_DIR,
        target_size=(IMG_WIDTH,IMG_HEIGHT),
        batch_size=BATCH_SIZE,
        class_mode='categorical',
        subset='validation'
    )

    return train_generator,validation_generator


def build_transfer_model(num_classes=4):
    print("\n---Constructing Neural Network Architecture---")
    
    #Load the Base Model(The "Eyes")
    #We strip off the original layer(include_top=False) because it was trained to recognize random objects we only care about skin.
    base_model = MobileNetV2(weights='imagenet', include_top=False, input_shape=
    (224, 224, 3))
    
    #Freeze the base model
    #mathematically locks Google's pre_trained weights so our tiny dataset doesn't overwrite them
    base_model.trainable = False
    
    #Add the Custom Classification Head (the "Brain")
    x = base_model.output
    x = GlobalAveragePooling2D()(x) 
    
    #Flattens the 2D pixel grids into a 1D array
    #Dropout acts as a "forgetting" mechanism, By randomly dropping 20% of the data, it forces the AI to learn the actual patterns of acne, not just memorize my specific photos
    x = Dropout(0.2)(x)
    
    # Final Decision Layer
    #Softmax forces the AI to output percentages that add up to 100% (e.g., 90% Acne_Mild, 10% Clear_Skin)
    predictions = Dense(num_classes, activation='softmax')(x)
    
    #Assemble the Model
    model = Model(inputs=base_model.input, outputs=predictions)
    
    #Compile the math as Adam is the optimizer (the algorithm that updates the weights).
    #learning rate 0.0001 is intentionally slow so it learns carefully.
    model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=0.0001),
                loss='categorical_crossentropy',
                metrics=['accuracy'])
    
    print("Model compilation complete.")
    return model




if __name__ == "__main__":
    #1. Prepare Data by printing the mathematical mapping of the folders so we know the AI sees them
    train_gen, val_gen = create_data_generators()
    print("\nClass Mapping Dictionary:", train_gen.class_indices)
    
    #2. Build Model and print the blueprint of the neural network
    ai_model = build_transfer_model(num_classes=4)
    ai_model.summary()
    
    #3. Define Safety Callbacks
    checkpoint = ModelCheckpoint("best_skin_model.keras", monitor='val_accuracy', save_best_only=True, mode='max')
    early_stop = EarlyStopping(monitor='val_accuracy', patience=3, restore_best_weights=True)
    
    #4. IGNITION: Train the Model
    print("\n---Intiating Model Training---")
    history = ai_model.fit(
        train_gen,
        validation_data=val_gen,
        epochs=EPOCHS,
        callbacks=[checkpoint,early_stop]
    )
    
    #5. Save the Final Output
    ai_model.save("final_skin_model.keras")
    print("\nTraining Complete. Neural Network saved to disk as 'final_skin_model.keras'.")







