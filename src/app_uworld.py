import os
from bs4 import BeautifulSoup
from datetime import datetime
from openai import OpenAI
import time
import threading
import os
import sys
import markdown
import shutil
import imgkit
from dotenv import load_dotenv
load_dotenv()

# Get the API key
openai_api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=openai_api_key)

def convert_html_to_image(html_content, output_path):
    options = {
        'format': 'png',
        'encoding': "UTF-8",
        'quality': 100,
    }
    imgkit.from_string(html_content, output_path, options=options)

# Note: The HTML files should be in the 'html_dump' directory and each html file should have a file name with the question number as the first two characters. Remember to change the directory paths to match your local setup.
# Function to extract text from a given HTML element and remove HTML tags
def extract_text_from_html(html_content, question_div_id, correct_answer_div_class, answer_list_div_id, explanation_div_id, html_file_path):
    soup = BeautifulSoup(html_content, 'html.parser')

    # Extract question
    question_div = soup.find('div', id=question_div_id)
    question_str = question_div.get_text(separator=' ', strip=True) if question_div else ""
    # remove new line characters
    question_str = question_str.replace('\n', ' ')
    # if the first characters are numbers, remove them until the first space
    try:
        question_str = question_str.split(' ', 1)[1]
    except:
        print('Warning: Could not remove the first characters from the question string. Question string might have a number at the beginning but this is not a problem. Manual editing in Anki might be necessary. Continue processing...')
        pass

    # Extract correct answer
    correct_answer_div = soup.find('div', class_=correct_answer_div_class)
    correct_answer_str = correct_answer_div.get_text(separator=' ', strip=True) if correct_answer_div else ""
    # If correct answer string is empty, print warning message.
    if not correct_answer_str:
        print('Warning: Correct answer string is empty. Continue processing...')
    # add new line after the correct answer
    correct_answer_str = correct_answer_str.replace('\n', ' ')
    correct_answer_str = correct_answer_str.replace('Omitted ', ' ')
    correct_answer_str += '</br>'
    #print(correct_answer_str)

    # Extract answer choices
    answer_list_div = soup.find_all('div', id=answer_list_div_id)
    # join the answer choices into a single string while adding the multiple choice letters and new line characters
    answer_list_str = ''.join(''.join([f'{chr(65 + i)}. ', div.get_text(separator=' ', strip=True)]) for i, div in enumerate(answer_list_div))
    # for a string that contains ") {any letter}. ", add a new line character '</br>' before the letter. Flexible to hanle any number of answer choices.
    for i in range(1, 10):
        try:
            answer_list_str = answer_list_str.replace(f') {chr(64 + i)}. ', f')</br>{chr(64 + i)}. ')
        except:
            break
    # remove new line characters
    answer_list_str = answer_list_str.replace('\n', ' ')
    answer_list_str = answer_list_str.replace('A. A. ', 'A. ')
    answer_list_str = '</br>' + answer_list_str

    # Extract explanation
    explanation_divs = soup.find_all('div', id=explanation_div_id)
    explanation_str = '</br></br>'.join(div.get_text(separator=' ', strip=True) for div in explanation_divs)
    # remove new line characters
    explanation_str = explanation_str.replace('\n', ' ')
    explanation_str = explanation_str.replace(' (Choice', '</br></br>(Choice')
    explanation_str = explanation_str.replace('Explanation ', '')
    explanation_str = explanation_str.replace('Topic Copyright © UWorld. All rights reserved.', ' ')
    explanation_str = explanation_str.replace('</br></br></br>Explanation: ', '</br>Explanation: ')
    explanation_str = explanation_str.replace('User Id: 1514650 ', '')

    explanation_str = '</br></br>' + explanation_str

    # Check for images in the HTML file directory
    # Remove the .html extension from the path
    html_dir_path = html_file_path[:-5]
    # add '_files' to the path 
    html_dir_path = html_dir_path + '_files'
    # Check if the image file exists
    if os.path.exists(html_dir_path):
        # Get the list of files in the directory
        html_dir_files = os.listdir(html_dir_path)
        # Check if the list is not empty
        if html_dir_files:
            # Iterate through the list of files
            for file in html_dir_files:
                # Check if the file is an image file
                if file.endswith('.png') or file.endswith('.jpg') or file.endswith('.jpeg') or file.endswith('.gif'):
                    # Copy the image file to the Anki media directory
                    # Get the full path of the image file
                    image_file_path = os.path.join(html_dir_path, file)
                    # Get the destination path in the Anki media directory
                    dest_path = os.path.join(anki_media_path, file)
                    # check that file name does not already exist in the Anki media directory
                    if os.path.exists(dest_path):
                        # add a number to the file name
                        file = file.split('.')
                        file = file[0] + '1.' + file[1]
                        dest_path = os.path.join(anki_media_path, file)
                    # Copy the image file to the Anki media directory
                    shutil.copy(image_file_path, dest_path)
                    # Add the image tag to the end of the explanation string
                    explanation_str += f'<img src="{file}"></img>'

    # Check if there are tables in the html file
    # Extract tables
    # try:
    #     table = soup.findall('table')
    #     table_html = str(table) if table else None
    # except:
    #     table_html = None
    # if table_html:
    #     #file name for the table image based on hour minute and second
    #     current_time = datetime.now().strftime('%H-%M-%S')
    #     output_image_path = os.path.join(anki_media_path, f'{current_time}_table.png')
    #     convert_html_to_image(table_html, output_image_path)
    #     # Add the image tag for this table to the end of the explanation string
    #     explanation_str += f'</br><img src="{current_time}_table.png"></img>'
    
    # combine correct answer and explanation
    back_side = correct_answer_str + answer_list_str + explanation_str
    return question_str, back_side, correct_answer_str, answer_list_str, explanation_str

# Function to format the extracted text into Anki flashcard format
def format_for_anki(question, answer):
    return f"{question}\t{answer}"

# Function to print the status message
def print_status(stop_event):
    while not stop_event.is_set():
        print("Generating text...", end="\r")
        sys.stdout.flush()  # Ensure the message is printed immediately
        time.sleep(2)  # Adjust this value to change the frequency

# Function to extract the JSON object from the response string generated by an LLM agent. Proototyping this function for later iterations of this code.
def extract_json_object_from_prod_agent_response(json_string):
    '''
    Extracts the JSON object from the response string generated by a given production team agent ensuring that if superflous characters outside of the JSON generated by an agent, these characters would be discarded. This JSON object contrains the retrieved pieces of information and the assembled section (from the retrieved information) of the medical note a given agent is responsible for. Agent agnostic.
    '''
    # Find the first occurrence of '{' and the last occurrence of '}'
    start_idx = json_string.find('{')
    end_idx = json_string.rfind('}') + 1
    # Extract the JSON object substring
    json_object_str = json_string[start_idx:end_idx]
    return json_object_str

# Function to use GPT-4o to generate complementary explanations for the questions
def generate_explanations(question, answer):
    # Create a stop event to control the status printing thread
    stop_event = threading.Event()

    # Start the status printing thread
    status_thread = threading.Thread(target=print_status, args=(stop_event,))
    status_thread.start()

    # Record the start time
    start_time = time.time()

    try:
      response = client.chat.completions.create(
          model='chatgpt-4o-latest',
          messages=[
              {
                  "role": "system",
                  "content": "You are a biomedical and medical education expert specializing in preparing students for NBME shelf exams. The level of detail should be proportionate to their relevance to the vignette. Below is a practice question along with its answer.\n\n Vignette Analysis: Identify and explain key words or phrases in the vignette that are critical for diagnosing the condition. Describe how these details help narrow down the differential diagnosis, focusing on what to rule in and rule out.\n\nCorrect Answer Explanation: Clearly explain the reasoning behind the correct answer. Discuss the thought process a student should follow, focusing on learning the core concept.\n\nPathophysiology Review: Provide a brief overview of the disease's pathophysiology, including etiology, risk factors, mechanisms, clinical manifestations, and treatment.\n\nIncorrect Answer Review: Instead of simply stating that the incorrect choice doesn't match the vignette, explain what clinical findings, history details, diagnostic test results, and treatment approaches would be expected if this option were correct. Highlight the key differences between these expected findings and those presented in the vignette."
              },
              {
                  "role": "user",
                  "content": question + '\n' + answer
              }
          ],
          temperature=0.75,
          max_tokens= 4096,
          top_p=1,
          frequency_penalty=0,
          presence_penalty=0
          )
    finally:
        # Stop the status printing thread
        stop_event.set()
        status_thread.join()

    # Calculate the elapsed time
    elapsed_time = time.time() - start_time
    gen_text = response.choices[0].message.content
    #gen_text = gen_text.replace("\t", "&emsp;").replace("\n", "<br>")
    # Wrap the content in a <div> or other HTML tag for better formatting
    gen_text = markdown.markdown(gen_text)
    gen_text = gen_text.replace('\n', '</br>')
    gen_text = gen_text.replace('</p></br><h3>', '</p><h3>')
    gen_text = gen_text.replace('</li></br></ul></br><h3>', '</li></br></ul><h3>')
    gen_text = gen_text.replace('</h3></br><ul></br><li>', '</h3></br><ul><li>')
    #gen_text = gen_text.replace('</li></br><li><strong>', '</li><li><strong>')
    #gen_text = gen_text.replace('</h3></br><ul><li><strong>', '</h3><ul><li><strong>')
    gen_text = '</br>' + gen_text

    # Print the elapsed time
    print(f"\nText generation completed in {elapsed_time:.2f} seconds.")
    return gen_text

# Directory paths
wk_dir ='/Users/morris/github_projects/question_bank_anki_export'
html_dir = wk_dir+'/html_dump'
output_dir = wk_dir+'/import_files'
anki_media_path = '/Users/morris/Library/Application Support/Anki2/User 1/collection.media'

# Create output directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)

# Get current date, hour, minute for the output file name
current_date = datetime.now().strftime('%Y-%m-%d_%H-%M')

output_file_path = os.path.join(output_dir, f'{current_date}.txt')

# Classes to identify the HTML divs
#question_div_class = 'questionListContainer--hbbIy containerMuted--arxU8'
question_div_id = 'questionText'
correct_answer_div_class = 'omitted-answer content d-flex align-items-start flex-column ng-star-inserted'
answer_list_div_id = 'answerContainer'
explanation_div_id = 'explanation-container'

# print number of html files in the directory
html_files = [f for f in os.listdir(html_dir) if f.endswith('.html')]
print(f"Number of HTML files in the directory: {len(html_files)}")

# Process each HTML file in the directory
with open(output_file_path, 'w', encoding='utf-8') as output_file:
    for filename in os.listdir(html_dir):
        if filename.endswith('.html'):
            html_file_path = os.path.join(html_dir, filename)
            # check if the first character in the file name is a number followed by a character, also check if the first two characters are numbers followed by a character, also check if the first three characters are numbers followed by a character. Then use the first one, two, or three characters as the question id suffix.
            if filename[0].isdigit() and filename[1].isalpha():
                question_id_suffix = filename[0]
            elif filename[0].isdigit() and filename[1].isdigit() and filename[2].isalpha():
                question_id_suffix = filename[:2]
            elif filename[0].isdigit() and filename[1].isdigit() and filename[2].isdigit() and filename[3].isalpha():
                question_id_suffix = filename[:3]
            with open(html_file_path, 'r', encoding='utf-8') as html_file:
                html_content = html_file.read()
                question, back_side, correct_answer_str, answer_list_str, explanation_str = extract_text_from_html(
                    html_content, question_div_id, correct_answer_div_class, answer_list_div_id, explanation_div_id, html_file_path
                )
                #print("correct_answer_str: ", correct_answer_str)
                #print("answer_list_str: ", answer_list_str)
                #print("explanation_str: ", explanation_str)
                # print file processing number, e.g., file 1 of 100
                print(f"File {html_files.index(filename)+1} of {len(html_files)}")
                gen_text = generate_explanations(question, correct_answer_str + answer_list_str)
                back_side = back_side + '</br></br>' + gen_text
                anki_format_text = format_for_anki(question, back_side)
                output_file.write(anki_format_text + '\n')
                # Debugging output to verify correct processing
                print(f"Processed file: {filename}")
                print(f"Front side: {question[:70]}")
                print(f"Back side: {back_side[:70]}"+"\n")

print(f"Done. Anki flashcards have been saved to {output_file_path}")