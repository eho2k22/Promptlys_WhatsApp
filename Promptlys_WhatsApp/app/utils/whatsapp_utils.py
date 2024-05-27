import logging
from flask import current_app, jsonify
import json
import requests
import tempfile
import hashlib
import shelve
import time
from datetime import datetime
import re 
import phonenumbers

from io import BytesIO
import os

# from app.services.openai_service import generate_response
import re

from dotenv import load_dotenv
import os

from openai import OpenAI
from supabase import create_client, Client


#load_dotenv('example.env')

# Replace with your Supabase service role key
print("SUPABASE CREDENTIALS are : ")
print(os.getenv("SUPABASE_URL"))
print(os.getenv("SUPABASE_KEY"))

print("OPENAI API KEY CREDENTIALS are : ")
print(os.getenv("OPENAI_API_KEY"))

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

print("OPENAI_API_KEY = ")
print( os.getenv("OPENAI_API_KEY") )

client = OpenAI(api_key = os.getenv("OPENAI_API_KEY"))

indicators = ["up-to-the-minute", "provide real-time", "most recent", "up-to-date", "most current", "most recent information", "provide real-time traffic", "get real-time traffic", "up-to-date data", "up-to-date information", "unable to find real-time information", "cannot provide current data", "real-time data not available", "current insights", "current data", "For real-time"]

indicators_img = ["build an image", "generate an image", "draw an image", "make an image", "build image", "generate image", "draw image", "make image", "build image", "generate image", "draw image", "make image" ]


# Predefined responses #######
about_response = (
    "Promptlys is a Professional Prompt Platform whose mission is to amplify your generative AI communications via effective prompting.\n\n"
    "On Promptlys, you can input a general topic and the prompt generator will produce a list of prompts that convert your intentions into relevant, well-constructed prompts.\n\n"
    "On Promptlys, you can search a library of publicly shared prompts by keyword or category, connect with prompt experts, and subscribe to premium prompt experts channels.\n\n"
    "You can generate 8 images for free with /image followed by prompt text, and pay $10 for 25 images more ! \n\n"
    "Promptlys is built on a freemium model. With a $100/year subscription you can access premium and customized prompts that can save thousands per month, for hiring a copywriter, graphic designer, or a programmer.\n\n"
    "Please visit us at our website: https://demo.promptlys.ai"
)

about_response_cn = (
    "Promptlys是一个专业的提示平台，其使命是通过有效的提示增强您的生成性AI通信。\n\n"
    "在Promptlys上，您可以输入一个通用主题，提示生成器将产生一系列提示，将您的意图转换为相关的、结构良好的提示。\n\n"
    "在Promptlys上，您可以通过关键词或类别搜索公共共享的提示库，连接提示专家，并订阅高级提示专家频道。\n\n"
    "您可以免费生成8张图片，每个提示文本后跟‘/image’，如果您希望构建更多，可以支付10美元购买25张图片！\n\n"
    "Promptlys建立在免费增值模型上。通过支付100美元/年的订阅费，您可以访问高级和定制提示，每月可以节省数千美元用于聘请文案撰写人员、平面设计师或程序员。\n\n"
    "请访问我们的网站：https://demo.promptlys.ai "

)

guide_response = (
    "1. Type  '/about' to browse what Promptlys is about and visit its website for more info!! \n\n"
    "2. Prefix '/prompt' to your prompt description and Promptlys will revise and enhance your prompt! \n\n"
    "3. Prefix '/image' to a prompt then Promptlys will generate an image !  . \n\n"
    "You can generate up to 8 images for free, then pay $10 for 25 images if you wish to build more. \n\n"
    "4. Prefix '/prompt_img' to your image descriptors and Promptlys will level up your prompt that builds powerful images  .   \n\n"
    "5. Type away in chat and Promptlys will engage and respond to your questions!! \n\n"
    "6. Type '/guide' or '/help' to review Promptlys Bot instructions"
)

guide_response_cn = (
    "1. 输入‘/about’来浏览Promptlys的相关信息并访问其网站了解更多信息！\n\n"
    "2. 在您的提示描述前加上‘/prompt’，Promptlys将修订并增强您的提示！\n\n"
    "3. 在提示前加上‘/image’，然后Promptlys将生成一张图片！\n\n"
    "您可以免费生成多达8张图片，然后如果您希望构建更多，可以支付10美元购买25张图片。\n\n"
    "4. 在您的图像描述符前加上‘/prompt_img’，Promptlys将提升您的提示，构建强大的图像。\n\n"
    "5. 在聊天中输入，Promptlys将参与并回答您的问题！\n\n"
    "6. 输入‘/guide’或‘/help’以查看Promptlys机器人指南"
)

instruction_message = (
    "Please upload your document by selecting the 'Document' icon ( \U0001F4C4 ) and choosing your file. \n\n "
    "Once uploaded, we will process it and you can start asking questions about its content."

)

assistant_instruction_message = (
    "Your files have been uploaded and added to my knowledge base.  Please ask away !  \n\n "
)

### Amanda GPT Keyword Filters ###

# Detect if the user is a seller or a buyer based on keywords
seller_keywords = ['sell', 'listing', 'market value', 'selling', 'sale', 'for sale']
buyer_keywords = ['buy', 'purchase', 'homes for sale']


### IRIS GPT Keyword Filters ###

iris_prospects_keywords = ['need help with my taxes', 'international tax advice', 'international tax services',  'tax planning for foreign income', 'speak with a tax consultant', 'speak with an international tax expert' ]



##### User Account Helper Function #####

def set_user_mode(wa_id, mode):
   supabase.table("Bot_Accounts").update({
            "Mode": mode,
            }).eq("tg_id", wa_id).execute()

def clear_user_mode(wa_id):
    # Reset the user's mode in the database to 'none' (0)
    try: 
        supabase.table("Bot_Accounts").update({"Mode": 0}).eq("tg_id", wa_id).execute()
        print(f"Mode cleared for user {wa_id}")
    except Exception as e:
        print(f"Error Clearing User mode: {e}")


def get_current_user_mode(wa_id):
    user_results = []
    user_mode = 0

    user_results = supabase.table('Bot_Accounts').select("Mode").eq("tg_id", wa_id).execute()
    print("User Mode Query results is: ")
    print(user_results)
    if user_results.data:
        user_mode = user_results.data[0]["Mode"]
    print(f"user {wa_id} has mode = {user_mode}")
    return user_mode


def get_current_user_locale(wa_id):
    user_results = []
    user_locale = ''

    user_results = supabase.table('Bot_Accounts').select("tg_locale").eq("tg_id", wa_id).execute()
    print("User Mode Query results is: ")
    print(user_results)
    if user_results.data:
        user_locale = user_results.data[0]["tg_locale"]
    print(f"user {wa_id} has Locale = {user_locale}")
    return user_locale

def get_country_from_phone_number(wa_id):
    try:
        # Assuming most users are from the United States, use "US" as default region
        phone_number = wa_id
        if not phone_number.startswith('+'):
            # Assuming the phone_number is complete but missing the '+'
            phone_number = '+' + phone_number
        parsed_number = phonenumbers.parse(phone_number, "US")
        country_code = phonenumbers.region_code_for_number(parsed_number)
        print(f"user {wa_id} Country Code = {country_code}")
        return country_code
    except phonenumbers.NumberParseException as e:
        print(f"Error parsing phone number: {e}")
        return None


### Prospects Helper Function ####


def set_prospect_role(wa_id, role, assistant_mode):
    # Check if a record exists for the given wa_id
    user_exists = supabase.table("Prospects").select("id").eq("user_id", wa_id).eq("assistant_mode", assistant_mode).execute()

    # If the prospect exists, update the existing record
    if user_exists.data:
        supabase.table("Prospects").update({
            "user_role": role
        }).eq("user_id", wa_id).execute()
    else:
        # If no record exists, create a new Prospect record
        print("No User Role exists,  create a new record")
        supabase.table("Prospects").insert({
            "user_id": wa_id,
            "user_role": role,
            "user_state" : "awaiting_contact_info", 
            "assistant_mode" : assistant_mode
        }).execute()




def get_prospect_info(wa_id, assistant_mode):
    ##response = supabase.table("Prospects").select("*").eq("user_id", wa_id).execute()
    response = supabase.table("Prospects").select("*").eq("user_id", wa_id).eq("assistant_mode", assistant_mode).execute()

    # Check if the query was successful and if data exists
    if response.data and response.data[0]:
        # Assuming the response data is a list of records, return the first one
        return response.data[0]
    else:
        # Create a new record if none exists
        new_user_data = {
            "user_id": wa_id,
            "user_role": 0,
            "user_state": "awaiting_contact_info",
            "assistant_mode" : assistant_mode
        }
        insert_response = supabase.table("Prospects").insert(new_user_data).execute()
        if not insert_response:
            print(f"Error creating new Prospect info for wa_id {wa_id} ")
            return {}
        print(f"New user record created for wa_id {wa_id}")
        return new_user_data  # Return the newly created record
        



def parse_contact_info(message):

    # Ensure there is at least one comma in the message
    if ',' not in message:
        return (None, None, None, 0)

    # Split the message into parts
    parts = message.split(',')
    # Clean the parts and remove any empty entries
    cleaned_parts = [part.strip() for part in parts if part.strip()]
    # Count the valid entries
    valid_count = len(cleaned_parts)

    # Define the patterns
    email_pattern = r"^\S+@\S+\.\S+$"
    phone_pattern = r"^\+?\d{7,15}$"  # Ensure the phone number has at least 7 digits
    name_pattern = r"^[A-Za-z ]+$"  # Name should only contain letters and spaces

    # Initialize placeholders
    name = email = phone = None

    # Analyze the cleaned parts
    if valid_count == 3:
        # Assume the order is Name, Email, Phone or Name, Phone, Email
        for part in cleaned_parts:
            if re.match(email_pattern, part):
                email = part
            elif re.match(phone_pattern, part):
                phone = part
            elif re.match(name_pattern, part):
                name = part
        
        return (name, email, phone, valid_count) if (name and email and phone) else (None, None, None, 0)

    elif valid_count == 2:
        # This handles Name and Email, or Name and Phone
        for part in cleaned_parts:
            if re.match(email_pattern, part) and not email:
                email = part
            elif re.match(phone_pattern, part) and not phone:
                phone = part
            elif re.match(name_pattern, part) and not name:
                name = part
        
        return (name, email, phone, valid_count) if ((name and email) or (name and phone)) else (None, None, None, 0)

    elif valid_count == 1:
        # Assume the single part could be a name if it matches the name pattern
        if re.match(name_pattern, cleaned_parts[0]):
            name = cleaned_parts[0]
            return (name, None, None, valid_count)
        else:
            return (None, None, None, 0)

    else:
        return (None, None, None, 0)



def validate_contact_info(name, email, phone):
    # Implement validation logic here
    # Simple checks for non-empty values
    return bool(name) and bool(email) and bool(phone)

def update_prospect_info(wa_id, name, email, phone, assistant_mode):
    # Update the user's contact information in the database
    supabase.table("Prospects").update({
        "name": name,
        "email": email,
        "phone": phone,
    }).eq("user_id", wa_id).eq("assistant_mode", assistant_mode).execute()

def set_prospect_state(wa_id, state, assistant_mode):
    # Update the user's state in 
    supabase.table("Prospects").update({
        "user_state": state
    }).eq("user_id", wa_id).eq("assistant_mode", assistant_mode).execute()



###################################


def log_http_response(response):
    logging.info(f"Status: {response.status_code}")
    logging.info(f"Content-type: {response.headers.get('content-type')}")
    logging.info(f"Body: {response.text}")


def get_text_message_input(recipient, text):
    return json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }
    )

def update_response_message_id(wa_id, message_id):

    user_results = []
    current_user_context = []
    new_index = 1

    user_results = supabase.table('Bot_Accounts').select("tg_context_summary").eq("tg_id", wa_id).execute()
    current_user_context = user_results.data[0]["tg_context_summary"]
    # Check if current_user_context is a string and needs to be converted
    if isinstance(current_user_context, str):
        print("update_response_message_id: current_user_context from DB is STRING, converting to List of Dictionaries!!")
        current_user_context = json.loads(current_user_context)

    if (current_user_context):
        start_index = 1
        count = 0
        for item in current_user_context:
            count += 1
        end_index = count
        print("INSIDE update_response_message Ending Idex (before DIV 2)= ")
        print(end_index)
        end_index = end_index // 2
                
        for i in range(start_index, end_index + 1):  # Plus 1 because range() is exclusive at the end
            for item in current_user_context:
                if item['index'] == end_index:
                    print("YES ! Found Response Message Item by index and now Updating its Message_ID ")
                    print("Matching Ending Idex = ")
                    print(end_index)
                    item['message_id'] = message_id
                
    print("Newly Updated Context with Message ID  = ")
    print(current_user_context)

         
    supabase.table("Bot_Accounts").update({
    "tg_context_summary": current_user_context,
    }).eq("tg_id", wa_id).execute()
    
    print(" RESPONSE ITEM MESSAGE_ID UPDATE in Context Summary  SUCCESS !! \n\n")
    return


def generate_response(response, wa_id, message_id, context_message_id):
    # Return text in uppercase
    # response is User Input,  parse this input appropriately

    #Processing Standard Requests: 
    # Fetch existing context from the Supabase database for the particular user


    try:
        if response.startswith('/prompt_img'):
            print("Processing Image Prompt Generation ...")
            #Processing Image Prompt Generation Request: 
            messages = [
                {"role": "system", "content": "You are an expert image prompt generator that is proficient at digesting vague, generic descriptions given by an user and converting them to specific, well-constructed prompt text that vividly describes the imagery in 70 words or less."},
                {"role": "assistant", "content": "This is Context. "},
                {"role": "user", "content": "This is User's Question"}
            ]
        
            for item in messages:
                if item["role"] == "user":
                    item["content"] = response[len('/prompt_img'):]

        elif response.startswith('/prompt'):
            print("Processing Text Prompt Generation ...")
            #Processing Prompt Generation Request: 
            messages = [
                {"role": "system", "content": "You are an expert prompt builder that is proficient at digesting vague, generic descriptions and converting them to specific, well-constructed prompt paragraphs that explicitly declares the role and tone appropriate for the asks, and effectively communicates user's intentions and goals in order to generates optimal responses in 150 words or less."},
                {"role": "assistant", "content": "This is Context. "},
                {"role": "user", "content": "This is User's Question"}
            ]
        
            for item in messages:
                if item["role"] == "user":
                    item["content"] = response[len('/prompt'):]


        else: 
            #Processing Standard Requests: 
            # Fetch existing context from the Supabase database for the particular user
            user_results = []
            current_user_context = []
            new_index = 1

            user_results = supabase.table('Bot_Accounts').select("tg_context_summary").eq("tg_id", wa_id).execute()
            current_user_context = user_results.data[0]["tg_context_summary"]
            # Check if current_user_context is a string and needs to be converted
            if isinstance(current_user_context, str):
                print("current_user_context from DB is STRING!!!")
                current_user_context = json.loads(current_user_context)

            print("User ID = ")
            print(wa_id)
            print("User Context Summary before update = ")
            if (not current_user_context):
                print("CURRENT_USER_CONTEXT = NONE !!")
            else: 
                print(current_user_context)

            prefixed_prompt = ""
            if (current_user_context):
                start_index = 1
                count = 0
                for item in current_user_context:
                    count += 1
                end_index = count 
                print("current end_index (before DIV 2) of context summary == ")
                print(end_index)
                end_index = end_index // 2
            
                i = 1

                if context_message_id == '':
                    ## Only iterate thru current_user_context list if it's not empty 
                    ## AND If Message is NOT A REPLY-TO Message 
                    print("About to genereate PREFIXED_PROMPT with NO REPLY-TO Context!! ..")
                
                    for i in range(start_index, end_index + 1):  # Plus 1 because range() is exclusive at the end
                        for item in current_user_context:
                            if item["index"] == i:
                                # Print the conversation based on the role
                                if item["role"] == "user":
                                    print(f"User said at Index {i}: {item['content']}")
                                    prefixed_prompt += f"I asked: {item['content']} \n\n"
                                elif item["role"] == "assistant":
                                    print(f"Assistant responded at Index {i}: {item['content']}")
                                    prefixed_prompt += f"You responded: {item['content']} \n\n"
                else:
                    ## This is a REPLY-TO Message, therefore Context is the previous message 
                    ## Use the Context_Message_ID to find and fetch the previous message
                    print("About to genereate PREFIXED_PROMPT with REPLY-TO Context!! ")
                
                    for i in range(start_index, end_index + 1):  # Plus 1 because range() is exclusive at the end
                        for item in current_user_context:
                            if item["message_id"] == context_message_id:
                                print("Found matching Reply-To Message ID!!!")
                                if item["role"] == "user":
                                    prefixed_prompt = f"I said: {item['content']} \n\n"
                                    print("prefixed_prompt == ")
                                    print(prefixed_prompt)
                                if item["role"] == "assistant":
                                    prefixed_prompt = f"You said: {item['content']} \n\n"
                                    print("prefixed_prompt == ")
                                    print(prefixed_prompt)
                            
                    
            # Get the index for the new user prompt
            if (current_user_context):
                new_index = max([item['index'] for item in current_user_context if item['role'] == 'user']) + 1
            else:
                new_index = 1
        

            messages = [
                {"role": "system", "content": "You are an expert prompt interpreter that is adept at understanding imperfect, error-prone user prompts and generate optimal, engaging, yet concise responses followed by relevant questions back to user in 150 total words or less. For questions regarding real-time information,  you would find and provide related website links that can address users' concerns in your response."},
                {"role": "assistant", "content": "This is Context. "},
                {"role": "user", "content": "This is User's Question"}
            ]
        
            for item in messages:
                if item["role"] == "user":
                    ## Prefix user's prompt with existing context 
                    if prefixed_prompt != "" and current_user_context is not None:
                        print("prefixed_prompt contains context,  prepending context to user input ..")
                        print("Given that: \n\n" + prefixed_prompt + "\n\n" + response)
                        item["content"] = "Given that: \n\n" + prefixed_prompt + "\n\n" + response 
                    else:
                        # no previous context 
                        print("no previous context, user input =")
                        print(response)
                        item["content"] = response 
                
            #if item["role"] == "assistant":
                #item["content"] = previous_context
        

        gpt_response = client.chat.completions.create(model="gpt-4o-2024-05-13",
        messages=messages)

        new_response = gpt_response.choices[0].message.content
        print("NEW RESPONSE =")
        print(new_response)

        if not response.startswith('/prompt'):
            if new_index > int(os.getenv("CONVO_WINDOW")):
                print("Convo Window Size =")
                print(os.getenv("CONVO_WINDOW"))
                # Reached Context Window Limit,  RESET context and index
                print(" ** Reached Context Window Limit,  RESET context and index! \n\n ")
                current_user_context = []
                new_index = 1; 

            # Store the newly generated user prompt and response pair into Bot_Accounts table, if user is middle of conversation
            new_context_item = {"index": new_index, "role": "user", "content": response, "message_id" : message_id}
            # Need to update message_id of new response_item after response is posted !!
            new_response_item = {"index": new_index, "role": "assistant", "content": new_response, "message_id" : ''}
            
            print("about to APPEND New User Input and Response !!")
            print(new_context_item)
            print(new_response_item)
            print("NEW INDEX = ")
            print(new_index)
        
            if (not current_user_context):
                current_user_context = [new_context_item, new_response_item]
            else:
                current_user_context.append(new_context_item)
                current_user_context.append(new_response_item)
        
            print("Newly Updated Context = ")
            print(current_user_context)

            #supabase.table('Bot_Accounts').upsert({'tg_context_summary': current_user_context}, 
                                                #returning='minimal').eq('tg_id', wa_id).execute()
        
            supabase.table("Bot_Accounts").update({
            "tg_context_summary": current_user_context,
            }).eq("tg_id", wa_id).execute()
    
            print(" USER CONTEXT UPDATE SUCCESS !! \n\n")

        return new_response
    except Exception as e:
        print(f"Error accessing OpenAI API: {e}")
        response = "Ooops. something went wrong,  please try again"
        return response 
        #bot.reply_to(message, "Sorry, I couldn't process that request. Please try again later.")
    # return response.upper()


def send_message(data):
    headers = {
        "Content-type": "application/json",
        "Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}",
    }

    url = f"https://graph.facebook.com/{current_app.config['VERSION']}/{current_app.config['PHONE_NUMBER_ID']}/messages"

    try:
        response = requests.post(
            url, data=data, headers=headers, timeout=10
        )  # 10 seconds timeout as an example
        response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code
    except requests.Timeout:
        logging.error("Timeout occurred while sending message")
        return jsonify({"status": "error", "message": "Request timed out"}), 408
    except (
        requests.RequestException
    ) as e:  # This will catch any general request exception
        logging.error(f"Request failed due to: {e}")
        return jsonify({"status": "error", "message": "Failed to send message"}), 500
    else:
        # Process the response as normal
        log_http_response(response)
        return response


# Function to browse internet for real-time data 

def fetch_and_display_search_results(user_query):
    api_key = os.getenv("GOOGLE_API_KEY")
    cx = os.getenv("GOOGLE_CX_KEY")
    query = user_query
    url = f"https://www.googleapis.com/customsearch/v1?key={api_key}&cx={cx}&q={query}&num=3"
    
    response = requests.get(url)
    if response.status_code == 200:
        search_results = response.json()
        response_string = "While I am not trained on real-time data, here are top 3 relevant links:\n\n"
        for item in search_results.get('items', []):
            snippet = item.get('snippet')
            formattedUrl = item.get('link')
            response_string += f"{snippet}, {formattedUrl}\n\n"
        return response_string.strip()
    else:
        return "Failed to fetch search results."

# Example usage
test_user_query = "what's the temperature like in New York now?"
print(fetch_and_display_search_results(test_user_query))


# Function to detect if User_query contains commands to draw image

def detect_user_query_for_image_generation(user_query):
    for indicator in indicators_img:
        print(f"current indicator = {indicator}")
        if (indicator.lower() in user_query.lower()):
            print("Detected Image Generation in User Query !!")
            print(f"Matching indicator = {indicator} ")
            return True
    
    return False




def process_text_for_whatsapp(text):
    # Remove brackets
    pattern = r"\【.*?\】"
    # Substitute the pattern with an empty string
    text = re.sub(pattern, "", text).strip()

    # Pattern to find double asterisks including the word(s) in between
    pattern = r"\*\*(.*?)\*\*"

    # Replacement pattern with single asterisks
    replacement = r"*\1*"

    # Substitute occurrences of the pattern with the replacement
    whatsapp_style_text = re.sub(pattern, replacement, text)

    return whatsapp_style_text


def check_user_first_interaction(wa_id):
    # Placeholder for checking the database or storage
    # If user is new, return True and store their wa_id
    # If user exists, return False
    # Implement this based on your storage solution
    pass


def download_image(image_url):
    """Download an image and return it as a bytes object."""
    response = requests.get(image_url)
    if response.status_code == 200:
        return BytesIO(response.content)
    else:
        print("Failed to download image")
        return None

def upload_image_to_whatsapp(image_url):
    print("ABOUT TO UPLOAD IMAGE...")
    print("ACCESS_TOKEN =")
    print("Image URL = ")
    print(image_url)
    print(current_app.config['ACCESS_TOKEN'])
    
    headers = {
        "Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}"
    }

    phone_number_id = os.getenv("PHONE_NUMBER_ID")
    print("Phone number ID: ")
    print(phone_number_id)
    whatsapp_media_upload_url = f"https://graph.facebook.com/v19.0/{phone_number_id}/media"

    # Download the image first
    image_bytes = download_image(image_url)
    if image_bytes is None:
        return None

    # Prepare the files and data for the POST request to upload the image
    files = {
        'file': ('image.png', image_bytes, 'image/png')
    }
    data = {
        "messaging_product": "whatsapp"
    }

    # Make the POST request to upload the image as binary data
    upload_response = requests.post(whatsapp_media_upload_url, headers=headers, files=files, data=data)
    
    print("UPLOAD IMAGE COMPLETED!")

    if upload_response.status_code == 200:
        upload_data = upload_response.json()
        media_id = upload_data.get("id")  # Assuming the response contains an ID field
        return media_id
    else:
        # Handle errors or unsuccessful upload attempts
        print(f"Failed to upload image to WhatsApp: {upload_response.text}")
        return None



def send_image_to_whatsapp(wa_id, image_url):
    # Step 1: Upload the image to WhatsApp to get a media ID
    # This step depends on the specifics of the WhatsApp API you're using
    media_id = upload_image_to_whatsapp(image_url)  # You need to implement this based on your API

    # Step 2: Send the media message with the media ID
    headers = {
        "Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}",
        "Content-Type": "application/json",
    }
    data = json.dumps({
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": wa_id,
        "type": "image",
        "image": {"id": media_id},
    })
    url = f"https://graph.facebook.com/{current_app.config['VERSION']}/{current_app.config['PHONE_NUMBER_ID']}/messages"
    response = requests.post(url, headers=headers, data=data)
    return response


### HELPER FUNCTIONS FOR FILE UPLOAD ###


#def respond_with_upload_instructions(wa_id):
    #instruction_message = ("Please upload your document by selecting the 'Attach' icon (📎) and choosing your file. "
                           #"Once uploaded, we will process it and you can start asking questions about its content.")
   # send_message(wa_id, instruction_message)


def fetch_media_url(media_id):
    url = f"https://graph.facebook.com/v19.0/{media_id}/"
    headers = {
        "Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}"
    }

    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        # Assuming the response contains a direct URL to the media file in the JSON response
        media_url = response.json().get("url", None)
        return media_url
    else:
        # Handle errors or unsuccessful response
        print(f"Failed to fetch media URL: {response.text}")
        return None

def download_file(document_url):
    # Logic to download the file from the document URL
    # You might need to set proper headers with your request
    # Depending on the API you're using to interface with WhatsApp
    

    # Fixed Document_URL to a Supabase Storage 
    #document_url = 'https://files.wewinmeta.com/storage/v1/object/public/docs/PlayPass-Policy_en.pdf'
    
    # Prepare the headers with the access token
    headers = {
        "Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}"
    }

    #response = requests.get(document_url, stream=True)
    # Make the request with the headers
    response = requests.get(document_url, headers=headers, stream=True)

    temp_file = None

    # Check if the request was successful
    if response.status_code == 200:
        # Create a temporary file
        print("Download File Success !!")
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        # Write the downloaded content to the file
        print("temp_file created !! ")
        print("tmp_file name = ")
        print(temp_file.name)
        for chunk in response.iter_content(chunk_size=128):
            temp_file.write(chunk)
        # Close the file
        temp_file.close()
        # Return the path to the temporary file
        print("Temp_file Name = ")
        print(temp_file.name)
        return temp_file.name
                      
    else:
        print("Failed to download Media! .")
        return None
    return file_path

# --------------------------------------------------------------
#  File Helper Functions 
# --------------------------------------------------------------


def compute_file_hash(file_path):
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


def upload_file(path):
    # Upload a file with an "assistants" purpose
    file = client.files.create(file=open(path, "rb"), purpose="assistants")
    return file

def process_uploaded_file(file_path, wa_id):
    # Compute file content hash
    file_hash = compute_file_hash(file_path)
    if (file_hash):
        assistant_id = retrieve_assistant_id_by_file_hash(file_hash)
        print("Retrieved Asisstant ID = ")
        print(assistant_id)
    
    if not (assistant_id):
        # FILE IS NEW, CREATE NEW ASSISTANT 
        file = upload_file(file_path)
        print("FILE CREATED SUCCESSFULLY!!")
        store_file_assistant_mapping(file_hash, assistant_id, wa_id)
        print("File HASH Saved to Assistants table !!")
        # Create an Assistant for user {wa_id}, then Sends a Message to User with the newly created Assistant ID
        create_or_update_assistant(file.id, file_hash, wa_id)
    else:
        # Assistant ID already exists
        # APPEND Assistant ID to assistant_instruction_message  SO WE Know which Assistant To Run !! 
        print("In Process_uploaded_file:  Existing Assistant ID found !!")
        assistant_msg = f"{assistant_id} - {assistant_instruction_message}"
    
        # Prompt user to start asking questions
        #data = get_text_message_input(wa_id, assistant_instruction_message)
        data = get_text_message_input(wa_id, f"Hi there, user {wa_id}, This assistant already esists.  Please prefix your queries with ' {assistant_id} - ' \n\n")
        send_message(data)




###################################################################

### HELPER FUNCTIONS FOR STORING ASSISTANT_ID and FILE_HASH #######

###################################################################




def store_file_assistant_mapping(file_hash, assistant_id, creator_id):
    """
    Stores the mapping of a file hash to its corresponding assistant ID and creator ID.
    """
    #with shelve.open('file_assistant_mappings_db', writeback=True) as db:
        # Each file hash maps to a dictionary containing assistant ID and creator ID
       # db[file_hash] = {'assistant_id': assistant_id, 'creator_id': creator_id}
    supabase.table("Assistants").insert({
            "creator_id": creator_id,
            "file_hash": file_hash,
            "assistant_id": assistant_id
        }).execute()
    print("File Hash - Assistant ID Insert Success!!")

def retrieve_assistant_id_by_file_hash(file_hash):
    """
    Retrieves an assistant ID by file hash.
    """
    #with shelve.open('file_assistant_mappings_db') as db:
        #mapping = db.get(file_hash, None)
        #if mapping is not None:
            #return mapping['assistant_id']
        # else:
            #return None
    
    assistant_exists = supabase.table("Assistants").select("*").eq("file_hash", file_hash).execute()

    if not assistant_exists.data:
        print("No Assistant exists by given File Hash !!")
        return None
    else:
        # Assistant Exists!
        print("Assistant found by given File Hash !! ")
        print(assistant_exists.data[0]["assistant_id"])
        return assistant_exists.data[0]["assistant_id"]
      
def retrieve_assistant_id_by_assistant_id(assistant_id):

    assistant_exists = supabase.table("Assistants").select("*").eq("assistant_id", assistant_id).execute()

    if not assistant_exists.data:
        print("No Assistant exists by given Assistant ID  !!")
        return None
    else:
        # Assistant Exists!
        print(f"Assistant found by given Assistant_ID:" )
        print(assistant_exists.data[0]["assistant_id"])
        return assistant_exists.data[0]["assistant_id"]



def create_or_update_assistant(file_id, file_hash, wa_id):
    # This function now needs to handle both creating a new assistant
    # and potentially updating an existing one

    #assistant = client.beta.assistants.create(
        #name=f"WhatsApp Session Assistant for {wa_id}",
        #model="gpt-4-0125-preview",
        #file_ids=[file_id],
    #)

    assistant = client.beta.assistants.create(
        name= f"Custom Knowledge Assistant for {wa_id}",
        instructions="You're a helpful WhatsApp assistant that can scan uploaded knolwedge files and provide useful responses based on the custom knowledge.  Be friendly and funny.",
        tools=[{"type": "retrieval"}],
        model="gpt-4o-2024-05-13",
        file_ids=[file_id],
    )
    # Store the assistant ID for future reference, possibly keyed by wa_id
    #store_assistant_id(wa_id, assistant.id)

    # APPEND Assistant ID to assistant_instruction_message  SO WE Know which Assistant To Run !! 

    assistant_msg = f"{assistant.id} - {assistant_instruction_message}"


    supabase.table("Assistants").update({
        "assistant_id": assistant.id
        }).eq("file_hash", file_hash).execute()
    
    # Prompt user to start asking questions
    #data = get_text_message_input(wa_id, assistant_instruction_message)
    data = get_text_message_input(wa_id, f"Hi there, user {wa_id}, you have just created a Custom Assistant ID = {assistant.id}.  Please preceed your queries with this ID \n\n")
    send_message(data)







# --------------------------------------------------------------
# Thread management
# --------------------------------------------------------------
def check_if_thread_exists(wa_id, assistant_id):
    #with shelve.open("threads_db") as threads_shelf:
        #return threads_shelf.get(wa_id, None)
    # Fetch the LATEST (Freshest) thread 
    thread_exists = supabase.table("Threads").select("*").eq("user_id", wa_id).eq("assistant_id", assistant_id).order("created_at", desc=True).execute()
    if thread_exists.data:
        print(f"Found thread_id {thread_exists.data[0]['thread_id']} ")
        return thread_exists.data[0]['thread_id']
    else:
        return None

def store_thread(wa_id, thread_id, assistant_id):
    #with shelve.open("threads_db", writeback=True) as threads_shelf:
        #threads_shelf[wa_id] = thread_id
    supabase.table("Threads").insert({
        "user_id": wa_id,
        "thread_id": thread_id,
        "assistant_id": assistant_id
    }).execute()
    print(f"Thread ID {thread_id} for Assistant ID {assistant_id} for user {wa_id} Insert Success!!")
    return

def is_any_run_active(thread_id):
    # Retrieve all runs for the thread
    runs = client.beta.threads.runs.list(thread_id=thread_id).data
    run_count = 0 
    # Iterate through runs to find any that are active
    for run in runs:
        run_count += 1
        print(f"run count : {run_count}")
        if run.status == "active" or run.status == "in_progress" or run.status == "timed_out":
            print(f"Active run found: {run.id}, status: {run.status}")
            #return run.id  # Return the ID of the active run
            # instead of re-using the Active / In-Progress run,  create a new one
            return "ACTIVE_RUN_FOUND"
        else:
            print(f"run {run.id} is marked {run.status} !!")
    print("No active runs found.")
    return None  # Return None if no active runs are found



# --------------------------------------------------------------
# Assistant Generate Response 
# --------------------------------------------------------------

def assistant_generate_response(message_body, wa_id, name, assistant_id):

    print(" **** Inside Assistant_Generate_Response *****")

    # If Assistant_id No longer exists,  Return an graceful message to User 
    if retrieve_assistant_id_by_assistant_id(assistant_id) is None:
        return f"Ooops!  Assistant ID {assistant_id} has already been deprecated.  Please double-check and make sure you have a valid Assistant ID !!"

    
    # Check if there is already a thread_id for the wa_id
    thread_id = check_if_thread_exists(wa_id, assistant_id)
    print(f"Found NEWEST thread ID for user {wa_id} = {thread_id}")
    
    runs = None
    run_count = 0

    if thread_id is not None: 
        runs = client.beta.threads.runs.list(thread_id)
        run_count = len(runs.data)
        print(f"thread {thread_id} now has {run_count} runs !!")


    # If a thread doesn't exist, create one and store it
    if thread_id is None or run_count > 10:
        print(f"Creating new thread for {name} with wa_id {wa_id}")
        thread = client.beta.threads.create()
        store_thread(wa_id, thread.id, assistant_id)
        thread_id = thread.id

    # Otherwise, retrieve the existing thread
    else:
        print("thread id exists ! ")
        print(thread_id)
        print(f"Retrieving existing thread for {name} with wa_id {wa_id}")
        thread = client.beta.threads.retrieve(thread_id)
        if is_any_run_active(thread_id) == "ACTIVE_RUN_FOUND":
            print(f"Gotcha! there is an active Run {is_any_run_active(thread.id)} for thread {thread.id})")
            if (thread.id != thread_id):
                print("wait a minute thread.id = {thread.id} and thread_id = {threa_id} ")
            #in this case,  please respond to user that waiting is required 
            return f"Assistant is currently busy with an active run.  Please wait 30 seconds and re-submit your query. Sorry for the inconvenience !!"

    # Add message to thread
    message = client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=message_body,
    )

    # Run the assistant and get the new message
    new_message = run_assistant(thread, assistant_id)
    print(f"To {name}:", new_message)
    return new_message


# ------------------------------------------------------------------------------------
# Run the Assistant by the appropriate assistantID (assistant_id) for the User (wa_id)
# ------------------------------------------------------------------------------------
def run_assistant(thread, assistant_id):
    # Retrieve the Assistant
    print("Inside run_assistant: Retrieving assistant, ID = ")
    print(assistant_id)
    #assistant = client.beta.assistants.retrieve("asst_7Wx2nQwoPWSf710jrdWTDlfE")
    try: 
        assistant = client.beta.assistants.retrieve(assistant_id)
    
    except Exception as e:
        print(f"Assistant with ID {assistant_id} does not exist!!")
        # Handle the non-existence of the Assistant ID appropriately here
        # For example, you could remove the thread associated with this Assistant ID
        return f"SORRY! the Assistant you're trying to access {assistant_id} no longer exists. Please try again with a valid Assistant ID."


    #Before creating a new run check if an existing run is available
    run = None

    if is_any_run_active(thread.id) == "ACTIVE_RUN_FOUND":
        # Retrieve the status of the latest run for the thread
        # Pick up the active run and proceed 
        #run = client.beta.threads.runs.list(thread_id=thread.id, limit=1).data[0]
        print("Inside Run_Assistant : Found Active Run, Create new Run anyways!!")
        # 3-20-2024
        # Still Found an Active Run,  ignore and still Create a new Run anyways!
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant.id,
        )
        print(f"Found an active or in-progress Run {run.id} for Thread {thread.id} ")
  
    else: 
        # Create a new Run for the assistant
        print(f"About to create a new Run for Thread {thread.id} ")
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant.id,
        )

    print(f"assistant ID = {assistant.id}")
    print(f"run ID = {run.id}")

    run_count = 0 

    # Wait for completion
    while run.status != "completed":
        # Be nice to the API
        time.sleep(0.8)
        run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        print(f"run ID = {run.id}")
        run_count += 1 
        if (run_count > 50):
            print(f" Thread Running over 30 iterations !! ! run ID = {run.id},  thread ID = {thread.id}, assistant ID = {assistant.id}")
            run.status = "timed_out"
            return f" Backend is busy,  taking a short break for thread ID = {thread.id}, assistant ID = {assistant.id}"

    print(f"YES! Run {run.id} has been completed for Thread {thread.id}, Don't Repeat!!")


    # Retrieve the Messages
    messages = client.beta.threads.messages.list(thread_id=thread.id)
    new_message = messages.data[0].content[0].text.value
    print(f"Generated message: {new_message}")
    return new_message


def process_whatsapp_message(body):
    wa_id = body["entry"][0]["changes"][0]["value"]["contacts"][0]["wa_id"]
    name = body["entry"][0]["changes"][0]["value"]["contacts"][0]["profile"]["name"]
    message = body["entry"][0]["changes"][0]["value"]["messages"][0]
    message_body = ''
    if 'text' in message:
        message_body = message["text"]["body"]
    print(" **** USER MESSAGE reads **** : \n\n ")
    print(message)
    message_id = message['id']
    context_message_id = ''
    print("Message ID = ")
    print(message_id)

    #5/6/2024
    current_user_mode = 0; 
    current_user_mode = get_current_user_mode(wa_id)
    print(f" current_user_mode = {current_user_mode}")

    # Define the pattern for an assistant ID
    pattern = r"^asst_[A-Za-z0-9]+"

    # Check if message starts with an 8-digit number, meaning an instruction for an Assistant !! 

    # 3-12-2024 Check if Message is a Reply-To

    if 'context' in message and 'from' in message['context']:
        # Accessing ID of the message being replied to
        message_owner_id = message['context']['from']
        print("YES! It is a Reply-To and Message Sender ID = ")
        print(message_owner_id)
        print("Context Message ID = ")
        context_message_id = message['context']['id']
        print(context_message_id)
        #print(message['context']['body'])
    
    else:
        print("No Parent Message ID for this message! ")
    

    # Generate a unique referral code using the user's ID
    referral_code = hashlib.sha256(str(wa_id).encode('utf-8')).hexdigest()[:10]
    # Format the current UTC time in ISO 8601 format, ensuring it's a string compatible with Supabase
    current_time = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    # Check if the user already exists in the database
    print("CHECKING IF USER EXISTS")
    user_exists = supabase.table("Bot_Accounts").select("*").eq("tg_id", wa_id).execute()
    user_locale = get_current_user_locale(wa_id)
    hey_msg = f"Hey There {name}, Welcome to Promptlys on WhatsApp!"

    # If the user does not exist, insert the new user
    if not user_exists.data:
        user_locale = get_country_from_phone_number(wa_id)
        supabase.table("Bot_Accounts").insert({
            "tg_id": wa_id,
            "tg_handle": name,
            "tg_refcode": referral_code, 
            "tg_type": "WhatsApp",
            "tg_locale": user_locale,
            "modified_at" : current_time
        }).execute()

        if user_locale == '+86' or user_locale == '+852' :
            hey_msg = f"你好，{name}，欢迎使用 Promptlys WhatsApp!"

        if user_locale == '+886':
            hey_msg = f"你好，{name}，歡迎使用 Promptlys WhatsApp!!"

        data = get_text_message_input(wa_id, hey_msg)
        send_message(data)

        if user_locale == '+86' or user_locale == '+852' :
            data = get_text_message_input(wa_id, guide_response_cn)
        else:
            data = get_text_message_input(wa_id, guide_response)
    
        send_message(data)
        print("NEW WHATSAPP USER INSERTION SUCCESS !!")
    else:
        # Optionally, update the user's handle if it has changed
        supabase.table("Bot_Accounts").update({
            "tg_handle": name,
            "tg_refcode": referral_code,  # Update this if you want to allow referral code updates
            "modified_at" : current_time    
        }).eq("tg_id", wa_id).execute()
        print("WHATAPP BOT USER UPDATE SUCCESS !!")

    # Check if it's a file upload action (for Assistant) #########
     # Check if the message has a 'text' field before accessing it
    if message is not None and not 'text' in message:
        print("Received a non-text message. Processing Upload.")
        if message['type'] == 'document':
            print("About to process FILE UPLOAD !! message looks like: ")
            print(message)
            document_info = message['document']
            document_id = message['document']['id']
            document_url = fetch_media_url(document_id)
            document_name = document_info.get('filename', '')
            
            print("document id = ")
            print(document_id)
            print("document URL = ")
            print(document_url)
            print("document name = ")
            print(document_name)

            file_path = download_file(document_url)
            if (file_path):
                print("New Document URL FILEPATH = ")
                print(file_path)
                ## Take the file, Build a Custom Assistant for user {wa_id}, then Notify 
                ## the user of the newly created Assistant and ask user to proceed with questions for the assistant 
    
                process_uploaded_file(file_path, wa_id)
                return
            else:
                print("File Upload Failed")

    # Check if this is the first interaction
    #if check_user_first_interaction(wa_id):
        #greeting_message = "Hello, welcome to Promptlys on WhatsApp! How can I assist you today?"  # Your predefined greeting message
        #data = get_text_message_input(wa_id, greeting_message)
        #send_message(data)
        #return  # Stop processing further to ensure only the greeting is sent on first interaction

    # Check for commands
    if message_body.startswith('/about'):
        data = get_text_message_input(wa_id, about_response)
        send_message(data)
        return
    elif message_body.startswith('/guide') or message_body.startswith('/help') :
        data = get_text_message_input(wa_id, guide_response)
        send_message(data)
        return
    elif message_body.startswith('/image') or detect_user_query_for_image_generation(message_body):
        user_prompt = message_body
        if message_body.startswith('/image'):
            user_prompt = message_body[len('/image'):].strip()  # Remove the command and leading spaces
        else:
            print("Detected Image Generation in User Prompt! ")
  
        data = get_text_message_input(wa_id, "🤖🎨 ...")
        print("HANDLING IMAGE PROMPTS NOW.. ")
        send_message(data)
        user_results = []
        user_results = supabase.table('Bot_Accounts').select("*").eq("tg_id", wa_id).execute()
        print("query response done")
        print(user_results)
        #if user_results.error:
        #print("query response ERROR")
        #raise Exception("Error fetching user's image limit")

        img_count = user_results.data[0]["img_count"]
        img_limit = user_results.data[0]["img_limit"]

        print("Imgage Limit = ")
        print(img_limit)
        print("Image Count =")
        print(img_count)

        if img_count >= img_limit:
            limit_exceeded_msg = "Sorry, you have reached the free image limit of 8, please upgrade your account by paying $10 for 25 images \n\n "
            paypal_msg = "Please click the following link to make payment:"

            data = get_text_message_input(wa_id, limit_exceeded_msg)
            send_message(data)
    
                
            # Send the PayPal payment link
            paypal_link = "https://www.paypal.com/ncp/payment/BZCSB9SKG8TAY"
            data = get_text_message_input(wa_id, f"{paypal_msg} {paypal_link}")
            send_message(data)
            return


        try:
            image_response = client.images.generate(
                model="dall-e-3",
                prompt=user_prompt, 
                size="1024x1024",
                quality="standard",
                n=1,
            )
            # Handle sending the generated image back as a response
            # This step depends on how you can send images via your setup. You might need to upload the image
            # to a publicly accessible URL and then send that URL in a message to the user.
            image_url = image_response.data[0].url  # Assuming this is how you get the URL; adjust based on actual response structure
            
            print("image_url : ")
            print(image_url)

            supabase.table("Bot_Accounts").update({
            "img_count": img_count + 1,
            }).eq("tg_id", wa_id).execute()
           
            # Now, instead of sending the URL as text, use the send_image_to_whatsapp function as an IN-LINE image 
            send_image_to_whatsapp(wa_id, image_url)
            return

            #data = get_text_message_input(wa_id, f"Here's the image: {image_url}")
            #send_message(data)
        except Exception as e:
            error_message = f"Failed to generate image: {str(e)}"
            data = get_text_message_input(wa_id, error_message)
            send_message(data)
            return

    #Command to Initiate Custom Assistant 
    elif message_body.startswith('/assistant'):
        data = get_text_message_input(wa_id, instruction_message)
        send_message(data)
        return
    
    #Command to to interact with a specific assistant by ID
    elif re.match(pattern, message_body):
        print("YES, we got Assistant ID and the user instructions!")
        assistant_id = re.match(pattern, message_body).group(0)
        print(f"Extracted Assistant ID : {assistant_id}")

        data = get_text_message_input(wa_id, "🤖💬...")
        send_message(data)

        _, prompt_text = message_body.split(' - ', 1)  # Split only at the first occurrence of " - "
        print(f"Extracted prompt text: {prompt_text}")

        # Now generate response with the specific assistant 
        #assistant_generate_response(prompt_text, wa_id, name, assistant_id)
        assistant_message = assistant_generate_response(prompt_text, wa_id, name, assistant_id)
        data = get_text_message_input(wa_id, assistant_message)
        send_message(data)
        return 

    #5/6/2024 - EXITING Custom Mode 

    elif message_body.startswith('/exit') or message_body.startswith('/Exit') :
        exit_msg = "Hi, exiting from: "
        if (current_user_mode == 5):
            exit_msg += "AmandaGPT"
        if (current_user_mode == 7):
            exit_msg += "Dust To Gold"
        if (current_user_mode == 8):
            exit_msg += "IRIS_AI"

        clear_user_mode(wa_id)
        print(f"CLEARED Custom User Mode for user {wa_id} !")
        data = get_text_message_input(wa_id, exit_msg)
        send_message(data)
    
    #4/4/2024 - Accountant GPT  (Iris)
    #Command to to interact with a Accountant GPT assistant 
    elif message_body.startswith('/Iris') or current_user_mode == 8:
        assistant_id = "asst_lH5TsPVGImGLbg3aWXbqgTu1"
        command, *args = message_body.split(maxsplit=1)
        prompt_text = args[0].strip() if args and command.lower() == '/iris' else message_body
        print(f"IRIS extracted prompt text: {prompt_text}")


        # Set the user's mode based on command
        if (current_user_mode != 8) : 
            set_user_mode(wa_id, 8)  
            print(f"Set Iris Mode (8) for user {wa_id} !")
            
            data = get_text_message_input(wa_id, f"You are now speaking with IRIS. Type '/exit' to return to Normal mode.")
            send_message(data)

        data = get_text_message_input(wa_id, "🤖💬...")
        send_message(data)

        # Check if current prospect is expected to provide contact info
        prospect_info = get_prospect_info(wa_id, 8)  # This function fetches Prospect user info including current state based on assitant mode
        # Check If the prospect is in 'awaiting_contact_info' state for all users 
        if (prospect_info and prospect_info['user_state'] == 'awaiting_contact_info'):
            # Attempt to parse contact information
            contact_name, email, phone, valid_count = parse_contact_info(message_body)
            update_prospect_info(wa_id, contact_name, email, phone, 8)
            if (valid_count >= 2):
                set_prospect_state(wa_id, 'prospect_info_added', 8)

            if (valid_count >= 1):
                data = get_text_message_input(wa_id, "Thank you for submtting your information.  Amanda will get in touch with you, meanwhile our virtual assistant will continue servicing you further!")
                send_message(data)
                return 

            # Check for seller keywords
        if any(keyword in prompt_text.lower() for keyword in iris_prospects_keywords ):
            # Set user as an Iris Prospect and create record in Prospects table 
            print(f"IRIS: detected a standard prospect !")
            set_prospect_role(wa_id, 0, 8) 
        
            if prospect_info['user_state'] == 'awaiting_contact_info':
                # Ask for contact information
                assistant_message = "Hi, It sounds like you are interested in professional tax services!   Please share your name, email, phone number (ex. John Smith, jsmith@gmail.com, 3233932820) and a consultant will get in touch with you!"
            else:
                assistant_message = "Hi, looks like we have your contact information. IRIS's team will get in touch with you for a free consulting session!"


        else: 
        
            # Now generate response with the specific assistant 
            #assistant_generate_response(prompt_text, wa_id, name, assistant_id)
            #4-15-2024 : Append "150 words or less" to each request 
            print(f"IRIS standard inquiry:  extracted prompt text: {prompt_text}")
            prompt_text += "in 100 words or less"
            assistant_message = assistant_generate_response(prompt_text, wa_id, name, assistant_id)
        

        data = get_text_message_input(wa_id, assistant_message)
        send_message(data)
        return 
    
    #Command to to interact with a AmandaGPT assistant 
    elif message_body.startswith('/AmandaGPT') or current_user_mode == 5:
        assistant_message = "This is your Assisant AmandaGPT"
        assistant_id = "asst_R8l5sv4uAlSwMs9JZWZyGext"
        command, *args = message_body.split(maxsplit=1)
        prompt_text = args[0].strip() if args and command.lower() == '/amandagpt' else message_body
        print(f"AmandaGPT extracted prompt text: {prompt_text}")

        # Set the user's mode 
        if (current_user_mode != 5) : 
            set_user_mode(wa_id, 5)  
            print(f"Set AmandaGPT Mode (5) for user {wa_id} !")
            
            data = get_text_message_input(wa_id, f"You are now speaking with AmandaGPT. Type '/exit' to return to Normal mode.")
            send_message(data)

        data = get_text_message_input(wa_id, "🤖💬...")
        send_message(data)

        # Check if current prospect is expected to provide contact info
        prospect_info = get_prospect_info(wa_id, 5)  # This function fetches Prospect user info including current state based on AmandaGPT assistant mode

         # If the prospect is in 'awaiting_contact_info' state
        if (prospect_info and prospect_info['user_state'] == 'awaiting_contact_info'):
            # Attempt to parse contact information
            contact_name, email, phone, valid_count = parse_contact_info(message_body)
            update_prospect_info(wa_id, contact_name, email, phone, 5)
            if (valid_count >= 2):
                set_prospect_state(wa_id, 'prospect_info_added', 5)

            if (valid_count >= 1):
                data = get_text_message_input(wa_id, "Thank you for submtting your information.  Amanda will get in touch with you, meanwhile our virtual assistant can continue to assist you!")
                send_message(data)
                return 

            # Check for seller keywords
        if any(keyword in prompt_text.lower() for keyword in seller_keywords):
            # Set user as a SELLER (role = 1) and create record in Prospects table 
            set_prospect_role(wa_id, 1, 5)
        
            if prospect_info['user_state'] == 'awaiting_contact_info':
                # Ask for contact information
                assistant_message = "Hi, It sounds like you are interested in selling!  Please share your name, email, phone number (ex. John Smith, jsmith@gmail.com, 3233932820) and a live agent will get in touch with you!"
            else:
                assistant_message = "Hi, looks like we have your contact information. Amanda will get in touch with you for initial engagement!"

        elif prompt_text.lower().startswith("find comps:") or prompt_text.lower().startswith("generate comps:"):
            address = prompt_text[len("Find comps: "):].strip()
            print(f"Looking up comps for address: {address}")
            address = address.strip().replace(" ", "+")  # Replace spaces with '+' for URL encoding
            print(f"Encoded address: {address}")

            cma_api_key = os.getenv("CMA_API_KEY")
            url = f"https://cloudcma.com/cmas/widget?api_key={cma_api_key}&name={wa_id}&address={address}"

            response = requests.get(url)
            if response.status_code == 200:
                cma_data = response.json()
                cma_guid = cma_data['cma']['guid']
                cma_link = f"https://cloudcma.com/live/{cma_guid}"
                assistant_message = f"Hi, {name}, your CMA report is ready at the link below: {cma_link}"
            else:
                assistant_message = "Sorry, I couldn't fetch the CMA report at this time."
        else:
            # Now generate response with the specific assistant 
            #assistant_generate_response(prompt_text, wa_id, name, assistant_id)
            #4-15-2024 : Append "150 words or less" to each request 
            prompt_text += "in 150 words or less"
            assistant_message = assistant_generate_response(prompt_text, wa_id, name, assistant_id)
        
        data = get_text_message_input(wa_id, assistant_message)
        send_message(data)
        return 
    
    #Command to to interact with a D2G assistant 
    elif message_body.startswith('/D2G') or current_user_mode == 7:
        assistant_id = "asst_QxHSbIhZh4sLKjN6YnCYg7tQ"
        command, *args = message_body.split(maxsplit=1)
        prompt_text = args[0].strip() if args and command.lower() == '/d2g' else message_body
        print(f"D2G extracted prompt text: {prompt_text}")

        # Set the user's mode 
        if (current_user_mode != 7) : 
            set_user_mode(wa_id, 7)  
            print(f"Set D2G Mode (7) for user {wa_id} !")
            
            data = get_text_message_input(wa_id, f"You are now speaking to Narrator of Dust To Gold. Type '/exit' to return to Normal mode.")
            send_message(data)


        data = get_text_message_input(wa_id, "🤖💬...")
        send_message(data)

        # Now generate response with the specific assistant 
        #assistant_generate_response(prompt_text, wa_id, name, assistant_id)
        #4-15-2024 : Append "150 words or less" to each request 
        prompt_text += "in 150 words or less"
        assistant_message = assistant_generate_response(prompt_text, wa_id, name, assistant_id)
        data = get_text_message_input(wa_id, assistant_message)
        send_message(data)
        return 


    else :
        # Handle regular prompts 
        # if prompts exceed 100 words,  show a message asking user to wait.. 
        if len(message_body) > 500:
            data = get_text_message_input(wa_id, "Hi, Please wait while processing a large prompt  ..")
            print("HANDLING LARGE PROMPTS NOW.. ")
            send_message(data)
        if len(message_body) > 20:
            data = get_text_message_input(wa_id, "🤖💬 ...")
            send_message(data)
        
        response = generate_response(message_body, wa_id, message_id, context_message_id)
        print("LATEST RESPONSE = ")
        print(response)

        #testing 
        #Check if response contains any indicator 
        indicator = "start"

        for indicator in indicators:
            print(f"current indicator = {indicator}")
            if (indicator.lower() in response.lower()):
                print("Yes Caught a match in Real Response")
                print(f"Matching indicator = {indicator} ")
                response = fetch_and_display_search_results(message_body)
                



        data = get_text_message_input(wa_id, response)
        new_response = send_message(data)
        print("New_Response ==")
        print(new_response)
        try: 
            if new_response.status_code == 200:
                print("response code = 200!! ")
                new_response_data = new_response.json()
                sent_message_id = new_response_data['messages'][0]['id']
                print("New Response Message ID = ")
                print(sent_message_id)
                print("Updating the response item message_id in DB Context Summary  now..")
                update_response_message_id(wa_id, sent_message_id)
                return
        except Exception as e:
            error_message = f"New Response failed to produce status_code = 200 !! Some error!"
            print(f"New Response failed to produce status_code = 200 !! Some error!")
            return
  



    ##  TO DO:  implement custom function here
    # response = generate_response(message_body)

    #data = get_text_message_input(current_app.config["RECIPIENT_WAID"], response)
    #send_message(data)


def is_valid_whatsapp_message(body):
    """
    Check if the incoming webhook event has a valid WhatsApp message structure.
    """
    return (
        body.get("object")
        and body.get("entry")
        and body["entry"][0].get("changes")
        and body["entry"][0]["changes"][0].get("value")
        and body["entry"][0]["changes"][0]["value"].get("messages")
        and body["entry"][0]["changes"][0]["value"]["messages"][0]
    )
