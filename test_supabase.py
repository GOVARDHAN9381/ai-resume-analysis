import os
from supabase import create_client, Client
from datetime import datetime

# Supabase Initialization
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://ulmdpmajlzaeszjafsfx.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVsbWRwbWFqbHphZXN6amFmc2Z4Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjI3NzYzNCwiZXhwIjoyMDk3ODUzNjM0fQ.MIU_E9DlonAFcJmu2CThc00eL5eZb06HOSS-nKbtK-I")

print("Initializing Supabase client...")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def test_connection():
    print("Testing connection by reading from 'candidates' table...")
    try:
        response = supabase.table("candidates").select("*").limit(1).execute()
        print("SUCCESS: Successfully connected and read from 'candidates'.")
        print(f"Current rows found: {len(response.data)}")
    except Exception as e:
        print(f"ERROR: Failed to read from Supabase: {e}")
        return False
        
    print("\nTesting insert into 'fraud_reports' table...")
    try:
        dummy_data = {
            "id": "TEST-12345",
            "risk_score": 0,
            "risk_level": "LOW RISK",
            "flags_count": 0,
            "flags": [],
            "created_at": datetime.now().isoformat()
        }
        # Insert
        insert_res = supabase.table("fraud_reports").insert(dummy_data).execute()
        print("SUCCESS: Successfully inserted test record into 'fraud_reports'.")
        
        # Read back
        read_res = supabase.table("fraud_reports").select("*").eq("id", "TEST-12345").execute()
        print(f"SUCCESS: Successfully read back the test record: {read_res.data[0]['id']}")
        
        # Cleanup
        print("Cleaning up test record...")
        supabase.table("fraud_reports").delete().eq("id", "TEST-12345").execute()
        print("SUCCESS: Cleanup complete.")
        
        print("\nAll Supabase tests passed!")
        return True
    except Exception as e:
        print(f"ERROR: Failed to write/read from Supabase: {e}")
        return False

if __name__ == "__main__":
    test_connection()
