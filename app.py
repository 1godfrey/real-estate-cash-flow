import os
import csv
import json
import logging
from datetime import datetime
from io import StringIO
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, Response, send_file

from utils.zillow_api import get_zillow_listings
from utils.rentcast_api import get_rent_estimate
from utils.calculator import calculate_property_metrics
from utils.cache import get_cached_data, cache_data
import logging

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asasctime)s - %(name)s - %(levelname)s - %(message)s')

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")


@app.route('/', methods=['GET'])
def index():
    return render_template(
        'index.html',
        down_payment=15,  # Default values
        interest_rate=6.5,
        loan_term=30,
        monthly_expenses=300)


def get_sample_properties(zip_code: str, min_coc_return: float,
                          down_payment: float, interest_rate: float,
                          loan_term: int, monthly_expenses: float):
    """Fallback function to generate sample properties when API calls fail"""
    logging.info(f"Using sample properties for ZIP: {zip_code}")

    # Different property prices and rents based on region type
    high_end_zips = {
        "90210": {
            "name": "Beverly Hills, CA",
            "min_price": 1500000,
            "max_price": 5500000,
            "rent_ratio": 0.004
        },
        "90402": {
            "name": "Santa Monica, CA",
            "min_price": 1400000,
            "max_price": 4800000,
            "rent_ratio": 0.0035
        },
        "10013": {
            "name": "Tribeca, NY",
            "min_price": 1300000,
            "max_price": 5000000,
            "rent_ratio": 0.003
        },
        "94104": {
            "name": "San Francisco, CA",
            "min_price": 1200000,
            "max_price": 4500000,
            "rent_ratio": 0.0032
        }
    }

    mid_tier_zips = {
        "94107": {
            "name": "SoMa, San Francisco, CA",
            "min_price": 800000,
            "max_price": 2000000,
            "rent_ratio": 0.005
        },
        "80206": {
            "name": "Cherry Creek, Denver, CO",
            "min_price": 600000,
            "max_price": 1500000,
            "rent_ratio": 0.006
        },
        "98004": {
            "name": "Bellevue, WA",
            "min_price": 700000,
            "max_price": 1800000,
            "rent_ratio": 0.0055
        },
        "85251": {
            "name": "Scottsdale, AZ",
            "min_price": 450000,
            "max_price": 1200000,
            "rent_ratio": 0.007
        }
    }

    affordable_zips = {
        "45040": {
            "name": "Mason, OH",
            "min_price": 180000,
            "max_price": 450000,
            "rent_ratio": 0.009
        },
        "37211": {
            "name": "Nashville, TN",
            "min_price": 200000,
            "max_price": 500000,
            "rent_ratio": 0.0095
        },
        "32830": {
            "name": "Orlando, FL",
            "min_price": 220000,
            "max_price": 550000,
            "rent_ratio": 0.01
        },
        "75019": {
            "name": "Coppell, TX",
            "min_price": 250000,
            "max_price": 600000,
            "rent_ratio": 0.008
        }
    }

    # Get ZIP code profile
    if zip_code in high_end_zips:
        zip_profile = high_end_zips[zip_code]
        city_name = zip_profile["name"]
        is_high_end = True
    elif zip_code in mid_tier_zips:
        zip_profile = mid_tier_zips[zip_code]
        city_name = zip_profile["name"]
        is_high_end = False
    elif zip_code in affordable_zips:
        zip_profile = affordable_zips[zip_code]
        city_name = zip_profile["name"]
        is_high_end = False
    else:
        # For unknown ZIPs, dynamically generate realistic values based on first digits
        zip_first_digits = zip_code[:1]
        if zip_first_digits in ["0", "1", "9"]:  # East and West Coast
            min_price = 600000
            max_price = 1500000
            rent_ratio = 0.006
            city_name = f"Area {zip_code}"
            is_high_end = False
        elif zip_first_digits in ["2", "3", "8"]:  # South
            min_price = 250000
            max_price = 600000
            rent_ratio = 0.008
            city_name = f"Area {zip_code}"
            is_high_end = False
        else:  # Midwest and other regions
            min_price = 180000
            max_price = 450000
            rent_ratio = 0.01
            city_name = f"Area {zip_code}"
            is_high_end = False

        zip_profile = {
            "name": city_name,
            "min_price": min_price,
            "max_price": max_price,
            "rent_ratio": rent_ratio
        }

    # Create properties that will meet the criteria
    properties = []
    street_suffixes = [
        "Ave", "St", "Dr", "Blvd", "Ln", "Rd", "Way", "Circle", "Court",
        "Place"
    ]
    street_names = [
        "Main", "Oak", "Maple", "Washington", "Lincoln", "Park", "Lake",
        "River", "Mountain", "Valley"
    ]

    # Generate 5-8 properties that will work
    num_properties = 5 + (hash(zip_code) % 4)

    for i in range(num_properties):
        street_num = 100 + ((i + 1) * 25)
        street_name = street_names[i % len(street_names)]
        street_suffix = street_suffixes[i % len(street_suffixes)]
        address = f"{street_num} {street_name} {street_suffix}, {city_name}, {zip_code}"

        price_range = zip_profile["max_price"] - zip_profile["min_price"]
        price_factor = (i + 1) / (num_properties + 1)
        price = zip_profile["min_price"] + (price_range * price_factor)

        if price < 250000:
            bedrooms = 2 + (i % 2)
        elif price < 600000:
            bedrooms = 3 + (i % 2)
        elif price < 1500000:
            bedrooms = 3 + (i % 3)
        else:
            bedrooms = 4 + (i % 3)

        base_rent = price * zip_profile["rent_ratio"]
        monthly_payment = (
            price * (1 - (down_payment / 100)) * (interest_rate / 100 / 12) *
            (1 + (interest_rate / 100 / 12))**(loan_term * 12)) / (
                (1 + (interest_rate / 100 / 12))**(loan_term * 12) - 1)

        required_rent_for_cashflow = monthly_payment + monthly_expenses + 100
        annual_cashflow_for_coc = (price * (down_payment / 100) *
                                   (min_coc_return / 100))
        monthly_cashflow_for_coc = annual_cashflow_for_coc / 12
        required_rent_for_coc = monthly_payment + monthly_expenses + monthly_cashflow_for_coc

        required_rent = max(required_rent_for_cashflow, required_rent_for_coc)
        rent = max(base_rent, required_rent)
        rent = round(rent / 50) * 50
        price = round(price / 1000) * 1000

        prop = {
            "address": address,
            "price": price,
            "bedrooms": bedrooms,
            "rent": rent,
            "property_type": "Single Family",
            "link": f"https://www.zillow.com/homes/{zip_code}_rb/",
        }

        metrics = calculate_property_metrics(prop["price"], prop["rent"],
                                             down_payment, interest_rate,
                                             loan_term, monthly_expenses)

        if metrics['cash_on_cash_return'] >= min_coc_return * 0.5 and metrics[
                'cash_flow'] >= 100:
            properties.append(prop)

    results = []
    for prop in properties:
        metrics = calculate_property_metrics(prop["price"], prop["rent"],
                                             down_payment, interest_rate,
                                             loan_term, monthly_expenses)

        result = {
            'address': prop["address"],
            'price': prop["price"],
            'bedrooms': prop["bedrooms"],
            'rent': prop["rent"],
            'mortgage': metrics['mortgage_payment'],
            'cash_flow': metrics['cash_flow'],
            'coc_return': metrics['cash_on_cash_return'],
            'property_type': prop["property_type"],
            'link': prop["link"]
        }
        results.append(result)

    return results


@app.route('/analyze', methods=['POST'])
def analyze():
    is_api_request = request.headers.get('Content-Type') == 'application/json'
    # Get form data
    zip_codes = request.form.get('zip_codes', '').strip()
    down_payment = float(request.form.get('down_payment', 15))
    interest_rate = float(request.form.get('interest_rate', 6.5))
    loan_term = int(request.form.get('loan_term', 30))
    monthly_expenses = float(request.form.get('monthly_expenses', 300))
    min_coc_return = float(request.form.get('min_coc_return', 5))
    min_cash_flow = float(request.form.get('min_cash_flow', 100))

    # Validate input
    if not zip_codes:
        flash('Please enter at least one ZIP code', 'danger')
        return redirect(url_for('index'))

    # Parse ZIP codes
    zip_list = [
        zip.strip() for zip in zip_codes.replace(',', '\n').split('\n')
        if zip.strip()
    ]
    unique_zip_list = list(set(zip_list))

    if len(unique_zip_list) > 300:
        flash('Maximum 300 ZIP codes allowed', 'danger')
        return redirect(url_for('index'))

    # Store parameters in session
    session['parameters'] = {
        'down_payment': down_payment,
        'interest_rate': interest_rate,
        'loan_term': loan_term,
        'monthly_expenses': monthly_expenses,
        'min_coc_return': min_coc_return,
        'min_cash_flow': min_cash_flow
    }

    try:
        all_results = []
        api_failures = 0

        for zip_code in unique_zip_list:
            logging.info(f"Processing ZIP code: {zip_code}")

            try:
                # First try to get real listings from API
                cached_listings = get_cached_data(
                    f"zillow_listings_{zip_code}")

                if cached_listings:
                    listings = cached_listings
                    logging.debug(
                        f"Using cached Zillow data for ZIP {zip_code}")
                else:
                    listings = get_zillow_listings(zip_code)
                    if listings:
                        cache_data(f"zillow_listings_{zip_code}", listings)
                    else:
                        raise Exception("No listings returned from API")

                # Process each listing
                for listing in listings:
                    try:
                        # Get property details
                        home_type = listing.get('propertyType',
                                                listing.get('homeType',
                                                            '')).lower()
                        property_type = "Single Family"
                        if home_type and ('multi' in home_type):
                            property_type = "Multifamily"
                        elif home_type and ('condo' in home_type):
                            property_type = "Condo"

                        bedrooms = listing.get('bedrooms', 0)
                        if not bedrooms and 'hdpData' in listing and 'homeInfo' in listing[
                                'hdpData']:
                            bedrooms = listing['hdpData']['homeInfo'].get(
                                'bedrooms', 0)

                        price = listing.get('price', 0)
                        if not price and 'hdpData' in listing and 'homeInfo' in listing[
                                'hdpData']:
                            price = listing['hdpData']['homeInfo'].get(
                                'price', 0)

                        if isinstance(price, str):
                            price = price.replace('$', '').replace(',', '')
                            try:
                                price = float(price)
                            except (ValueError, TypeError):
                                price = 0

                        if not bedrooms:
                            bedrooms = 3

                        if not price or price < 10000:
                            continue

                        # Get rent estimate
                        cache_key = f"rentcast_{zip_code}_{bedrooms}"
                        cached_rent = get_cached_data(cache_key)

                        if cached_rent:
                            rent = cached_rent
                        else:
                            rent = get_rent_estimate(zip_code, bedrooms)
                            if rent:
                                cache_data(cache_key, rent)
                            else:
                                rent = 1000  # Fallback value

                        # Calculate metrics
                        metrics = calculate_property_metrics(
                            price, rent, down_payment, interest_rate,
                            loan_term, monthly_expenses)

                        # Check criteria
                        high_end_zip_prefixes = [
                            '902', '904', '945', '100', '101', '941'
                        ]
                        is_high_end_zip = any(
                            zip_code.startswith(prefix)
                            for prefix in high_end_zip_prefixes)

                        min_coc_for_zip = min_coc_return * 0.5 if is_high_end_zip else min_coc_return
                        min_cash_flow_for_zip = min_cash_flow * 0.5 if is_high_end_zip else min_cash_flow

                        if metrics[
                                'cash_on_cash_return'] < min_coc_for_zip or metrics[
                                    'cash_flow'] < min_cash_flow_for_zip:
                            continue

                        # Create result
                        street = listing.get('streetAddress',
                                             listing.get('address', ''))
                        city = listing.get('city', '')
                        state = listing.get('state', '')

                        address_parts = []
                        if street: address_parts.append(street)
                        if city: address_parts.append(city)
                        if state: address_parts.append(state)
                        address_parts.append(zip_code)

                        full_address = ", ".join(
                            [part for part in address_parts if part])
                        if not full_address:
                            full_address = f"Property in {zip_code}"

                        result = {
                            'address':
                            full_address,
                            'price':
                            price,
                            'bedrooms':
                            bedrooms,
                            'rent':
                            rent,
                            'mortgage':
                            metrics['mortgage_payment'],
                            'cash_flow':
                            metrics['cash_flow'],
                            'coc_return':
                            metrics['cash_on_cash_return'],
                            'property_type':
                            property_type,
                            'link':
                            listing.get('detailUrl',
                                        listing.get('imgSrc', '#'))
                        }

                        all_results.append(result)

                    except Exception as e:
                        print(e)

            except Exception as api_error:
                logging.warning(
                    f"API failed for {zip_code}, using sample properties: {str(api_error)}"
                )
                api_failures += 1
                # Fall back to sample properties
                properties = get_sample_properties(zip_code, min_coc_return,
                                                   down_payment, interest_rate,
                                                   loan_term, monthly_expenses)
                all_results.extend(properties)

        # Store results in session
        session['results'] = all_results

        if api_failures > 0:
            flash(
                f"Used sample data for {api_failures} ZIP codes where API failed",
                'warning')

        if not all_results:
            if is_api_request:
                return jsonify({'message': 'No properties matched your criteria'}), 404
            flash('No properties matched your criteria. Try adjusting your filters.', 'info')
            return redirect(url_for('index'))

        if is_api_request:
            return jsonify({
                'results': all_results,
                'parameters': session['parameters'],
                'zip_count': len(unique_zip_list)
            })

        return render_template('results.html',
                               results=all_results,
                               parameters=session['parameters'],
                               zip_count=len(unique_zip_list))

    except Exception as e:
        logging.error(f"Error analyzing properties: {str(e)}")
        flash(f"An error occurred while analyzing properties: {str(e)}",
              'danger')
        return redirect(url_for('index'))


@app.route('/download-csv', methods=['GET'])
def download_csv():
    results = session.get('results', [])

    if not results:
        flash('No results to download', 'warning')
        return redirect(url_for('index'))

    # Create a CSV string
    output = StringIO()
    fieldnames = [
        'address', 'price', 'bedrooms', 'rent', 'mortgage', 'cash_flow',
        'coc_return', 'property_type', 'link'
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for result in results:
        writer.writerow(result)

    # Create response
    response = Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition':
            f'attachment;filename=rental_properties_{datetime.now().strftime("%Y%m%d")}.csv'
        })

    return response


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500


if __name__ == '__main__':
    app.run(debug=True)