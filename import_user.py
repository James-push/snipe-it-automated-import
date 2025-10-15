import csv
import requests
import secrets
import string
from dotenv import load_dotenv
import os

load_dotenv()

API_URL = os.getenv("API_URL")
API_TOKEN = os.getenv("API_TOKEN")
CSV_FILE = "user_template.csv"  # Must have: first_name, last_name, username, email
OUTPUT_FILE = "generated_passwords.csv"

HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Accept": "application/json",
    "Content-Type": "application/json"
}

# --- FUNCTION TO GENERATE SECURE PASSWORD ---
def generate_password(length=12):
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(characters) for _ in range(length))

# --- FUNCTION TO FETCH USER DETAILS BY EMAIL ---
def get_user_by_email(email):
    try:
        response = requests.get(f"{API_URL}/users?email={email}", headers=HEADERS)
        if response.status_code == 200:
            data = response.json()

            # Your API returns "rows", not "data"
            if isinstance(data, dict) and "rows" in data:
                users = data["rows"]
                if isinstance(users, list) and len(users) > 0:
                    # Just to be extra safe, match by email in case API returns partial matches
                    for user in users:
                        if user.get("email", "").strip().lower() == email.strip().lower():
                            return user  # Found the existing user
        else:
            print(f"⚠️ Failed to fetch user {email}: {response.status_code}")
        return None
    except Exception as e:
        print(f"⚠️ Error fetching user {email}: {e}")
        return None

# --- FUNCTION TO UPDATE EXISTING USER ---
def update_user(user_id, first_name, last_name, username, email):
    try:
        payload = {
            "first_name": first_name,
            "last_name": last_name,
            "username": username,
            "email": email
        }

        response = requests.patch(f"{API_URL}/users/{user_id}", headers=HEADERS, json=payload)
        if response.status_code in [200, 201, 202, 204]:
            print(f"✅ Updated user ID {user_id} ({email})")
            return True
        else:
            print(f"❌ Failed to update user ID {user_id}: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"⚠️ Error updating user {user_id}: {e}")
        return False

# --- FUNCTION TO CHECK IF USER NEEDS UPDATE ---
def user_needs_update(existing_user, first_name, last_name, username, email):
    # Normalize for comparison (strip spaces and lowercase emails/usernames)
    return (
        existing_user.get("first_name", "").strip() != first_name.strip() or
        existing_user.get("last_name", "").strip() != last_name.strip() or
        existing_user.get("username", "").strip().lower() != username.strip().lower() or
        existing_user.get("email", "").strip().lower() != email.strip().lower()
    )

# --- FUNCTION TO CREATE NEW USER ---
def create_user(first_name, last_name, username, email, password):
    try:
        payload = {
            "first_name": first_name,
            "last_name": last_name,
            "username": username,
            "email": email,
            "password": password,
            "password_confirmation": password,
            "activated": True
        }

        response = requests.post(f"{API_URL}/users", headers=HEADERS, json=payload)
        result = response.json() if "application/json" in response.headers.get("Content-Type", "") else {}

        if response.status_code in [200, 201]:
            user_id = None
            if "data" in result and isinstance(result["data"], dict):
                user_id = result["data"].get("id")
            elif "id" in result:
                user_id = result["id"]

            print(f"🆕 Created new user: {email} (ID: {user_id})")
            return True, user_id, password
        else:
            print(f"❌ Failed to create {email}: {response.status_code} - {response.text}")
            return False, None, None
    except Exception as e:
        print(f"⚠️ Error creating user {email}: {e}")
        return False, None, None

# --- MAIN IMPORT LOOP ---
with open(CSV_FILE, newline='') as csvfile, open(OUTPUT_FILE, "w", newline='') as outfile:
    reader = csv.DictReader(csvfile)
    writer = csv.writer(outfile)
    writer.writerow(["user_id", "email", "username", "generated_password", "status"])

    for row in reader:
        email = row["email"].strip()
        username = row["username"].strip()
        first_name = row["first_name"].strip()
        last_name = row["last_name"].strip()

        existing_user = get_user_by_email(email)

        if existing_user:
            user_id = existing_user.get("id", "N/A")

            if user_needs_update(existing_user, first_name, last_name, username, email):
                if update_user(user_id, first_name, last_name, username, email):
                    writer.writerow([user_id, email, username, "", "updated"])
                else:
                    writer.writerow([user_id, email, username, "", "update failed"])
            else:
                print(f"⏩ Skipped (no change): {email}")
                writer.writerow([user_id, email, username, "", "no change"])
        else:
            password = generate_password()
            success, user_id, pwd = create_user(first_name, last_name, username, email, password)
            if success:
                writer.writerow([user_id, email, username, password, "created"])
            else:
                writer.writerow(["", email, username, password, "create failed"])
