from google.cloud import speech
from google.cloud import texttospeech
import json
from google.cloud import dialogflow


# ###############################
# Google Speech-to-Text part
def speech_to_text(input_audio, client, sample_rate_hertz):
    with open(input_audio, 'rb') as audio_file:
        audio_data = audio_file.read()

    audio = speech.RecognitionAudio(content=audio_data)
    config = speech.RecognitionConfig(
        sample_rate_hertz=sample_rate_hertz,
        enable_automatic_punctuation=True,
        language_code='en-US'
    )

    response = client.recognize(config=config, audio=audio)
    print("Response: ", response)

    response_dict = json.loads(speech.RecognizeResponse.to_json(response))
    print("Response Dict: ", response_dict)

    query_text = response_dict['results'][0]['alternatives'][0]['transcript']
    print("Speech-to-Text completed: " + query_text)

    return query_text


# ###############################
# Google Dialogflow part
def query_dialogeflow(project_id, session_id, text, language_code, client):
    session_path = client.session_path(project_id, session_id)
    print("Session Path: " + session_path)

    text_input = dialogflow.TextInput(text=text, language_code=language_code)
    query_input = dialogflow.QueryInput(text=text_input)

    df_response = client.detect_intent(request={"session": session_path, "query_input": query_input})
    print("Dialogflow Response: ", df_response)

    fulfillment_text = df_response.query_result.fulfillment_text
    print("Dialogflow Query completed: " + fulfillment_text)

    return fulfillment_text


# ###############################
# Google Text-to-Speech part
def text_to_speech(query_reply, client):
    print("Starting Text-to-Speech for: " + query_reply)

    synthesis_input = texttospeech.SynthesisInput(text=query_reply)
    voice_params = texttospeech.VoiceSelectionParams(language_code='en-US',
                                                     ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL)
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)

    response = client.synthesize_speech(input=synthesis_input, voice=voice_params, audio_config=audio_config)
    print("Text-to-Speech completed.")

    return response.audio_content


# ###############################
# Google Text-to-Speech with index part
def text_to_speech_with_index(query_reply, client, index):
    audio_content = text_to_speech(query_reply, client)

    output_file = f"speech_output/output_{index}.mp3"
    with open(output_file, "wb") as file:
        file.write(audio_content)

    print(f"Audio content written to {output_file}")
