import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk.corpus import stopwords
from urllib.parse import parse_qs, urlparse
import json
import pandas as pd
from datetime import datetime
import uuid
import os
from typing import Callable, Any
from wsgiref.simple_server import make_server

nltk.download('vader_lexicon', quiet=True)
nltk.download('punkt', quiet=True)
nltk.download('averaged_perceptron_tagger', quiet=True)
nltk.download('stopwords', quiet=True)

adj_noun_pairs_count = {}
sia = SentimentIntensityAnalyzer()
stop_words = set(stopwords.words('english'))

reviews = pd.read_csv('data/reviews.csv').to_dict('records')

class ReviewAnalyzerServer:
    def __init__(self) -> None:
        # This method is a placeholder for future initialization logic
        pass

    def analyze_sentiment(self, review_body):
        sentiment_scores = sia.polarity_scores(review_body)
        return sentiment_scores

    def __call__(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> bytes:
        """
        The environ parameter is a dictionary containing some useful
        HTTP request information such as: REQUEST_METHOD, CONTENT_LENGTH, QUERY_STRING,
        PATH_INFO, CONTENT_TYPE, etc.
        """

        if environ["REQUEST_METHOD"] == "GET":
                #Create the response body from the reviews and convert to aJSON byte string
            response_body = json.dumps(reviews, indent=2).encode("utf=8")
            
            # Here's Mycode
            

            # Set the appropriate response headers
            start_response("200 OK", [
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(response_body)))
             ])
            
            return [response_body]     
        if environ["REQUEST_METHOD"] == "GET":
            # Parse query parameters
            query_params = parse_qs(environ.get('QUERY_STRING', ''))
            location = query_params.get('location', [None])[0]
            start_date = query_params.get('start_date', [None])[0]
            end_date = query_params.get('end_date', [None])[0]

            # Filter reviews based on query parameters
            filtered_reviews = [review for review in reviews if
                                (not location or review['Location'] == location) and
                                (not start_date or review['Timestamp'] >= start_date) and
                                (not end_date or review['Timestamp'] <= end_date)]

            # Add sentiment analysis to each review
            for review in filtered_reviews:
                review['sentiment'] = self.analyze_sentiment(review['ReviewBody'])

            # Sort reviews by compound sentiment score in descending order
            filtered_reviews.sort(key=lambda x: x['sentiment']['compound'], reverse=True)

            # Create the response body and convert to a JSON byte string
            response_body = json.dumps(filtered_reviews, indent=2).encode("utf-8")

            # Set the appropriate response headers
            start_response("200 OK", [
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(response_body)))
            ])

            return [response_body]


        if environ["REQUEST_METHOD"] == "POST":
            try:
                # Read the request body
                content_length = int(environ.get('CONTENT_LENGTH', 0))
                request_body = environ['wsgi.input'].read(content_length).decode('utf-8')
                post_params = parse_qs(request_body)

                # Extract the location and review body from the request
                location = post_params.get('Location', [None])[0]
                review_body = post_params.get('ReviewBody', [None])[0]

                if location and review_body:
                    # Create a new review
                    review_id = str(uuid.uuid4())
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    new_review = {
                        'ReviewId': review_id,
                        'Location': location,
                        'ReviewBody': review_body,
                        'Timestamp': timestamp
                    }

                    # Add the new review to the reviews list
                    reviews.append(new_review)

                    # Optionally save to CSV to persist the data
                    pd.DataFrame(reviews).to_csv('data/reviews.csv', index=False)

                    # Create the response body and convert to a JSON byte string
                    response_body = json.dumps(new_review, indent=2).encode("utf-8")

                    # Set the appropriate response headers
                    start_response("201 Created", [
                        ("Content-Type", "application/json"),
                        ("Content-Length", str(len(response_body)))
                    ])

                    return [response_body]
                else:
                    start_response("400 Bad Request", [("Content-Type", "text/plain")])
                    return [b"Location and ReviewBody are required fields"]

            except Exception as e:
                start_response("500 Internal Server Error", [("Content-Type", "text/plain")])
                return [str(e).encode("utf-8")]


if __name__ == "__main__":
    app = ReviewAnalyzerServer()
    port = os.environ.get('PORT', 8000)
    with make_server("", port, app) as httpd:
        print(f"Listening on port {port}...")
        httpd.serve_forever()