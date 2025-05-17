import os
from bs4 import BeautifulSoup
from datetime import datetime
from openai import OpenAI
import time
import threading
import os
import sys
from dotenv import load_dotenv
load_dotenv()

# Get the API key
openai_api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=openai_api_key)


# Note: The HTML files should be in the 'html_dump' directory and each html file should have a file name with the question number as the first two characters. Remember to change the directory paths to match your local setup.
# Function to extract text from a given HTML element and remove HTML tags
def extract_text_from_html(html_content, question_id, correct_answer_div_class, explanation_div_class):
    soup = BeautifulSoup(html_content, 'html.parser')

    # Extract question
    question_div = soup.find('div', id=question_id)
    question_str = question_div.get_text(separator=' ', strip=True) if question_div else ""
    # remove new line characters
    question_str = question_str.replace('\n', ' ')
    # if the first characters are numbers, try to remove them until the first space
    try:
        if question_str[0].isdigit():
            question_str = question_str.split(' ', 1)[1]
    except:
        print(f"<----Warning: Did not find a number as the first character in the question string.---> {question_id}")
        print(f"<----Warning: Question string contents---> {question_str}")

    # Extract correct answer
    correct_answer_div = soup.find('div', class_=correct_answer_div_class)
    correct_answer_str = correct_answer_div.get_text(separator=' ', strip=True) if correct_answer_div else ""
    # if the correct answer string is empty, try the alternative class name
    if not correct_answer_str:
        correct_answer_div = soup.find('div', class_=correct_answer_div_class_alt)
        correct_answer_str = correct_answer_div.get_text(separator=' ', strip=True) if correct_answer_div else ""
    if not correct_answer_str:
        correct_answer_div = soup.find('div', class_=correct_answer_div_class_alt_2)
        correct_answer_str = correct_answer_div.get_text(separator=' ', strip=True) if correct_answer_div else ""
    if not correct_answer_str:
        correct_answer_div = soup.find('div', class_=correct_answer_div_class_alt_3)
        correct_answer_str = correct_answer_div.get_text(separator=' ', strip=True) if correct_answer_div else ""           
    # if the correct answer string is still empty, print a warmning message
    if not correct_answer_str:
        print(f"<----Warning: Correct answer not found for question---> {question_id}")

    # add new line after the correct answer
    correct_answer_str = correct_answer_str.replace('\n', ' ')
    correct_answer_str = correct_answer_str.replace('Give feedback', '')
    correct_answer_str += '</br>'
    correct_answer_str = 'Correct Answer: ' + correct_answer_str
    #print(correct_answer_str)

    # Extract explanation
    explanation_divs = soup.find_all('div', class_=explanation_div_class)
    # if the explanation divs are empty, print a warmning message
    if not explanation_divs:
        print(f"<----Warning: Explanation not found for question---> {question_id}")
    explanation_str = '</br></br>'.join(div.get_text(separator=' ', strip=True) for div in explanation_divs)
    # remove new line characters
    explanation_str = explanation_str.replace('\n', ' ')
    # remove 'Give feedback' text
    explanation_str = explanation_str.replace('Give feedback', '')
    explanation_str = '</br>' + explanation_str

    # combine correct answer and explanation
    back_side = correct_answer_str + explanation_str


    return question_str, back_side, correct_answer_str, explanation_str

# Function to format the extracted text into Anki flashcard format
def format_for_anki(question, answer):
    return f"{question}\t{answer}"

# Function to print the status message
def print_status(stop_event):
    while not stop_event.is_set():
        print("Generating text...", end="\r")
        sys.stdout.flush()  # Ensure the message is printed immediately
        time.sleep(2)  # Adjust this value to change the frequency

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
          model='gpt-4o-2024-08-06',
          messages=[
              {
                  "role": "system",
                  "content": "You are a medical education expert specializing in preparing students for NBME shelf exams. The level of detail should be proportionate to their relevance to the vignette. Below is a practice question along with its answer.\n\n Vignette Analysis: Identify and explain key words or phrases in the vignette that are critical for diagnosing the condition. Describe how these details help narrow down the differential diagnosis, focusing on what to rule in and rule out.\n\nCorrect Answer Explanation: Clearly explain the reasoning behind the correct answer. Discuss the thought process a student should follow, focusing on learning the core concept.\n\nPathophysiology Review: Provide a brief overview of the disease's pathophysiology, including etiology, risk factors, mechanisms, clinical manifestations, and treatment.\n\nIncorrect Answer Review: Instead of simply stating that the incorrect choice doesn't match the vignette, explain what clinical findings, history details, diagnostic test results, and treatment approaches would be expected if this option were correct. Highlight the key differences between these expected findings and those presented in the vignette."
              },
              {
                  "role": "user",
                  "content": question + '\n' + answer
              }
          ],
          temperature=0.75,
          #max_tokens=4096,
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
    gen_text = gen_text.replace("\t", "&emsp;").replace("\n", "<br>")
    # Wrap the content in a <div> or other HTML tag for better formatting
    gen_text = f"<div>{gen_text}</div>"

    # Print the elapsed time
    print(f"\nText generation completed in {elapsed_time:.2f} seconds.")
    return gen_text

# Directory paths
wk_dir ='/Users/morris/github_projects/question_bank_anki_export'
html_dir = wk_dir+'/html_dump'
output_dir = wk_dir+'/gen_anki'

# Create output directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)

# Get current date, hour, minute for the output file name
current_date = datetime.now().strftime('%Y-%m-%d_%H-%M')

output_file_path = os.path.join(output_dir, f'{current_date}.txt')

# Classes to identify the HTML divs
#question_div_class = 'questionListContainer--hbbIy containerMuted--arxU8'
correct_answer_div_class = 'container--CKAXW correctAnswer--xNrke'
correct_answer_div_class_alt = 'container--CKAXW pointer--eMKos correctAnswer--xNrke'
correct_answer_div_class_alt_2 = 'container--CKAXW pointer--eMKos correctAnswer--xNrke'
correct_answer_div_class_alt_3 = '-f8b48b6542a07-container -f8b48b6542a07-pointer -f8b48b6542a07-correctAnswer'

explanation_div_class = '-f8b48b6542a07-explanationContainer'

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
                question_id = f'FLaJnh0OIM_{question_id_suffix}'
                question, back_side, correct_answer_str, explanation_str = extract_text_from_html(
                    html_content, question_id, correct_answer_div_class, explanation_div_class
                )
                print(f"File {html_files.index(filename)+1} of {len(html_files)}")
                gen_text = generate_explanations(question, correct_answer_str)
                back_side = back_side + '</br></br>' + gen_text
                anki_format_text = format_for_anki(question, back_side)
                output_file.write(anki_format_text + '\n')
                # Debugging output to verify correct processing
                print(f"Processed file: {filename}")
                print(f"Question: {question[:80]}")
                print(f"Back side: {back_side[:80]}"+"\n")

print(f"Done. Anki flashcards have been saved to {output_file_path}")