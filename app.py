import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request, jsonify
import joblib
import numpy as np

# Initialize Flask app
app = Flask(__name__)

# Load the trained XGBoost model
model = joblib.load('xgboost_price_model.pkl')

# Initialize Firebase Admin SDK
cred = credentials.Certificate('D://EXPERIMENTS SEM-7//MAJOR PROJECT//MAJOR PROJECT APP//dynamic-pricing-engine-67298-firebase-adminsdk-lnmu5-747f43e0c4.json')
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://dynamic-pricing-engine-67298-default-rtdb.firebaseio.com/'
})

# New logic for adjusting the predicted price
def adjust_price(predicted_price, competitor_price, rating, num_customers, num_views, stock_level, seasonality_index):
    if predicted_price > competitor_price * 1.1:
        predicted_price = competitor_price * 1.05
    if rating >= 4.5:
        predicted_price *= 1.1
    elif rating < 3:
        predicted_price *= 0.9
    if num_customers > 100:
        predicted_price *= 1.05
    elif num_customers < 20:
        predicted_price *= 0.95
    if num_views > 200:
        predicted_price *= 1.03
    elif num_views < 50:
        predicted_price *= 0.97
    if stock_level < 20:
        predicted_price *= 1.08
    elif stock_level > 100:
        predicted_price *= 0.92
    if seasonality_index > 0.7:
        predicted_price *= 1.12
    elif seasonality_index < 0.4:
        predicted_price *= 0.88
    return predicted_price

@app.route('/predict_price', methods=['POST'])
def predict_price():
    try:
        data = request.json
        # Extract the relevant features for prediction
        features = np.array([[data['Number_of_Customers'], 
                              data['Number_of_Views'], 
                              data['Product_Category'], 
                              data['Stock_Level'], 
                              data['Historical_Price'], 
                              data['Competitor_Price'], 
                              data['Seasonality_Index'], 
                              data['Discount_Offered'], 
                              data['Rating']]])

        # Predict the price using the XGBoost model
        predicted_price = model.predict(features)[0]

        # Adjust the predicted price based on custom business logic
        adjusted_price = adjust_price(predicted_price, 
                                      data['Competitor_Price'], 
                                      data['Rating'], 
                                      data['Number_of_Customers'], 
                                      data['Number_of_Views'], 
                                      data['Stock_Level'], 
                                      data['Seasonality_Index'])

        # Push the predicted price to Firebase under a specific product ID
        ref = db.reference('predicted_prices/' + str(data.get('Product_ID', 'unknown_product')))
        ref.set({
            'predicted_price': adjusted_price
        })

        return jsonify({'predicted_price': adjusted_price}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400

# API route to update prices directly from Postman or external sources
@app.route('/update_price', methods=['POST'])
def update_price():
    try:
        data = request.json
        # Example data expected: {"product1": 499, "product2": 399}
        for product, price in data.items():
            ref = db.reference(f'predicted_prices/{product}')
            ref.set({'predicted_price': price})
        
        return jsonify({"message": "Prices updated successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True)