import os
import psycopg2
from psycopg2 import OperationalError
from dotenv import load_dotenv

#load the hidden variables from the .env file into the system
load_dotenv()

def create_connection():
    try:
        #Attempt connection
        connection = psycopg2.connect(
            database="she_radiance",
            user="postgres",
            password=os.getenv("DB_PASSWORD"),
            host="127.0.0.1",
            port="5432"
        )
        print("Connection to PostgreSQL database successful.")
        return connection
    
    except OperationalError as e:
        # Catch the error
        print(f"The error '{e}' occurred. Connection failed.")
        return None

def insert_ingredient(condition,compound, phase, logic):
    conn = create_connection()
    if conn is None:
        return # Stops execution if the pipeline is broken
    
    try:
        # Open the cursor(the messenger)
        cursor = conn.cursor()

        # Define the SQL command.
        sql_insert = """
            INSERT INTO INGREDIENT_DB (Target_Condition, Active_Compound, Treatment_Phase, Dermatological_logic)
            VALUES (%s, %s, %s, %s)
        """
        # Execute the command, passing the actual variables to fill the %s placeholders
        cursor.execute(sql_insert, (condition, compound, phase, logic))

        # Permanently save the transaction
        conn.commit()
        # This only prints if the commit succeeds
        print(f"Successfully added ingredient: {compound} for {condition}")

    except Exception as e:
        # This only runs if something above crashes
        print(f"Failed to insert data: {e}")

    finally:
        # Close the doors you open to prevent memory leaks
        if conn:
            cursor.close()
            conn.close()


if __name__ == "__main__":
    # Acne_Mild Routine
    insert_ingredient("Acne_Mild","Salicylic Acid", "Cleanse", "Lowers pH, dissolves sebum, unclogs pores.")
    insert_ingredient("Acne_Mild","Benzoyl Peroxide", "Cleanse", "Antibacterial, eliminates acne-causing microflora.")
    insert_ingredient("Acne_Mild","Retinol", "Serum", "Antioxidant, accelerates cell turnover.")
    insert_ingredient("Acne_Mild","Niacinamide", "Serum", "Protects skin barrier, reduces inflammation.")
    insert_ingredient("Acne_Mild","Aloe Vera", "Moisturize", "Alleviates irritation, repairs and soothes skin.")
    
    # Hyperpigmentation Routine
    insert_ingredient("Hyperpigmentation","Alpha Hydroxy Acids (AHAs)", "Cleanse", "Enhances exfoliation, stimulates cell renewal.")
    insert_ingredient("Hyperpigmentation","Kojic Acid", "Serum", "Inhibits melanin formation.")
    insert_ingredient("Hyperpigmentation","Alpha Arbutin", "Serum", "Provides direct depigmenting properties.")
    insert_ingredient("Hyperpigmentation","Vitamin C", "Moisturize", "Antioxidant, fades dark spots.")
    
    # Clear Skin Routine
    insert_ingredient("Clear_Skin","Alpha Hydroxy Acids (AHAs)", "Cleanse", "Maintains texture via gentle exfoliation.")
    insert_ingredient("Clear_Skin","Hyaluronic Acid", "Serum", "Binds water to the skin, increasing hydration.")
    insert_ingredient("Clear_Skin","Vitamin C", "Moisturize", "Provides daily antioxidant protection.")
    
    # All Conditions
    insert_ingredient("All","Zinc Oxide", "Protect", "Shields skin from UV radiation and oxidation.")

