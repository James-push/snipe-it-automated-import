import csv
import requests
import logging
from datetime import datetime
import sys
from dotenv import load_dotenv
import os

load_dotenv()  

# --- CONFIGURATION ---
API_URL = os.getenv("API_URL")
API_TOKEN = os.getenv("API_TOKEN")
HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Accept": "application/json",
    "Content-Type": "application/json"
}
CSV_FILE = "asset_template.csv"
OUTPUT_FILE = f"asset_import_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
LOG_FILE = f"asset_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# --- LOGGING SETUP ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# --- FUNCTION TO FETCH USER BY EMAIL ---
def get_user_by_email(email):
    try:
        response = requests.get(f"{API_URL}/users?email={email}", headers=HEADERS)
        logger.debug(f"User fetch response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            logger.debug(f"User response for {email}: {data}")
            
            if isinstance(data, dict) and "rows" in data:
                users = data["rows"]
                if isinstance(users, list) and len(users) > 0:
                    logger.info(f"User found: {email}")
                    return users[0]
                else:
                    logger.warning(f"No rows returned for email: {email}")
            else:
                logger.warning(f"'rows' key not found. Keys available: {list(data.keys())}")
        else:
            logger.error(f"API error: {response.status_code} - {response.text}")
        
        return None
    except Exception as e:
        logger.error(f"Error fetching user {email}: {e}")
        return None

# --- FUNCTION TO FETCH CATEGORY BY NAME ---
def get_category_by_name(name):
    try:
        response = requests.get(f"{API_URL}/categories?search={name}", headers=HEADERS)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and "rows" in data:
                categories = data["rows"]
                if isinstance(categories, list) and len(categories) > 0:
                    return categories[0]
        return None
    except Exception as e:
        logger.error(f"Error fetching category {name}: {e}")
        return None

# --- FUNCTION TO FETCH MODEL BY NAME ---
def get_model_by_name(name):
    try:
        response = requests.get(f"{API_URL}/models?search={name}", headers=HEADERS)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and "rows" in data:
                models = data["rows"]
                if isinstance(models, list) and len(models) > 0:
                    return models[0]
        return None
    except Exception as e:
        logger.error(f"Error fetching model {name}: {e}")
        return None

# --- FUNCTION TO FETCH STATUS BY NAME ---
def get_status_by_name(name):
    try:
        response = requests.get(f"{API_URL}/statuslabels?search={name}", headers=HEADERS)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and "rows" in data:
                statuses = data["rows"]
                if isinstance(statuses, list) and len(statuses) > 0:
                    return statuses[0]
        return None
    except Exception as e:
        logger.error(f"Error fetching status {name}: {e}")
        return None

# --- FUNCTION TO FETCH LOCATION BY NAME ---
def get_location_by_name(name):
    try:
        response = requests.get(f"{API_URL}/locations?search={name}", headers=HEADERS)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and "rows" in data:
                locations = data["rows"]
                if isinstance(locations, list) and len(locations) > 0:
                    return locations[0]
        return None
    except Exception as e:
        logger.error(f"Error fetching location {name}: {e}")
        return None

# --- FUNCTION TO GET ASSET BY TAG ---
def get_asset_by_tag(asset_tag):
    try:
        response = requests.get(f"{API_URL}/hardware?search={asset_tag}", headers=HEADERS)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and "rows" in data:
                assets = data["rows"]
                if isinstance(assets, list) and len(assets) > 0:
                    for asset in assets:
                        if asset.get("asset_tag") == asset_tag:
                            return asset
        return None
    except Exception as e:
        logger.error(f"Error fetching asset {asset_tag}: {e}")
        return None

# --- FUNCTION TO CREATE ASSET ---
def create_asset(name, asset_tag, model_id, status_id, assigned_user_id, location_id, serial):
    try:
        payload = {
            "asset_tag": asset_tag,
            "model_id": model_id,
            "status_id": status_id,
            "name": name,
            "assigned_user": assigned_user_id,
            "location_id": location_id,
            "serial": serial
        }
        response = requests.post(f"{API_URL}/hardware", headers=HEADERS, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            # Handle different response structures
            if isinstance(result, dict):
                if "payload" in result:
                    return result["payload"]
                elif "rows" in result and len(result["rows"]) > 0:
                    return result["rows"][0]
        return None
    except Exception as e:
        logger.error(f"Error creating asset {asset_tag}: {e}")
        return None

# --- FUNCTION TO ASSIGN ASSET TO USER ---
def assign_asset_to_user(asset_id, user_id, location_id, serial):
    try:
        payload = {
            "assigned_user": user_id,
            "location_id": location_id,
            "serial": serial
        }
        response = requests.patch(f"{API_URL}/hardware/{asset_id}", headers=HEADERS, json=payload)
        
        if response.status_code == 200:
            return True
        else:
            logger.error(f"Error assigning asset {asset_id}: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Error assigning asset {asset_id}: {e}")
        return False

# --- MAIN IMPORT LOOP ---
logger.info("=" * 80)
logger.info("SNIPE-IT ASSET IMPORT STARTED")
logger.info("=" * 80)

stats = {"total": 0, "created": 0, "updated": 0, "failed": 0}

try:
    with open(CSV_FILE, newline='', encoding='utf-8') as csvfile, \
         open(OUTPUT_FILE, "w", newline='', encoding='utf-8') as outfile:
        
        reader = csv.DictReader(csvfile)
        writer = csv.writer(outfile)
        writer.writerow([
            "asset_tag", "name", "assigned_to", "model_name", 
            "category_name", "status_label", "location_name", "serial", "asset_id", "user_id", "status"
        ])
        
        for row in reader:
            stats["total"] += 1
            
            asset_tag = row.get("asset_tag", "").strip()
            name = row.get("name", "").strip()
            assigned_to_email = row.get("assigned_to", "").strip()
            category_name = row.get("category_name", "").strip()
            model_name = row.get("model_name", "").strip()
            status_label = row.get("status_label", "").strip()
            location_name = row.get("location_name", "").strip()
            serial = row.get("serial", "").strip()
            
            # Validate required fields
            if not all([asset_tag, name, assigned_to_email, category_name, model_name, status_label, location_name, serial]):
                logger.warning(f"Missing required fields in row")
                writer.writerow([asset_tag, name, assigned_to_email, model_name, 
                               category_name, status_label, location_name, serial, "", "", "failed - missing fields"])
                stats["failed"] += 1
                continue
            
            # Get user
            user = get_user_by_email(assigned_to_email)
            if not user:
                logger.warning(f"User not found: {assigned_to_email}")
                writer.writerow([asset_tag, name, assigned_to_email, model_name, 
                               category_name, status_label, location_name, serial, "", "", "failed - user not found"])
                stats["failed"] += 1
                continue
            
            user_id = user.get("id")
            
            # Get category
            category = get_category_by_name(category_name)
            if not category:
                logger.warning(f"Category not found: {category_name}")
                writer.writerow([asset_tag, name, assigned_to_email, model_name, 
                               category_name, status_label, location_name, serial, "", user_id, "failed - category not found"])
                stats["failed"] += 1
                continue
            
            category_id = category.get("id")
            
            # Get model
            model = get_model_by_name(model_name)
            if not model:
                logger.warning(f"Model not found: {model_name}")
                writer.writerow([asset_tag, name, assigned_to_email, model_name, 
                               category_name, status_label, location_name, serial, "", user_id, "failed - model not found"])
                stats["failed"] += 1
                continue
            
            model_id = model.get("id")
            
            # Get status
            status = get_status_by_name(status_label)
            if not status:
                logger.warning(f"Status not found: {status_label}")
                writer.writerow([asset_tag, name, assigned_to_email, model_name, 
                               category_name, status_label, location_name, serial, "", user_id, "failed - status not found"])
                stats["failed"] += 1
                continue
            
            status_id = status.get("id")
            
            # Get location
            location = get_location_by_name(location_name)
            if not location:
                logger.warning(f"Location not found: {location_name}")
                writer.writerow([asset_tag, name, assigned_to_email, model_name, 
                               category_name, status_label, location_name, serial, "", user_id, "failed - location not found"])
                stats["failed"] += 1
                continue
            
            location_id = location.get("id")
            
            # Check if asset exists
            existing_asset = get_asset_by_tag(asset_tag)
            if existing_asset:
                asset_id = existing_asset.get("id")
                if assign_asset_to_user(asset_id, user_id, location_id, serial):
                    logger.info(f"Updated existing asset: {asset_tag} → {assigned_to_email}")
                    writer.writerow([asset_tag, name, assigned_to_email, model_name, 
                                   category_name, status_label, location_name, serial, asset_id, user_id, "updated"])
                    stats["updated"] += 1
                else:
                    logger.error(f"Failed to assign asset: {asset_tag}")
                    writer.writerow([asset_tag, name, assigned_to_email, model_name, 
                                   category_name, status_label, location_name, serial, asset_id, user_id, "failed"])
                    stats["failed"] += 1
                continue
            
            # Create new asset
            new_asset = create_asset(name, asset_tag, model_id, status_id, user_id, location_id, serial)
            if new_asset:
                asset_id = new_asset.get("id")
                logger.info(f"Created asset: {asset_tag} → {assigned_to_email} (ID: {asset_id})")
                writer.writerow([asset_tag, name, assigned_to_email, model_name, 
                               category_name, status_label, location_name, serial, asset_id, user_id, "success"])
                stats["created"] += 1
            else:
                logger.error(f"Failed to create asset: {asset_tag}")
                writer.writerow([asset_tag, name, assigned_to_email, model_name, 
                               category_name, status_label, location_name, serial, "", user_id, "failed"])
                stats["failed"] += 1
    
    logger.info("=" * 80)
    logger.info("IMPORT SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total Processed: {stats['total']}")
    logger.info(f"Created:         {stats['created']}")
    logger.info(f"Updated:         {stats['updated']}")
    logger.info(f"Failed:          {stats['failed']}")
    logger.info(f"Results saved to: {OUTPUT_FILE}")
    logger.info(f"Log saved to:     {LOG_FILE}")
    logger.info("=" * 80)

except FileNotFoundError:
    logger.error(f"CSV file not found: {CSV_FILE}")
except Exception as e:
    logger.error(f"Fatal error: {e}")