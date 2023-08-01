import streamlit as st
import tempfile
import os
import requests
import openai
from elevenlabs import set_api_key, generate, voices, clone
from st_files_connection import FilesConnection
import pathlib
from typing import List
from pydub.utils import mediainfo
import uuid


def main():
    st.title("Welcome to :red[__Storify__]")
    
    # Instantiate some variables in the session state
    if "generated_story" not in st.session_state:
        st.session_state.generated_story = "Hello, How are you doing? Let's do something amazing!"
    
    if "voice_path" not in st.session_state:
        st.session_state.voice_path = ""

    if "voice_list" not in st.session_state:
        st.session_state.voice_list = []

    if "voice" not in st.session_state:
        st.session_state.voice = ""
    
    if "custom_file" not in st.session_state:
        st.session_state.custom_file = ""

    # Create connection object and retrieve file contents.
    conn = st.experimental_connection('s3', type=FilesConnection)

    def generate_story(prompt):
        
        response = openai.Completion.create(
            engine="text-davinci-003",  # GPT-3.5 Turbo engine
            prompt=prompt,
            max_tokens=150,  # Adjust this based on how long you want the story to be
            n=1,
            stop=None,  # You can specify a stop condition if needed
            temperature=0.7,  # Adjust the temperature to control the randomness of the output
            frequency_penalty=0.0,
            presence_penalty=0.0
        )
        
        return response.choices[0].text.strip()
    

    @st.cache_data(show_spinner=False)
    def get_list_of_voices():
        v = voices()
        st.session_state.voice_list = [v.name for v in v]
    
    def generate_audio(text: str, voice: str = "Rachel", model: str = "eleven_multilingual_v1"):

        audio = generate(text=text, voice=voice, model=model)

        random_file_name = str(uuid.uuid4())

        audio_path = random_file_name + ".mp3"

        try:
            with conn.open("storifybucket/"+audio_path, 'wb') as f:
                f.write(audio)

            return audio_path

        except Exception as e:
            print(e)
            return ""
        
    
    def generate_new_voice(text: str, name: str, description: str, files: List[str]):

        audio_path = name + ".mp3"

        voice = clone(
            name=name,
            description=description,
            files=files
        )
        
        audio = generate(text=text, voice=voice)

        try:
            with conn.open("storifybucket/"+audio_path, 'wb') as f:
                f.write(audio)
            return audio_path

        except Exception as e:
            print(e)
            return ""


    with st.container():
        st.header(":orange[Story Generation]")
        st.write("-----")

        #left_column, right_column = st.columns(1)
        with st.container():
             # User can select to provide full story or generate it
            story_option = st.selectbox("Choose an option:", ["Upload your own story", "Generate story using OpenAI"])
            if story_option == "Upload your own story":
                
                with st.form(key="story_upload_option"):
            
                    uploaded_file = st.file_uploader("Upload your story file", type=["txt"])
                    
                    if uploaded_file is not None:
                        try:
                        # Read the contents of the uploaded file
                            input_story = uploaded_file.read().decode("utf-8")
                            
                            # Display the uploaded story
                            st.text_area("Your uploaded story:", value=input_story, key="user_story", height=300)
                            
                        except Exception as e:
                            st.error(f"Error reading the file: {e}")

                    submit_button = st.form_submit_button(label="Set Story")
                    if submit_button:
                        if input_story in ("", "None", None):
                            st.error("Make sure you enter your story above..")
                        st.session_state.generated_story = input_story


            elif story_option == "Generate story using OpenAI":
                    openai_api_key = st.text_input("Fill OpenAI API Key", type="password")
                    if openai_api_key != "":
                        openai.api_key = openai_api_key
                        with st.form(key="generate_story_form"):

                            story_type = st.selectbox("Select Story:", ["Fairy Tale", "Horror", "Success", "Science Fiction", "Action", "Love", "Thriller", "Comedy"])
                            age = st.selectbox("Age Group:", ["Children", "Teenagers", "Adults"])
                            language = st.selectbox("Language:", ["English"])
                            extra_text = st.text_area("Write story character name/details (Not Required):", "")
                    
                            submit_button = st.form_submit_button(label="Let's Magic")

                            if submit_button:
                                try:
                                    # Create a more descriptive prompt for generating the story
                                    if extra_text:
                                        story_prompt = f"Generate a {age} {story_type} story in {language} language. Additional Information about the story: {extra_text}"
                                    else:
                                        story_prompt = f"Generate a {age} {story_type} story in {language} language."

                                    with st.spinner('Wait for magic...'):
                                        # Generate story (replace this with your AI-based story generation logic)
                                        generated_story = generate_story(prompt=story_prompt)
                                        st.session_state.generated_story = generated_story.lstrip()

                                    st.text_area("Generated Story:", value=st.session_state.story)
                                except UnboundLocalError:  # Catch the specific error you're interested in
                                    st.error("Please enter your OpenAI API Key to do magic.")
            

    
    with st.container():
        st.header(":orange[Audio Generation]")
        st.write("-----")

        with st.container():
            elevenlabs_api_key = st.text_input("Fill ElevenLabs API Key", type="password")
            if elevenlabs_api_key != "":
                set_api_key(elevenlabs_api_key)
                with st.spinner(text="Setting Key, Please wait..."):
                    get_list_of_voices()
                if len(st.session_state.voice_list) > 0:
                    audio_option = st.selectbox("Generate audio:", ["Use default voices", "Custom voice"])
                    if audio_option == "Use default voices":
                        with st.form(key="voice_form"):
                            try:
                                voice = st.selectbox("Choose a voice:", st.session_state.voice_list)
                            except UnboundLocalError as e:
                                st.error(e)
                                voice = st.selectbox("Choose a voice:", ["Rachel"])
                            model = st.selectbox("Choose a model:", ["eleven_multilingual_v1"])
                            st.session_state.voice = voice

                            voice_submit_button = st.form_submit_button(label="Generate Audio")
                            if voice_submit_button:
                                try:
                                    with st.spinner("Generating your audio..."):
                                        # Generate audio
                                        audio = generate_audio(
                                            text=st.session_state.generated_story,
                                            voice=voice,
                                            model=model
                                        )
                                        
                                        print(audio)
                                        st.audio(conn.open("storifybucket/"+audio, mode="rb").read(), format="audio/mp3")
                                        st.session_state.voice_path = audio
                                except UnboundLocalError:  # Catch the specific error you're interested in
                                    st.error("Please enter your ElevenLabs API Key to generate a story.")

                    elif audio_option == "Custom voice":
                        with st.form(key="clone_form"):
                            
                            voice_name = st.text_input("Voice name:", key="voice_name")
                            voice_description = st.text_input(
                                label="Voice description:",
                                key="voice_description",
                                placeholder="Gradma sound"
                                )
                            
                            voice_file = st.file_uploader("Upload a voice sample for the custom voice", type=['mp3', 'wav'])

                            clone_submit_button = st.form_submit_button(label="Generate Audio")

                            if clone_submit_button and voice_file is not None:
                                print(voice_file)

                                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmpfile:
                                    # Write the uploaded audio bytes to temp file
                                    tmpfile.write(voice_file.getvalue())
                                    tmp_filename = tmpfile.name
                                # Add validation for maximum length of the audio file
                                audio_info = mediainfo(tmp_filename)
                                if float(audio_info["duration"]) > 120:
                                    st.error("Uploaded audio is too long. Please upload an audio of maximum 2 minutes.")

                                try:
                                    with st.spinner("Creating custom voice..."):
                                        audio = generate_new_voice(
                                            text=st.session_state.generated_story,
                                            name=voice_name,
                                            description=voice_description,
                                            files=[tmp_filename]
                                        )
                                        st.audio(conn.open("storifybucket/"+audio, mode="rb").read(), format="audio/mp3")
                                        st.session_state.voice = "custom"
                                        st.session_state.voice_path = audio
                                except Exception as e:
                                    print(e)
                                    st.error("Cloning went wrong...")
                                finally:
                                    os.remove(tmp_filename)


    if st.session_state.voice_path != "":
        with st.container():
            st.header(":orange[Video Generation]")
            st.write("-----")

            with st.container():
                video_option = st.selectbox("Generate a video:", ["Upload my video/image", "Generate Using AI"])
                
                if video_option == "Upload my video/image":

                    with st.form(key="custom_video_image_form"):

                        uploaded_file = st.file_uploader("Upload files:", [".png", ".jpg", ".mp4"], accept_multiple_files=False)

                        video_submitt_button = st.form_submit_button("Upload File")
                        
                        if video_submitt_button:
                            with st.spinner("Uploading file..."):
                                random_file_name = str(uuid.uuid4())
                                custom_file_path = random_file_name + pathlib.Path(uploaded_file.name).suffix

                                st.session_state.custom_file = custom_file_path

                                try:
                                    with conn.open("storifybucket/"+custom_file_path, 'wb') as f:
                                        f.write(uploaded_file.read())
                                except Exception as e:
                                    print(e)
                            
                elif video_option == "Generate Using AI":
                        if st.session_state.voice == "custom":
                            gender = st.selectbox("Choose voice gender:", ["male", "female"])
                            st.session_state.custom_file = "character/" + gender + ".png"
                        else:
                            if st.session_state.voice == "Rachel":
                                ext = ".mp4"
                            else:
                                ext = ".png"
                            st.session_state.custom_file = "character/" + st.session_state.voice.lower() + ext
                
                if st.session_state.custom_file != "" : 
                    generate_button = st.button("Generate Video")
                    if generate_button:
                        try:
                            with st.spinner("Generating your video..."):
                                try:
                                    payload = {
                                        "input_face": "https://storifybucket.s3.amazonaws.com/" + st.session_state.custom_file,
                                        "input_audio": "https://storifybucket.s3.amazonaws.com/"+st.session_state.voice_path,
                                    }

                                    response = requests.post("https://api.gooey.ai/v2/Lipsync/",
                                        headers={"Authorization": "Bearer sk-hPpa7h88ZFrgtisdVMZsURODCskCVihRKQF8pWIlCX9pZvyj"},
                                        json=payload,
                                    )

                                    result = response.json()

                                    res = requests.get(result['output']['output_video'])

                                    st.video(res.content, format="video/mp4")

                                    # Download video
                                    st.download_button(
                                        label="Download Video",
                                        data=res.content,
                                        file_name=result['id'] + ".mp4",
                                        mime="video/mp4",
                                        on_click=None
                                    )
                                            
                                except Exception as e:
                                    print(e)

                        except Exception as e:
                                st.error("")

                            

if __name__ == "__main__":
    main()
