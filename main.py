from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import re  # <--- NEW IMPORT

app = Flask(__name__)

# ------------------- #
# VEHICLE INFO FETCHER#
# ------------------- #
def get_vehicle_details(rc_number: str) -> dict:
    rc = rc_number.strip().upper()
    url = f"https://vahanx.in/rc-search/{rc}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36",
        "Referer": "https://vahanx.in/rc-search",
        "Accept-Language": "en-US,en;q=0.9"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        # If the site blocks us, this will catch it
        if response.status_code != 200:
            return {"error": f"Website returned status: {response.status_code}"}
        
        soup = BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        return {"error": str(e)}

    # --- IMPROVED SEARCH FUNCTION --- #
    def get_value(label_pattern):
        # Searches for text matching the pattern (ignoring case & spaces)
        try:
            # We use re.compile to match "Owner Name", "Owner Name:", "Owner Name " etc.
            tag = soup.find("span", string=re.compile(label_pattern, re.IGNORECASE))
            if tag:
                parent = tag.find_parent("div")
                if parent:
                    # Try finding the <p> tag which usually holds the value
                    value_tag = parent.find("p")
                    if value_tag:
                        return value_tag.get_text(strip=True)
            return None
        except AttributeError:
            return None

    # We check if we actually found a vehicle table. 
    # If "Owner Name" is missing, the car data likely didn't load.
    owner_name = get_value(r"Owner\s*Name") 

    data = {
        "Owner Name": owner_name,
        "Father's Name": get_value(r"Father'?s?\s*Name"), # Handles "Father Name" or "Father's Name"
        "Owner Serial No": get_value(r"Owner\s*Serial"),
        "Model Name": get_value(r"Model\s*Name"),
        "Maker Model": get_value(r"Maker\s*Model"),
        "Vehicle Class": get_value(r"Vehicle\s*Class"),
        "Fuel Type": get_value(r"Fuel\s*Type"),
        "Registration Date": get_value(r"Registration\s*Date"),
        "Insurance Expiry": get_value(r"Insurance\s*Expiry"),
        "Registered RTO": get_value(r"Registered\s*RTO"),
        "City Name": get_value(r"City\s*Name"),
        # We explicitly look for RTO Address to avoid confusion
        "RTO Address": get_value(r"Address"), 
    }
    
    return data

@app.route("/", methods=["GET"])
def api():
    rc_number = request.args.get("rc_number")

    if not rc_number:
        return jsonify({
            "credit": "API DEVELOPER: @mowa",
            "status": "online",
            "message": "Welcome! Usage: /?rc_number=YOUR_RC_HERE"
        }), 200

    details = get_vehicle_details(rc_number)

    if details.get("error"):
        return jsonify({
            "credit": "API DEVELOPER: @mowa",
            "status": "error",
            "message": details["error"]
        }), 500

    # If Owner Name is STILL null, it means the website didn't have data for this car
    if not details.get("Owner Name"):
         return jsonify({
            "credit": "API DEVELOPER: @mowa",
            "status": "not_found",
            "message": "Vehicle details not found on server. (RTO Address may be visible)",
            "partial_data": details
        }), 404

    return jsonify({
        "credit": "API DEVELOPER : @mowa",
        "status": "success",
        "rc_number": rc_number.upper(),
        "details": details
    })
