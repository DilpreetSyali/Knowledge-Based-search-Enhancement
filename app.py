import requests
from flask import Flask, request, jsonify, render_template
import firebase_admin
from firebase_admin import credentials, firestore
import spacy

# Initialize Firebase
cred = credentials.Certificate(r"D:\newproject-2-9a253-firebase-adminsdk-fbsvc-e3b2793510.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Initialize spaCy(NLP WORK!)
nlp = spacy.load("en_core_web_md")

# Google Custom Search API credentials
API_KEY = 'AIzaSyBt5Uwcmz-huJllYUw2wM4PI1ip278TU-A'             #can be changed
CSE_ID = '95619b9796a5b4227'

app = Flask(__name__)

def google_search(query):

    url = f'https://www.googleapis.com/customsearch/v1?q={query}&key={API_KEY}&cx={CSE_ID}'
    try:
        response = requests.get(url)
        # Debugging: print the API response
        print(f"API Response Status Code: {response.status_code}")
        print(f"API Response: {response.text}")
        
        response.raise_for_status()  # This will raise an exception for HTTP errors
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error during API call: {e}")
        return {}

def store_search_history(query):
    
    history_ref = db.collection('search_history')
    # Prevent duplicates
    if not any(doc.to_dict()['query'].lower() == query.lower() for doc in history_ref.stream()):
        history_ref.add({'query': query})

def get_search_history(query):
    """Fetch search history from Firebase Firestore."""
    history_ref = db.collection('search_history')
    docs = history_ref.stream()
    history = []
    for doc in docs:
        if query.lower() in doc.to_dict()['query'].lower():
            history.append(doc.to_dict()['query'])
    return history

def suggest_related_terms(query, search_history):
    """Use spaCy to find related terms based on the query and search history."""
    query_vector = nlp(query).vector
    suggestions = []
    for term in search_history:
        similarity = nlp(term).similarity(nlp(query))
        if similarity > 0.7:  # Adjust threshold for better results
            suggestions.append(term)
    return suggestions

def get_combined_suggestions(query, history_suggestions, dynamic_suggestions):
    """Combine suggestions from search history and dynamic Google search results."""
    combined = list(set(history_suggestions + dynamic_suggestions))
    combined.sort()  # Optional: sort alphabetically
    return combined

@app.route('/')
def home():
    """Render the homepage."""
    return render_template('index.html')

@app.route('/autocomplete')
def autocomplete():
    """Return search suggestions based on the user's query."""
    query = request.args.get('q', '')
    if not query:
        return jsonify({"suggestions": []})

    # Get search history from Firebase
    history = get_search_history(query)

    # Get dynamic suggestions from Google search
    search_results = google_search(query)
    dynamic_suggestions = [item['title'] for item in search_results.get('items', [])]

    # Suggest related terms using NLP (spaCy)
    related_suggestions = suggest_related_terms(query, history)

    # Combine both history and dynamic suggestions
    combined_suggestions = get_combined_suggestions(query, related_suggestions, dynamic_suggestions)

    return jsonify({"suggestions": combined_suggestions})

@app.route('/search')
def search():
    """Perform a search and store the query in Firebase, then return results."""
    query = request.args.get('q', '')
    if not query:
        return jsonify({"results": []})

    # Store the search query in Firebase (only after the search is performed)
    store_search_history(query)

    # Get search results from Google Custom Search API
    search_results = google_search(query)
    results = [
        {"title": item['title'], "url": item['link'], "snippet": item.get('snippet', '')}
        for item in search_results.get('items', [])
    ]
    return jsonify({"results": results})

if __name__ == "__main__":
    app.run(debug=True)
