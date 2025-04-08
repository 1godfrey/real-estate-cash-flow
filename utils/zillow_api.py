import os
import time
import json
import logging
import requests
from typing import List, Dict, Any, Optional

def get_zillow_listings(zip_code: str) -> List[Dict[str, Any]]:
    """
    Fetches property listings from Zillow API for a given ZIP code.
    
    Args:
        zip_code: The ZIP code to search for properties.
        
    Returns:
        A list of property listings.
    """
    logging.debug(f"Fetching Zillow listings for ZIP: {zip_code}")
    api_key = os.environ.get("ZILLOW_API_KEY")
    
    if not api_key:
        logging.error("Zillow API key not found in environment variables")
        raise ValueError("Zillow API key not configured. Please set the ZILLOW_API_KEY environment variable.")
    
    url = "https://zillow-com1.p.rapidapi.com/propertyExtendedSearch"
    
    querystring = {
        "location": zip_code,
        "home_type": "All",  # More inclusive to show all property types
        "sort": "Price_Low_High",
        "page": "1"
    }
    
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "zillow-com1.p.rapidapi.com"
    }
    
    try:
        response = requests.get(url, headers=headers, params=querystring)
        response.raise_for_status()  # Raise an exception for non-2xx status codes
        
        data = response.json()
        
        # Check if we have properties in the response
        if "props" not in data or not data["props"]:
            logging.warning(f"No properties found for ZIP code {zip_code}")
            return []
        
        # Accept all property types to be more inclusive
        properties = data["props"]
        logging.debug(f"Found {len(properties)} properties in ZIP {zip_code}")
        return properties
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching Zillow data for ZIP {zip_code}: {str(e)}")
        try:
            if e.response:
                logging.error(f"API response: {e.response.text}")
        except:
            logging.error("Unable to get response details")
        return []
    except (json.JSONDecodeError, KeyError) as e:
        logging.error(f"Error parsing Zillow API response for ZIP {zip_code}: {str(e)}")
        return []
    except Exception as e:
        logging.error(f"Unexpected error with Zillow API for ZIP {zip_code}: {str(e)}")
        return []
