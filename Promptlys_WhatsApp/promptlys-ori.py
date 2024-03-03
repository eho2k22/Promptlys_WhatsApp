import os
import telebot
import hashlib
from openai import OpenAI


from telebot import types
from supabase import create_client, Client



client = OpenAI(api_key = os.environ['OPENAI_KEY'])


# Initialize the Supabase client
supa_url =  os.environ['SUPABASE_URL'] # Replace with your Supabase project URL
supa_key =  os.environ['SUPABASE_KEY'] # Replace with your Supabase project KEY

# Replace with your Supabase service role key
supabase = create_client(supa_url, supa_key)

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
            "tg_refcode": referral_code
        }).execute()
        print("NEW USER INSERTION SUCCESS !!")
    else:
        # Optionally, update the user's handle if it has changed
        supabase.table("Bot_Accounts").update({
            "tg_handle": user_handle,
            "tg_refcode": referral_code  # Update this if you want to allow referral code updates
        }).eq("tg_id", user_id).execute()
        print("USER UPDATE SUCCESS !!")


# Function to get the count of unique users
def get_unique_user_count():
    result = supabase.table("Bot_Accounts").select("tg_id", count='exact').execute()
    return result.count if result.count is not None else 0



#BOT_TOKEN = os.environ.get('BOT_TOKEN')
BOT_TOKEN = '6845936933:AAFln5qb8yG9H13i9e-gkQFpM8B4EZrfusA'
print("Bot Token = ")
print(BOT_TOKEN)
bot = telebot.TeleBot(BOT_TOKEN)
BOT_OWNER_ID = '1226261708'  


# Dictionary to store file_id against unique identifiers
assets = {}

# Variable to hold the last received file_id
last_received_file_id = None

@bot.message_handler(content_types=['document', 'video'])
def handle_docs_and_videos(message):
    global last_received_file_id
    print("Handling incoming file asset...")
    file_id = None
    if message.document:
        file_id = message.document.file_id
    elif message.video:
        file_id = message.video.file_id
    
    if file_id:
        last_received_file_id = file_id


@bot.message_handler(commands=['display_assets'])
def display_assets(message):
    # Split the message to get the identifier
    args = message.text.split(maxsplit=1)
    
    #if len(args) < 2:
        #bot.reply_to(message, "Please specify the asset identifier.")
        #return
    
    # When no specific identifier is provided
    if len(args) < 2:
        print("No Identifier specified")
        if assets:  # Check if there are any assets stored
            print("about to loop through assets..")
            response = "Available assets:\n" + "\n".join([f"{identifier}" for identifier in assets.keys()])
        else:
            response = "No assets available."
        #bot.send_message(chat_id, response)
            bot.reply_to(message, response)
        return


    identifier = args[1].strip()
    file_id = assets.get(identifier)


    
    if file_id:
        # Determine if it's a video or document based on stored information or simply try sending it
        bot.send_document(message.chat.id, file_id)  # or bot.send_video depending on your handling
    else:
        bot.reply_to(message, "Asset not found.")



# Assuming you have a function to create a menu
def create_menu(language='en'):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=4, one_time_keyboard=True)
    if language == 'cn':
        show_me_button = telebot.types.KeyboardButton('教程视频')
        masters_app_button = telebot.types.KeyboardButton('大师介绍')
        builder_app_button = telebot.types.KeyboardButton('Prompt构建')
        chat_app_button = telebot.types.KeyboardButton('聊天')
    else:  # Default to English
        show_me_button = telebot.types.KeyboardButton('VIDEOS')
        masters_app_button = telebot.types.KeyboardButton('MASTERS')
        builder_app_button = telebot.types.KeyboardButton('PROMPT BUILDER')
        chat_app_button = telebot.types.KeyboardButton('CHAT')

    markup.add(show_me_button, masters_app_button, builder_app_button, chat_app_button)
    return markup

####### Language-Specific START SECTION ##########

@bot.message_handler(commands=['start'])
def send_welcome(message):
    # Extract payload from the /start command if any
    payload = message.text[7:]  # This strips out '/start ' to see if there's anything following it
    user_id = message.from_user.id
    user_handle = message.from_user.username
    
    # Default values
    language = 'en'
    action = ''

    # Known language codes
    known_languages = ['cn', 'en']  # Extend this list as needed

    # Parse the payload for language and action if present
    if '_' in payload:
        parts = payload.split('_')
        language = parts[0] if parts[0] in ['cn', 'en'] else 'en'  # Validate language
        action = '_'.join(parts[1:])  # Remainder is considered the action

    elif payload in known_languages:
        # If the payload is a known language code without an action
        language = payload
        # The action remains as the default ('') or you can set a default action here
    else:
        action = payload  # Assuming the whole payload is an action if no underscore

    print(f"HANDLING MESSAGE: ABOUT TO UPDATE BOT ACCOUNTS !! Language: {language}, Action: {action}")
    update_bot_accounts(user_id, user_handle)  # Assuming you might want to store the preferred language too

    # Handle actions
    if action == 'show_masters':
        welcome_text = (
            f"Hi, @{user_handle}! , Welcome to PROMPT MASTERS Section 👋\n\n" if language == 'en' else
            f"您好, @{user_handle}! 欢迎来到PROMPT专家介绍 👋\n\n"
        )
        bot.send_message(message.chat.id, welcome_text)
        send_ambassadors_info(message)  
        return


    if action == 'show_videos':
        welcome_text = (
            f"Hi, @{user_handle}! , Welcome to Promptlys Overview  👋\n\n" if language == 'en' else
            f"您好, @{user_handle}! 欢迎观看Promptlys介绍视频 👋\n\n"
        )
        bot.send_message(message.chat.id, welcome_text)
        send_links(message)
        return  # Stop further processing to prevent showing the welcome message after handling the payload

    
    if action == 'build_prompt':
        welcome_text = (
            f"Hi, @{user_handle}! , Welcome to Prompt Builder 👋\n\n" if language == 'en' else
            f"您好, @{user_handle}! 欢迎使用Prompt生成器 👋\n\n"
        )
        bot.send_message(message.chat.id, welcome_text)
        build_prompt(message, language=language)
        return  # Stop further processing to prevent showing the welcome message after handling the payload


    if action == 'build_chat':
        welcome_text = (
            f"Hi, @{user_handle}! , Welcome to Promptlys TeleBot Chat 👋\n\n" if language == 'en' else
            f"您好, @{user_handle}! 欢迎来 Promptlys TeleBot 聊天 👋\n\n"
        )
        bot.send_message(message.chat.id, welcome_text)
        build_chat(message, language=language)
        return  # Stop further processing to prevent showing the welcome message after handling the payload


    # Default welcome message
    welcome_text = (
        f"Hi, @{user_handle}! Welcome to the Promptlys TeleBot 🧞‍♂️✨! 👋\n\n"
        "I am here to answer all your questions about Promptlys, A Professional Prompt Network helping professionals optimize their generative AI communications!\n\n"
        "You can select from the following: \n\n" 
        "1. Execute commands from the actions menu \n\n"
        "2. Prefix 'prompt: ' to a prompt text and the Bot will fix and revise your prompt. \n\n"
        "3. Prefix 'chat: ' to your chat and the bot will chat and respond to your query. \n\n"
        "Ready to amplify your prompts with the power of our expert community? 🚀\n\n"
        "Let's embark on this exciting journey together!.\n\n"
        if language == 'en'
        else
        f"嗨，@{user_handle}！欢迎来到 Promptlys TeleBot 🧞‍♂️✨！👋\n\n"
        "我在这里回答您关于Promptlys的所有问题，Promptlys是一个帮助专业人士优化生成式AI通信的专业Prompt平台！\n\n"
        "您可以做以下：\n\n"
        "1. 点击操作菜单中执行命令\n\n"
        "2. 给提示内容前加上'prompt: '，Promptlys TeleBot 将修复并提高提示质量。\n\n"
        "3. 给聊天内容前加上'chat: '，Promptlys TeleBot 将聊天并回应你的查询。\n\n"
    )


    menu = create_menu(language=language)  # Updated to include language support

    image_url = 'https://msfpfmwdawonueqaevru.supabase.co/storage/v1/object/public/img/promptlys-120.png'
    # Send an image from a URL and a welcome message with a custom keyboard
    bot.send_photo(message.chat.id, image_url)
    bot.send_message(message.chat.id, welcome_text, reply_markup=menu)





@bot.message_handler(commands=['show_videos'])
def send_links(message):
    links = [
        "Founder's Welcome:\n https://youtu.be/gd4WdqHpeXc",
        "Good Prompt vs Poor Prompt Comparison:\n https://youtu.be/Vddk35EUp-A",
        "MidJourney Prompting:\n https://youtu.be/APoLJir9N0U"
    ]
    response = '\n\n'.join(links)  # Add two new lines for spacing between each link
    bot.reply_to(message, response)




@bot.message_handler(commands=['show_masters'])
def send_masters_info(message):
    document_url = 'https://demo.promptlys.ai/prompt_masters/'
    response_message = f"Please browse attached document link for details on Masters: {document_url}"
    bot.reply_to(message, response_message)


@bot.message_handler(commands=['referral'])
def send_referral_link(message):
    user_id = message.from_user.id
    # Create a unique referral code using the user's ID. This is a simple example using SHA256 hashing.
    referral_code = hashlib.sha256(str(user_id).encode('utf-8')).hexdigest()[:10]  # Take the first 10 characters for brevity
    # Construct the referral link.
    referral_link = f"https://t.me/Promptlys_TeleBot?start={referral_code}"
    # Send the referral link to the user.
    bot.reply_to(message, f"Your personal invite link {referral_link}")


# Command handler for '/show_counts'
@bot.message_handler(commands=['show_counts'])
def show_counts(message):
    # Check if the user's ID matches the authorized ID
    if str(message.from_user.id) == '1226261708':
        user_count = get_unique_user_count()
        bot.send_message(message.chat.id, f"Promptlys TeleBot User Total = {user_count}")
    else:
        bot.send_message(message.chat.id, "Sorry, this TG account is not authorized to perform this action.")




@bot.message_handler(commands=['build_prompt'])
def build_prompt(message, language='en'):
    if language == 'cn':
        instructions = "请输入'prompt:' 或 '/prompt'  前缀的提示描述，然后让Promptlys TeleBot 对其进行增强！ 例如，“prompt：提供有关大学申请流程的提示示例。”'"
    else:
        instructions = "Please input your prompt description prefixed with 'prompt:' and let Promptlys Telebot enhance it !   ex: 'prompt: provide prompt examples for the college application process.'"
    
    bot.reply_to(message, instructions)



@bot.message_handler(commands=['build_chat'])
def build_chat(message, language='en'):
    if language == 'cn':
        instructions = "请输入前缀为 'chat:'或 '/chat' 的聊天消息与Promptlys TeleBot 聊天。 例如，'chat：提供挪威7日游必看推荐。'"
    else:
        instructions = "Please input your chat message prefixed with 'chat:' to interact with Promptlys TeleBot. For example, 'chat: Provide recommendations for a 7-day trip to Norway.'"
    
    bot.reply_to(message, instructions)





@bot.message_handler(func=lambda message: True)
def handle_message(message):
    # Whenever a user interacts with the bot, call update_bot_accounts
    user_id = message.from_user.id
    user_handle = message.from_user.username
    print("HANDLING MESSAGE: ABOUT TO UPDATE BOT ACCOUNTS !!")
    update_bot_accounts(user_id, user_handle)

    if message.text == 'VIDEOS' or message.text == '教程视频':
        send_links(message)
    elif message.text == 'MASTERS' or message.text == '大师介绍':
        send_masters_info(message)
    elif message.text == 'PROMPT BUILDER' or message.text == 'Prompt构建':
        if message.text == 'PROMPT BUILDER':
            build_prompt(message)
        else:
            build_prompt(message, 'cn')
    elif message.text == 'CHAT' or message.text == '聊天':
        if message.text == 'CHAT':
            build_chat(message)
        else:
            build_chat(message, 'cn')
    
    #else:
        #echo_all(message)
        #bot.reply_to(message, message.text)
    elif message.text.startswith("store:"):
        global assets
        if last_received_file_id: 
            identifier = message.text.split("store:")[1].strip()  # Extract the identifier
            print("FILE IDENTIFIER for the next File == ")
            print(identifier)
            assets[identifier] = last_received_file_id
            bot.reply_to(message, f"Stored {identifier} with file_id: {last_received_file_id}")
            print(f"Stored {identifier} with file_id: {last_received_file_id}")

    elif message.text.startswith("prompt:") or message.text.startswith("Prompt:") or message.text.startswith("/prompt") or message.text.startswith("/Prompt"):
        # Enhanced part to interact with the specified OpenAI model
        bot.reply_to(message, "ACK: " + message.text + " Please wait while processing ...")
        try:
            messages = [
                {"role": "system", "content": "You are an expert prompt builder that is proficient at digesting vague, generic prompts and converting them to specific, well-constructed prompts by following general prompting guidelines such as setting the role, the tone, providing context specfics and describing expected output format."},
                {"role": "assistant", "content": "This is Context. "},
                {"role": "user", "content": "This is User's Question"}
            ]
     
            for item in messages:
                if item["role"] == "user":
                    item["content"] = message.text
                   
                #if item["role"] == "assistant":
                    #item["content"] = previous_context
            

            gpt_response = client.chat.completions.create(model="gpt-4-0125-preview",
            messages=messages)
            
            bot_reply = gpt_response.choices[0].message.content

            #bot_reply = response.choices[0].text.strip()
            bot.reply_to(message, bot_reply)
        except Exception as e:
            print(f"Error accessing OpenAI API: {e}")
            bot.reply_to(message, "Sorry, I couldn't process that request. Please try again later.")
    
    elif message.text.startswith("chat:") or message.text.startswith("Chat:") or message.text.startswith("/chat") or message.text.startswith("/Chat"):
        # Enhanced part to interact with the specified OpenAI model
        bot.reply_to(message, "ACK: " + message.text + " Please wait while processing ...")
        try:
            messages = [
                {"role": "system", "content": "You are an expert prompt interpreter that is adept at understanding imperfect, error-prone user prompts and come up with the most optima, relevant, and engaging responses."},
                {"role": "assistant", "content": "This is Context. "},
                {"role": "user", "content": "This is User's Question"}
            ]
     
            for item in messages:
                if item["role"] == "user":
                    item["content"] = message.text
                   
                #if item["role"] == "assistant":
                    #item["content"] = previous_context
            

            gpt_response = client.chat.completions.create(model="gpt-4-0125-preview",
            messages=messages)
            
            bot_reply = gpt_response.choices[0].message.content

            #bot_reply = response.choices[0].text.strip()
            bot.reply_to(message, bot_reply)
        except Exception as e:
            print(f"Error accessing OpenAI API: {e}")
            bot.reply_to(message, "Sorry, I couldn't process that request. Please try again later.")
    
    elif message.text.startswith("image:") or message.text.startswith("Image:") or message.text.startswith("/image") or message.text.startswith("/Image"):
         # Enhanced part to interact with the specified OpenAI model
        try:
            messages = [
                {"role": "system", "content": "You are an expert and creative illustrator that is adept at understanding imperfect, error-prone user prompts and convert the into the most remarkable and relatable images."},
                {"role": "assistant", "content": "This is Context. "},
                {"role": "user", "content": "This is User's Question"}
            ]
    
            for item in messages:
                if item["role"] == "user":
                    item["content"] = message.text

            response = client.images.generate(
            model="dall-e-3",
            prompt=message.text,
            size="1024x1024",
            quality="standard",
            n=1,
            )
            print("Message Text = ")
            print(message.text)
            print("Image Prompt = ")
            print(message.text[6:])
            image_url = response.data[0].url
            bot.send_photo(message.chat.id, image_url)
        
        except Exception as e:
            print(f"Error accessing OpenAI Image API: {e}")
            bot.reply_to(message, "Sorry, I couldn't process that image request. Please try again later.")

    else:
        # bot.reply_to(message, message.text)
        bot.reply_to(message, "ACK: " + message.text + " Please wait while processing ...")
        # Enhanced part to interact with the specified OpenAI model
        try:
            messages = [
                {"role": "system", "content": "You are an expert prompt interpreter that is adept at understanding imperfect, error-prone user prompts and come up with the most optima, relevant, and engaging responses."},
                {"role": "assistant", "content": "This is Context. "},
                {"role": "user", "content": "This is User's Question"}
            ]
     
            for item in messages:
                if item["role"] == "user":
                    item["content"] = message.text
                   
                #if item["role"] == "assistant":
                    #item["content"] = previous_context
            

            gpt_response = client.chat.completions.create(model="gpt-4-0125-preview",
            messages=messages)
            
            bot_reply = gpt_response.choices[0].message.content

            #bot_reply = response.choices[0].text.strip()
            bot.reply_to(message, bot_reply)
        except Exception as e:
            print(f"Error accessing OpenAI API: {e}")
            bot.reply_to(message, "Sorry, I couldn't process that request. Please try again later.")

bot.polling()
