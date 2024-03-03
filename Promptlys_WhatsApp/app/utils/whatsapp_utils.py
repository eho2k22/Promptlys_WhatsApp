import logging
from flask import current_app, jsonify
import json
import requests
import hashlib

from io import BytesIO
import os

# from app.services.openai_service import generate_response
import re

from dotenv import load_dotenv
import os

from openai import OpenAI
from supabase import create_client, Client


load_dotenv('example.env')

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

# Predefined responses
about_response = (
    "Promptlys is a Professional Prompt network whose mission is to optimize generative AI communications via effective prompting.\n\n"
    "On Promptlys, you can input a general topic and the prompt generator will produce a list of prompts that convert your intentions into relevant, well-constructed prompts.\n\n"
    "On Promptlys, you can search a library of publicly shared prompts by keyword or category, connect with prompt experts, and subscribe to premium prompt experts channels.\n\n"
    "Promptlys is built on a freemium model. With a $100/year subscription you can access premium and customized prompts that can save thousands per month, for hiring a copywriter, graphic designer, or a programmer.\n\n"
    "Please visit us at our website: https://demo.promptlys.ai"
)

guide_response = (
    "1. Type  '/about' to browse what Promptlys is about and visit its website for more info!! \n\n"
    "2. Prefix '/prompt' to your prompt description and the Bot will revise and enhance your prompt !\n\n"
    "3. Prefix /image to a prompt description then the Bot will generate an image based on your prompt description. \n\n"
    "4. Type away in chat and Promptlys Bot will engage and respond to your questions!! \n\n"
    "5. Type '/guide' to replay Promptlys Bot instructions"
)



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


def generate_response(response):
    # Return text in uppercase
    # response is User Input,  parse this input appropriately

    try:
        if response.startswith('/prompt'):
            #Processing Prompt Generation Request: 
            messages = [
                {"role": "system", "content": "You are an expert prompt builder that is proficient at digesting vague, generic descriptions and converting them to specific, well-constructed prompt examples that explicitly declares the appropriate role and tone, and effectively communicates user's intentions and goals. Please generate each response in 200 words or less"},
                {"role": "assistant", "content": "This is Context. "},
                {"role": "user", "content": "This is User's Question"}
            ]
        
            for item in messages:
                if item["role"] == "user":
                    item["content"] = response[len('/prompt'):]


        else: 
            #Processing Standard Requests: 
            messages = [
                {"role": "system", "content": "You are an expert prompt interpreter that is adept at understanding imperfect, error-prone user prompts and generate with the most optimal and engaging responses in 250 total words or less."},
                {"role": "assistant", "content": "This is Context. "},
                {"role": "user", "content": "This is User's Question"}
            ]
        
            for item in messages:
                if item["role"] == "user":
                    item["content"] = response 
                
            #if item["role"] == "assistant":
                #item["content"] = previous_context
        

        gpt_response = client.chat.completions.create(model="gpt-4-0125-preview",
        messages=messages)
        
        response = gpt_response.choices[0].message.content

        return response
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




def process_whatsapp_message(body):
    wa_id = body["entry"][0]["changes"][0]["value"]["contacts"][0]["wa_id"]
    name = body["entry"][0]["changes"][0]["value"]["contacts"][0]["profile"]["name"]


    message = body["entry"][0]["changes"][0]["value"]["messages"][0]
    message_body = message["text"]["body"]

  

    # Generate a unique referral code using the user's ID
    referral_code = hashlib.sha256(str(wa_id).encode('utf-8')).hexdigest()[:10]
    # Check if the user already exists in the database
    print("CHECKING IF USER EXISTS")
    user_exists = supabase.table("Bot_Accounts").select("*").eq("tg_id", wa_id).execute()

    # If the user does not exist, insert the new user
    if not user_exists.data:
        supabase.table("Bot_Accounts").insert({
            "tg_id": wa_id,
            "tg_handle": name,
            "tg_refcode": referral_code, 
            "tg_type": "WhatsApp"
        }).execute()

        hey_msg = f"Hey There {name}, Welcome to Promptlys on WhatsApp!"
        data = get_text_message_input(wa_id, hey_msg)
        send_message(data)
        data = get_text_message_input(wa_id, guide_response)
        send_message(data)
        print("NEW WHATSAPP USER INSERTION SUCCESS !!")
    else:
        # Optionally, update the user's handle if it has changed
        supabase.table("Bot_Accounts").update({
            "tg_handle": name,
            "tg_refcode": referral_code  # Update this if you want to allow referral code updates
        }).eq("tg_id", wa_id).execute()
        print("WHATAPP BOT USER UPDATE SUCCESS !!")


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
    elif message_body.startswith('/guide'):
        data = get_text_message_input(wa_id, guide_response)
        send_message(data)
    elif message_body.startswith('/image'):
        user_prompt = message_body[len('/image'):].strip()  # Remove the command and leading spaces
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
            
            # Now, instead of sending the URL as text, use the send_image_to_whatsapp function as an IN-LINE image 
            send_image_to_whatsapp(wa_id, image_url)

            #data = get_text_message_input(wa_id, f"Here's the image: {image_url}")
            #send_message(data)
        except Exception as e:
            error_message = f"Failed to generate image: {str(e)}"
            data = get_text_message_input(wa_id, error_message)
            send_message(data)


    else:
        # Handle regular message
        data = get_text_message_input(wa_id, "Please wait while processing ..")
        print("HANDLING TEXT PROMPTS NOW.. ")
        send_message(data)
        response = generate_response(message_body)
        print("COMPLETING GENERATE_RESPONSE now.. ")
        data = get_text_message_input(wa_id, response)
        send_message(data)

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
