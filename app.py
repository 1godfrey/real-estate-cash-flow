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

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html', 
                          down_payment=20,  # Default values
                          interest_rate=7,
                          loan_term=30,
                          monthly_expenses=300)

@app.route('/analyze', methods=['POST'])
def analyze():
    # Get form data
    zip_codes = request.form.get('zip_codes', '').strip()
    down_payment = float(request.form.get('down_payment', 20))
    interest_rate = float(request.form.get('interest_rate', 7))
    loan_term = int(request.form.get('loan_term', 30))
    monthly_expenses = float(request.form.get('monthly_expenses', 300))
    min_coc_return = float(request.form.get('min_coc_return', 8))
    min_cash_flow = float(request.form.get('min_cash_flow', 200))
    
    # Validate input
    if not zip_codes:
        flash('Please enter at least one ZIP code', 'danger')
        return redirect(url_for('index'))
    
    # Parse ZIP codes
    zip_list = [zip.strip() for zip in zip_codes.replace(',', '\n').split('\n') if zip.strip()]
    unique_zip_list = list(set(zip_list))  # Remove duplicates
    
    if len(unique_zip_list) > 300:
        flash('Maximum 300 ZIP codes allowed', 'danger')
        return redirect(url_for('index'))
    
    # Store parameters in session for later use
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
        
        for zip_code in unique_zip_list:
            logging.debug(f"Processing ZIP: {zip_code}")
            
            # Check cache for Zillow listings
            cached_listings = get_cached_data(f"zillow_listings_{zip_code}")
            if cached_listings:
                listings = cached_listings
                logging.debug(f"Using cached Zillow data for ZIP {zip_code}")
            else:
                # Get new listings from Zillow API
                listings = get_zillow_listings(zip_code)
                if listings:
                    # Cache the results
                    cache_data(f"zillow_listings_{zip_code}", listings)
            
            if not listings:
                flash(f"No listings found for ZIP code {zip_code}", "warning")
                continue
            
            # Process each listing
            for listing in listings:
                # Get property type, default to "Residential" if not specified
                home_type = listing.get('propertyType', '').lower()
                property_type = "Residential"
                
                # Try to be more specific if we can determine the property type
                if 'single' in home_type:
                    property_type = "Single Family"
                elif 'multi' in home_type:
                    property_type = "Multifamily"
                
                # Get bedrooms and price
                bedrooms = listing.get('bedrooms', 0)
                price = listing.get('price', 0)
                
                if bedrooms < 1 or price < 10000:  # Basic validation
                    continue
                
                # Get rent estimate for the ZIP/bedroom combination
                cache_key = f"rentcast_{zip_code}_{bedrooms}"
                cached_rent = get_cached_data(cache_key)
                
                if cached_rent:
                    rent = cached_rent
                    logging.debug(f"Using cached rent data for {zip_code}/{bedrooms}")
                else:
                    rent = get_rent_estimate(zip_code, bedrooms)
                    if rent:
                        cache_data(cache_key, rent)
                
                if not rent:
                    logging.warning(f"Could not get rent estimate for {zip_code}/{bedrooms}")
                    continue
                
                # Calculate financial metrics
                metrics = calculate_property_metrics(
                    price, 
                    rent, 
                    down_payment, 
                    interest_rate, 
                    loan_term, 
                    monthly_expenses
                )
                
                # Check if property meets filtering criteria
                if metrics['cash_on_cash_return'] < min_coc_return or metrics['cash_flow'] < min_cash_flow:
                    continue
                
                # Create result object
                result = {
                    'address': f"{listing.get('streetAddress', 'Unknown')}, {listing.get('city', '')}, {listing.get('state', '')} {zip_code}",
                    'price': price,
                    'bedrooms': bedrooms,
                    'rent': rent,
                    'mortgage': metrics['mortgage_payment'],
                    'cash_flow': metrics['cash_flow'],
                    'coc_return': metrics['cash_on_cash_return'],
                    'property_type': property_type,
                    'link': listing.get('detailUrl', '#')
                }
                
                all_results.append(result)
        
        # Store results in session
        session['results'] = all_results
        
        if not all_results:
            flash('No properties matched your criteria. Try adjusting your filters.', 'info')
            return redirect(url_for('index'))
            
        return render_template('results.html', 
                             results=all_results, 
                             parameters=session['parameters'],
                             zip_count=len(unique_zip_list))
                             
    except Exception as e:
        logging.error(f"Error analyzing properties: {str(e)}")
        flash(f"An error occurred while analyzing properties: {str(e)}", 'danger')
        return redirect(url_for('index'))

@app.route('/download-csv', methods=['GET'])
def download_csv():
    results = session.get('results', [])
    
    if not results:
        flash('No results to download', 'warning')
        return redirect(url_for('index'))
    
    # Create a CSV string
    output = StringIO()
    fieldnames = ['address', 'price', 'bedrooms', 'rent', 'mortgage', 'cash_flow', 'coc_return', 'property_type', 'link']
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    for result in results:
        writer.writerow(result)
    
    # Create response
    response = Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment;filename=rental_properties_{datetime.now().strftime("%Y%m%d")}.csv'
        }
    )
    
    return response

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500
