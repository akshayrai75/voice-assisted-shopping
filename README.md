# voice-assisted-shopping
project aimed at enhancing online ordering accessibility for differently-abled individuals, featuring a voice-activated chatbot.

### Steps to run
#### Step 1 - 
Create google cloud API key for Google dialogflow and for speech2text/text2speech services.<br />
#### Step 2 - 
create a db with test data provided in *test_db_dump* folder.<br />
#### Step 3 - 
Create a Google dialogflow chatbot with matching intents mentioned in *process_intent* function of *main.py* and connection to our db or receiving out data, and test it's functioning in the google provided UI. (I could not share that, dont know how).<br />
reference code from google docs: https://cloud.google.com/dialogflow/es/docs/quick/api<br />
YouTube reference: https://www.youtube.com/watch?v=2e5pQqBvGco <br />
#### Step 4 - 
Install requirements.txt for this project. Then test the working of all the functions mentioned in *google_cloud_service.py* which is about connection to google cloud services like dialogflow, speech2text and text2speech from our app.<br />
reference code from google docs: <br />
https://cloud.google.com/text-to-speech/docs/libraries#client-libraries-install-python<br />
https://cloud.google.com/speech-to-text/docs/speech-to-text-client-libraries#client-libraries-install-python<br />
#### Step 5 - 
Used sqlalchemy for app connection with db and fast-api for api creation through *db_connect.py, db_models.py and main.py*. Run the *main.py* file to enable backend functionality.<br />
#### Step 6 - 
Run the *index.html* file in *voice-assisted-shopping-test_ui* folder and test the functionality. The voice recording starts at on-key-down of "space-bar key" and stops at on-key-up. And then you hear a voice output. The conversation is continued until end-condition commands are met or an error occurs.