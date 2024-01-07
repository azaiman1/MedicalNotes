import openai
import os
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_mail import Mail, Message


def get_env_variable(name: str):
    """
    :param name: str - Name of the environmental variable
    :return: Environmental variable or raise error if the environmental variable is not set
    """
    value = os.getenv(name)
    if not value:
        raise EnvironmentError(f"Missing environment variable: {name}")
    return value



openai_client = openai.OpenAI(api_key=get_env_variable('OPENAI_API_KEY'))

app = Flask(__name__)
app.secret_key = get_env_variable('FLASK_KEY')

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = get_env_variable('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = get_env_variable('MAIL_PASSWORD')
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False


mail = Mail(app)



openai.api_key = get_env_variable('OPENAI_API_KEY')

# Directory to save uploaded files
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'ogg', 'm4a'}

EXAMPLES = ["Input: He is a 77-year-old man who was referred for evaluation of abnormal chest, imaging and concerns for obstructive sleep apnea. Has a history of asthma, environmental, allergies, diabetes, type, two, hypertension, and obesity. He was recently hospitalized at GBMC 11, seven20, 23–11, 14, 2023 with acute atoxic respiratory failure secondary to asthma exacerbation in the setting of a multifocal pneumonia. When he went to the hospital, he complained of shortness of breath, cough, and Beerland sputum. CT chest revealed multifocal nodule infiltrate scattered within the lower lobes. He was treated with antibiotics and has clinically improved and returned to baseline. He has a history of asthma. He was diagnosed as a child. His season is the fall/winter. He has never been hospitalized nor intubated. He does not use medication. His triggers, glue grass, trees and heavy sense. He has had problems with albuterol. He uses private mist once twice daily, but does not take medicine maintenance medication‘s. He played sports in college., He’s nice and short of breath, cough, speed production. He is concerned about, the imaging findings at his mother died of breast cancer at the age of 67 and he’s been extremely worried. He reports that he knew that they died as a child after the heater burst. After the heater got everywhere. He does complain of sinus congestion, and difficulty breathing through his nose. Daytime fatigue. In the hospital he was to noted to have Roxy during the night he goes to sleep between 12 and 2 AM loudly but has not been told of any apneic episodes. He wakes up two times in the night to go to the bathroom between nine and 11, he feels refreshed and does not have a headache. He’ll easily snooze if left alone. ? Output: is a 77 year old man who presents with abnormal imaging and concerns for obstructive sleep apnea. He has a history of asthma, environmental allergies, DM type II, HTN, and obesity. He was recently hospitalized at GBMC 11/7/23 - 11/14/23 with acute hypoxic respiratory failure secondary to an asthma exacerbation in the setting of multifocal pneumonia.  He presented with cough, shortness of breath, and hypoxia.  His initial peak flows were 280 cc.  CT chest revealed multifocal nodular infiltrate scattered within the bilateral lower lobes with ground glass nodular infiltrate in the RML and some scar in left upper lobe along with a 5 mm nodule in the left lower lobe. He was treated with Steroids, Bronchodilators (Symbicort and DuoNebs) as well as Ceftriaxone/Doxycycline, and clinically improved.  Since discharge, he feels he is returned to baseline. He has a history of asthma.  His triggers include grass, trees, and off, and heavy scents.  He was never hospitalized for his asthma nor intubated.  His worst seasons of the cold months (fall).  He does not use any maintenance medications.  In the fall, he uses his Primatene mist on average 1-2 times per day.  He complains of difficulty using albuterol as it dries his throat/lungs out.  If he uses a nebulizer, he has no issues.  He is never felt impaired by his asthma.  He was a physical education teacher for 41 years endplate college sports.  He is able to walk without limit, but does not new stairs because of damaged right knee.  He works out at the gym doing heavy lifting for 30 minutes daily.  He denies any cough, or sputum production.  Initially, he was using Symbicort twice daily, but is only using it daily. He is concerned about the imaging findings.  His mother died of breast cancer at age of 67.  He never smoked.  He reports that he nearly died of coal dust as a child.  The heater exploded and coal dust got everywhere.  He may have been told that he stops breathing, but he never felt impaired.  He does complain of sinus congestion and difficulty breathing through his nose. In the hospital, he was thought to have nocturnal hypoxemia.  He goes to bed between 12:00 a.m. and 2:00 a.m..  He snores loudly, but has not been told of any apneic episodes.  He wakes up at least twice to go to the bathroom.  He wakes up between 9 and 11:00 a.m. generally feeling refreshed but without a headache.  He will easily doze sitting after lunch or watching TV."]


app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename: str):
    """
    :param filename: str - Name of the filename to check
    :return: bool - Boolean indicating if file extension is allowed
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def upload_file():
    """
    :return: Rendered 'upload.html' template for the file upload page
    """
    return render_template('upload.html')


@app.route('/uploader', methods=['GET', 'POST'])
def upload_audio_file():
    """
    Handle the file upload and processing. It uploads the file, processes it,
    sends an email with the response, and provides user feedback.
    :return: Redirects upload page or renders page success message
    """
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']

        # If user does not select file, browser also submits an empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            # Process the file for transcription and get GPT response
            transcript = transcribe_audio(file_path)
            os.remove(file_path)  # Remove file after processing
            response = chat_with_gpt4(transcript)

            # Send email with the GPT response
            subject = f"Transcription for {filename}"
            msg = Message(subject=subject,
                          sender=app.config['MAIL_USERNAME'],
                          recipients=[get_env_variable('RECIPIENT_ADDRESS')],
                          body=response)
            mail.send(msg)

            # Provide feedback to the user
            flash('Email sent successfully!')
            return redirect(url_for('upload_file'))

    return render_template('upload.html')

def transcribe_audio(file_path: str, model="whisper-1", response_format="text") -> str:
    """
    :param file_path: Filepath to audio file being transcribed
    :param model: Model used
    :param response_format: Format of the Response
    :return: String of audio from given file
    """
    # Initialize OpenAI client

    # Open the audio file
    with open(file_path, "rb") as audio_file:
        # Create a transcription request
        transcript = openai_client.audio.transcriptions.create(
            model=model,
            file=audio_file,
            response_format=response_format
        )
    return transcript


def chat_with_gpt4(transcription: str, system_message="You are a helpful medical assistant notetaker.", examples=EXAMPLES, temperature=0.7) -> str:
    """
    :param transcription: String of the audio file transcribed into text
    :param system_message: The system message provided to the LLM
    :param examples: Examples to feed LLM to better understand task
    :param temperature: Temperature of the LLM
    :return: GPT4 response given the parameters
    """
    messages = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    if examples:
        for example in examples:
            messages.append({"role": "system", "content": example})
    messages.append({"role": "user", "content": transcription})

    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=messages,
        temperature=temperature,
        max_tokens=2500
    )
    return response.choices[0].message.content


if __name__ == '__main__':
    app.run(debug=True)
