import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import pdfplumber
import docx
import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv

# Load environment variables with absolute path
basedir = os.path.abspath(os.path.dirname(__file__))
env_path = os.path.join(basedir, '.env')
load_dotenv(env_path)

app = Flask(__name__)
# Enable CORS so the React/Vanilla frontend can communicate with this API
CORS(app)

# Configure Gemini API
GENAI_API_KEY = os.getenv("GEMINI_API_KEY")
if GENAI_API_KEY:
    genai.configure(api_key=GENAI_API_KEY)
else:
    print("WARNING: GEMINI_API_KEY not found in environment variables.")

# Helper to extract text from a PDF
def extract_text_from_pdf(file_path):
    text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return None
    return text

# Helper to extract text from DOCX
def extract_text_from_docx(file_path):
    try:
        doc = docx.Document(file_path)
        return "\n".join([paragraph.text for paragraph in doc.paragraphs])
    except Exception as e:
        print(f"Error reading DOCX: {e}")
        return None

# Route to test if the server is running
@app.route('/api/status', methods=['GET'])
def status():
    return jsonify({"status": "running", "message": "DEET AI Backend is active."})

# Main processing route
@app.route('/api/extract-resume', methods=['POST'])
def extract_resume():
    if 'resume' not in request.files:
        return jsonify({"error": "No resume file provided"}), 400
        
    file = request.files['resume']
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Save the file temporarily
    temp_path = os.path.join("temp", file.filename)
    os.makedirs("temp", exist_ok=True)
    file.save(temp_path)

    extracted_text = ""
    is_image = False
    
    # Determine File Type and Extract accordingly
    lower_filename = file.filename.lower()
    
    try:
        if lower_filename.endswith('.pdf'):
            extracted_text = extract_text_from_pdf(temp_path)
            
        elif lower_filename.endswith(('.doc', '.docx')):
            extracted_text = extract_text_from_docx(temp_path)
            
        elif lower_filename.endswith(('.txt')):
            with open(temp_path, 'r', encoding='utf-8') as f:
                extracted_text = f.read()
                
        elif lower_filename.endswith(('.png', '.jpg', '.jpeg')):
            is_image = True
            
        else:
            os.remove(temp_path)
            return jsonify({"error": "Unsupported file format. Please upload PDF, DOCX, TXT, or Image."}), 400

        # Step 2: Use LLM to structure the extracted text
        if not GENAI_API_KEY:
            os.remove(temp_path)
            return jsonify({"error": "Gemini API key is not configured on the server."}), 500

        # Create a strict prompt to force JSON output
        system_prompt = """
        You are an expert HR parsing AI. Extract the following information from the resume.
        Return the information ONLY as a valid JSON object matching this exact schema:
        {
            "firstName": "First name of candidate",
            "lastName": "Last name of candidate. If only one name is present, put it in firstName and leave lastName empty",
            "email": "Email address",
            "phone": "Phone number digits only. Remove country codes like +91",
            "dob": "Date of Birth in YYYY-MM-DD format if available, else empty string",
            "gender": "Candidate gender ('male', 'female', or 'others') if apparent or stated, else empty string",
            "socialStatus": "Any mentioned social category (e.g. 'sc', 'st', 'bc', 'general'). Default to empty string",
            "address": {
                "hno": "House number or flat number if available",
                "street": "Street name or area",
                "pincode": "6-digit postal code if available in India, else empty string",
                "city": "City or District name"
            },
            "highestEducation": "The highest degree achieved (e.g., '1' for B.Tech, '2' for Degree, etc. Map 'B.Tech' or 'BE' to 'btech' and 'BSc' or 'BA' to 'degree'. Default to empty string if unsure)",
            "passoutYear": "Year of graduation or passing out in YYYY format. Default to empty string.",
            "schoolName": "Name of the school for 10th/SSC. Default empty.",
            "intermediateName": "Name of the college for 12th/Intermediate/Diploma. Default empty.",
            "languages": ["List of language blocks array"],
            "mandatorySkills": ["List of Technical skills array"],
            "optionalSkills": ["List of Soft skills array"],
            "collegeName": "Name of the most recent university or college",
            "jobType": "Job title or role they are targeting based on experience",
            "expYears": "Total years of professional experience as an integer. Use 0 if none.",
            "expMonths": "Remaining months of experience as an integer (0-11). Use 0 if none.",
            "summary": "A 1-2 sentence professional summary combining their experience. Max 150 characters."
        }
        
        Rules:
        1. If a value is not found, use an empty string "" or empty array [].
        2. Do not include markdown formatting like ```json in the output.
        3. Make sure it is strictly valid JSON that can be parsed by Python's json.loads().
        """

        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # If it's an image, pass the image directly to Gemini's multimodal API
        if is_image:
            with Image.open(temp_path) as img:
                response = model.generate_content([system_prompt, img])
        else:
             # If it's text, ensure we actually got text
            if not extracted_text or len(extracted_text.strip()) < 20:
                os.remove(temp_path)
                return jsonify({"error": "Could not extract readable text from document."}), 422
                
            response = model.generate_content(f"{system_prompt}\n\nResume Text:\n---\n{extracted_text}\n---")
        
        # Clean the response just in case the model adds markdown code blocks
        raw_json_str = response.text.strip()
        if raw_json_str.startswith("```json"):
            raw_json_str = raw_json_str[7:]
        if raw_json_str.endswith("```"):
            raw_json_str = raw_json_str[:-3]
        
        raw_json_str = raw_json_str.strip()
            
        import json
        structured_data = json.loads(raw_json_str)

        # Cleanup temp file
        os.remove(temp_path)
        
        # Step 3: Return the structured data back to the frontend
        return jsonify({
            "status": "success",
            "data": structured_data
        })

    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        print(f"Server Error: {str(e)}")
        return jsonify({"error": f"An internal server error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    # Run the Flask app on port 5000
    app.run(debug=True, port=5000)
