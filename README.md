# Attendify
Backend of Smart attendance system created using flask for testing purposes

## Prerequisites
1. Create a Firebase Admin Account:
    - Go to [Firebase Console](https://console.firebase.google.com/)
    - Create a new project
    - Generate a service account key (Project Settings > Service Accounts)
    - Download the JSON file

2. Create a Pinecone Vector Database Account:
    - Sign up at [Pinecone](https://www.pinecone.io/)
    - Create an API key
    - Create an index

## Environment Setup
1. Create a `.env` file with the following:
```
FIREBASE_CREDENTIALS=path/to/firebase-credentials.json
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_ENVIRONMENT=your_pinecone_environment
PINECONE_INDEX_NAME=your_index_name
```

## Running the Application
Build and start the containers:
```bash
docker-compose up --build -d
```
