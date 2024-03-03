import os
import telebot
import hashlib
from openai import OpenAI
import linebot 

#deprecated!!
##from linebot import LineBotApi
##from linebot import WebhookHandler

from linebot import v3
from linebot import LineBotApi
from linebot.v3.webhook import WebhookHandler
from linebot import LineBotApi
from linebot.models import MessageEvent, TextMessage


### V3 ######
from linebot.v3.exceptions import (
    InvalidSignatureError
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent
)
### V3 ######

#from linebot.models import TextSendMessage
from linebot.exceptions import LineBotApiError
from flask import Flask, request, abort


from telebot import types
from supabase import create_client, Client



openai_key = os.environ['OPENAI_KEY']
supa_url = os.environ['SUPABASE_URL']
supa_key = os.environ['SUPABASE_KEY']
line_access_token = os.environ['LINE_ACCESS_TOKEN']
line_channel_secret = os.environ['LINE_CHANNEL_SECRET']



# Initialize the Supabase client

# Replace with your Supabase service role key
supabase = create_client(supa_url, supa_key)



# Initialize Flask app
app = Flask(__name__)


client = OpenAI(api_key = openai_key)


# Initialize Line bot API
#line_bot_api = LineBotApi(line_access_token)

### V3 ######
configuration = Configuration(access_token=line_access_token)
### V3 ######

handler = WebhookHandler(line_channel_secret)






# Function to determine user locale based on profile
def get_user_locale(user_id):
    try:
        profile = line_bot_api.get_profile(user_id)
        return profile.language
    except LineBotApiError as e:
        print(f"Error getting user profile: {e}")
        return None


# Function to get user profile including handle
def get_user_profile(user_id):
    try:
        profile = line_bot_api.get_profile(user_id)
        return profile.display_name
    except LineBotApiError as e:
        print(f"Error getting user profile: {e}")
        return None



# Function to add or update user info in the "Bot_Accounts" table
def update_bot_accounts(user_id, user_handle):

    # Generate a unique referral code using the user's ID
    referral_code = hashlib.sha256(str(user_id).encode('utf-8')).hexdigest()[:10]
    # Check if the user already exists in the database
    print("CHECKING IF USER EXISTS")
    user_exists = supabase.table("Bot_Accounts").select("*").eq("tg_id", user_id).execute()

    # If the user does not exist, insert the new user
    if not user_exists.data:
        supabase.table("Bot_Accounts").insert({
            "tg_id": user_id,
            "tg_handle": user_handle,
            "tg_refcode": referral_code, 
            "tg_type": "Line"
        }).execute()
        print("NEW LINE BOT USER INSERTION SUCCESS !!")
    else:
        # Optionally, update the user's handle if it has changed
        supabase.table("Bot_Accounts").update({
            "tg_handle": user_handle,
            "tg_refcode": referral_code  # Update this if you want to allow referral code updates
        }).eq("tg_id", user_id).execute()
        print("LINE BOT USER UPDATE SUCCESS !!")


# Function to get the count of unique users
def get_unique_user_count():
    result = supabase.table("Bot_Accounts").select("tg_id", count='exact').execute()
    return result.count if result.count is not None else 0






# Function to handle incoming messages
def handle_message(event):
    user_id = event.source.user_id
    message_text = event.message.text

    # Determine user's locale
    locale = get_user_locale(user_id)

    # Process message based on prefixes
    if message_text.startswith('/guide'):
        send_guide_message(user_id)
    elif message_text.startswith('chat:') or message_text.startswith('prompt:'):
        invoke_openai_api(user_id, message_text, locale)
    #elif message_text.startswith('prompt:'):
        #invoke_openai_api(user_id, message_text[len('prompt:'):], locale)
    else:
        # Default response for unrecognized messages
        send_default_response(user_id, locale)

# Function to send guide message
# Function to send guide message
def send_guide_message(user_id, locale='zh-Hant'):
    # English version of the guide message
    guide_message_en = (
        "1.Prefix 'prompt: ' to your prompt description and the Bot will enhance, revise and generate your prompt!\n"
        "2.Prefix 'chat: ' to a prompt or question then the Bot will chat and respond to your query.\n"
        "3.Type '/guide' to replay instructions"
    )
    
    # Traditional Chinese version of the guide message
    guide_message_zh = (
        "1.在您的提示描述前加上“prompt:”，機器人將增強、修改並生成您的提示！\n"
        "2.在提示或問題前加上“chat:”，機器人將進行聊天並回答您的查詢。\n"
        "3.輸入'/guide'重播說明。"
    )
    
    # Determine which message to send based on user's locale
    if locale == 'zh-Hant':
        send_message(user_id, guide_message_zh)
    else:
        send_message(user_id, guide_message_en)


# Function to invoke OpenAI API
def invoke_openai_api(user_id, user_text, locale):
    # Implement OpenAI API invocation to generate response or prompt
    # Replace this placeholder with actual code to call OpenAI API

    # For demonstration purposes, just echo back the input prompt
    #response = f"Received prompt: {prompt}"

    # Enhanced part to interact with the specified OpenAI model
    messages = []
    prompt = ""

    try:
        if user_text.startswith('prompt:'):
            messages = [
                {"role": "system", "content": "You are an expert prompt builder that is proficient at digesting vague, generic prompts and converting them to specific, well-constructed prompts by following general prompting guidelines such as setting the role, the tone, providing context specfics and describing expected output format."},
                {"role": "assistant", "content": "This is Context. "},
                {"role": "user", "content": "This is User's Question"}
            ]
            prompt = user_text[len('prompt:'):]
        
        if user_text.startswith('chat:'):
            messages = [
                {"role": "system", "content": "You are an expert prompt analyzer that is adept at understanding imperfect, error-prone user prompts and come up with the most optima, relevant, and engaging responses."},
                {"role": "assistant", "content": "This is Context. "},
                {"role": "user", "content": "This is User's Question"}
            ]
            prompt = user_text[len('chat:'):]
    
        for item in messages:
            if item["role"] == "user":
                item["content"] = prompt
                
        
        gpt_response = client.chat.completions.create(model="gpt-4-0125-preview",
        messages=messages)
        
        bot_reply = gpt_response.choices[0].message.content
        send_message(user_id, bot_reply)
        return 

    except Exception as e:
        print(f"Error accessing OpenAI API: {e}")
        send_message(user_id, "Sorry, I couldn't process that request. Please try again later.")
        return

    if locale == 'zh-Hant':
        send_message(user_id, f"收到你的提示描述: {prompt}")
    else : 
        send_message(user_id, f"Received prompt: {prompt}")

# Function to send default response for unrecognized messages
def send_default_response(user_id, locale):
    # Default response for unrecognized messages
    if locale == 'zh-Hant':
        default_response = "抱歉，我沒有理解。請輸入 '/guide' 查看說明。"
    else: 
        default_response = "Sorry, I didn't understand that. Type '/guide' for instructions."

    send_message(user_id, default_response)

# Function to send message to user
def send_message(user_id, message):
    try:
        line_bot_api.push_message(user_id, TextSendMessage(text=message))
    except LineBotApiError as e:
        print(f"Error sending message to user {user_id}: {e}")

# Define webhook endpoint for receiving messages
@app.route('/webhook', methods=['POST'])
def webhook():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'





##### V2 #############

# Register message event handler
## @handler.add(MessageEvent, message=TextMessage)
## def handle_message_event(event):
    # Extract user ID and handle from the event
    ##user_id = event.source.user_id
   ## user_handle = get_user_handle(user_id)  # Assuming sender_id is the handle, adjust accordingly
    
    # Invoke the function to update bot accounts
    ## update_bot_accounts(user_id, user_handle)
    
   ## handle_message(event)




##### V3 ########

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message_event(event):
    try:
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=f'ACKNOWLEDGED: {event.message.text}')]  # Prefix added here
                )
            )

        # Extract user ID and handle from the event
        user_id = event.source.user_id
        user_handle = get_user_handle(user_id)  # Assuming sender_id is the handle, adjust accordingly
        
        # Invoke the function to update bot accounts
        update_bot_accounts(user_id, user_handle)
        
        # Handle the message
        handle_message(event)
    except Exception as e:
        print(f"Error handling message: {e}")





if __name__ == '__main__':
    app.run()


#################################################################
















