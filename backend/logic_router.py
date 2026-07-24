import psycopg2
import psycopg2.extras # Needed to return data as a dictionary
from database import create_connection

def get_routine_from_db(ai_diagnosis):
    """
    Step 1: Queries the PostgreSQL database for treatments matching the diagnosis.
    """
    conn = create_connection() #  imported from database.py
    if conn is None:
        return []

    try:
        # DictCursor ensures the data comes back as a Python dictionary,
        # which our safety filter function requires.
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Pull ingredients for the specific diagnosis, AND the sunscreen ("All")
        sql_query = """
            SELECT DISTINCT Active_Compound, Treatment_Phase, Dermatological_Logic
            FROM INGREDIENT_DB
            WHERE Target_Condition = %s OR Target_Condition = 'All';
        """
        
        cursor.execute(sql_query, (ai_diagnosis,))
        raw_routine = cursor.fetchall()
        
        # Convert the database rows into a standard Python list of dictionaries
        routine_list = [dict(row) for row in raw_routine]
        return routine_list

    except Exception as e:
        print(f"Database Query Error: {e}")
        return []
    finally:
        if conn:
            cursor.close()
            conn.close()


def enforce_safety_rules(raw_routine_list):
    """
    Step 2: The Conflict Filter.
    Takes the raw list of ingredients from the DB and removes dangerous combinations.
    """
    # Extract just the ingredient names to make checking easier
    ingredients = [item['active_compound'] for item in raw_routine_list]
    
    safe_routine = raw_routine_list.copy()

    # Rule 1 & 2: Oxidation Cancellation (Benzoyl Peroxide destroys Retinol & Vitamin C)
    if "Benzoyl Peroxide" in ingredients:
        safe_routine = [item for item in safe_routine if item['active_compound'] not in ["Retinol", "Vitamin C"]]
        
    # Rule 3: Exfoliation Overload (Retinol + AHAs/Salicylic Acid)
    if "Retinol" in ingredients:
        safe_routine = [item for item in safe_routine if item['active_compound'] not in ["Alpha Hydroxy Acids (AHAs)", "Salicylic Acid"]]

    #Rule 4: The pH Clash
    # Vitamin C requires a specific pH and clashes with AHAs.
    if "Vitamin C" in ingredients:
        safe_routine = [item for item in safe_routine if item['active_compound'] not in ["Alpha Hydroxy Acids (AHAs)"]]

    return safe_routine


def sort_chronologically(safe_routine):
    """
    Step 3: Orders the ingredients into the correct dermatological sequence.
    """
    phase_order = {"Cleanse": 1, "Serum": 2, "Moisturize": 3, "Protect": 4}
    
    # Sorts the dictionary based on the phase_order mapping
    sorted_routine = sorted(safe_routine, key=lambda x: phase_order.get(x['treatment_phase'], 5))
    return sorted_routine


def route_treatment(ai_diagnosis):
    """
    The Main Controller. This is the only function your Streamlit UI will call.
    """
    print(f"--- Routing Logic Initiated for: {ai_diagnosis} ---")

    # THE TRIAGE GATE (Medical Redirect)
    if ai_diagnosis == 'Acne_Severe':
        return {
            "status": "medical_redirect",
            "message": "Based on the AI analysis, you are experiencing Severe/Cystic Acne. Over-the-counter serums cannot penetrate deep enough to treat this condition safely. Please consult a board-certified dermatologist for prescription treatments."
        }

    # Standard Operations
    elif ai_diagnosis in ['Acne_Mild', 'Hyperpigmentation', 'Clear_Skin']:
        
        # 1. Pull raw data from database
        raw_data = get_routine_from_db(ai_diagnosis)
        
        # 2. Filter out chemical burns
        safe_data = enforce_safety_rules(raw_data)
        
        # 3. Sort for the user
        final_routine = sort_chronologically(safe_data)
        
        return {
            "status": "success",
            "routine": final_routine
        }
        
    else:
        return {"status": "error", "message": "Unknown diagnosis received."}
    
def route_from_vision(vision_result: dict) -> dict:
    """
    SR-002: Routing entry point for vision-API-based diagnoses (backend/vision_client.py).
    Applies referral policy to a vision_client.analyze_selfie() result, then delegates to
    the existing route_treatment() DB/safety/sort pipeline for known conditions.
    """
    status = vision_result.get("status")
    condition = vision_result.get("condition")
    referral_flag = vision_result.get("referral_flag")

    # a. Engine-level failure (api_error, auth_error, parse_error, refusal, ...)
    if status != "ok":
        return {"status": "inconclusive", "reason": "engine_error"}

    # b. Model itself was not confident enough to pick a condition
    if condition == "Uncertain_Refer":
        return {"status": "inconclusive", "reason": "low_certainty"}

    # c. Severe acne or an explicit referral flag -> existing medical redirect payload
    if condition == "Acne_Severe" or referral_flag is True:
        return route_treatment("Acne_Severe")

    # d. Known, routable conditions -> existing DB query + enforce_safety_rules + sort_chronologically
    if condition in ("Acne_Mild", "Hyperpigmentation", "Clear_Skin"):
        return route_treatment(condition)

    # e. Anything else (unrecognized label)
    return {"status": "inconclusive", "reason": "unknown_label"}


if __name__ == "__main__":
    # Simulating the AI detecting Mild Acne
    print("\n--- TEST 1: Acne_Mild ---")
    acne_result = route_treatment("Acne_Mild")
    if acne_result['status'] == 'success':
        for step in acne_result.get('routine', []):
            print(f"{step['treatment_phase']}: {step['active_compound']} - {step['dermatological_logic']}")

    # Simulating the AI detecting Severe Acne
    print("\n--- TEST 2: Acne_Severe ---")
    severe_result = route_treatment("Acne_Severe")
    print(severe_result['message'])