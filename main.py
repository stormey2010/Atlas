import discord  # For Discord bot functionality
import openai   # For OpenAI API interaction
import groq     # For Groq interaction
from groq import Client  # Example Groq API client class
from datetime import datetime  # To timestamp logs
from memory.extract import memory_set
import memory.retrieve as retrieve
import memory.db_handler as db_handler
import memory.db as db
import threading
from config import *


groq_client = Client(api_key=GROQ_API)  # Initialize client

# System instructions for OpenAI
SYSTEM_INSTRUCTIONS = """you are a helpful assistant..."""

# Correct model specified for the project
MODEL_NAME = "gpt-4o-mini"

# Initializing Discord client with necessary intents
intents = discord.Intents.default()
intents.message_content = True  # Allows access to message content for commands
client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)

# Bot startup event to confirm login and sync commands
@client.event
async def on_ready():
    print(f'Logged in as {client.user} (ID: {client.user.id})')
    try:
        await tree.sync()  # Syncs commands globally
        print("Commands synced successfully.")
    except Exception as e:
        print(f"Error syncing commands: {e}")

# Slash command to interact with the bot
@tree.command(name="atlas", description="Ask ATLAS anything!")
async def atlas(interaction: discord.Interaction, question: str):
    try:
        # Check if interaction is valid and defer it
        print("Received interaction, deferring response...")
        await interaction.response.defer()

        # Check if question is empty or invalid (early validation)
        if not question.strip():
            await interaction.followup.send("Please provide a valid question.")
            return

        print("Processing the question...")

        # Retrieve user details from the interaction (Discord)
        user_id = interaction.user.id
        username = interaction.user.name
        discriminator = interaction.user.discriminator

        # Retrieve relevant memory based on the current query
        relevant_memory = retrieve.retrive(question, user_id)

        # Formulate the full context for the model
        messages = [
            {"role": "system", "content": SYSTEM_INSTRUCTIONS},
        ]

        if relevant_memory:  # Add memory context if available
            memory_context = (
                f"Here is some relevant past information:\n{relevant_memory}\n\n"
                f"Proceed with the user's new query."
            )
            messages.append({"role": "system", "content": memory_context})
        
        # Add the user's current question
        messages.append({"role": "user", "content": question})

        # Debugging: Print messages being sent to Groq
        print("Messages sent to Groq:", messages)

        # Format the context for Groq (flatten if required by Groq's API)
        formatted_context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])

        # Call Groq for the response
        try:
            response = groq_client.chat.completions.create(
                messages=messages,  # Pass the conversation context
                model="llama-3.2-90b-vision-preview",  # Replace with the actual Groq model/version
                max_tokens=1500,
                temperature=0.65,
            )
        except Exception as groq_error:
            # Catch any errors with the Groq API
            return await extract(interaction, groq_error)

        # Debugging: Print raw Groq API response
        print("Groq API response:", response)

        # Extract the answer from the Groq response
        answer = response.choices[0].message.content.strip()

        # Debugging: Print the final answer
        print("Answer from Groq:", answer)

        # Send the answer to Discord (handling large answers)
        if len(answer) > 2000:
            parts = [answer[i:i + 2000] for i in range(0, len(answer), 2000)]
            for part in parts:
                await interaction.followup.send(part)  # Send each chunk as a follow-up
        else:
            await interaction.followup.send(f"ATLAS: {answer}")

        # Save the user input and bot response to memory
        print(user_id)
        memory_set(question, user_id, username)

    except Exception as e:
        # Catch any other unexpected errors
        await interaction.followup.send("Error connecting to A.T.L.A.S Servers. Please try again.")
        print(f"Unexpected Error: {e}")

async def extract(interaction, groq_error):
    await interaction.followup.send("Error connecting to ATLAS Servers. Please try again.")
    print(f"Groq API error: {groq_error}")
    return

memory_ui_thread = threading.Thread(target=lambda: db.app.run(debug=False, threaded=True), daemon=True)
memory_ui_thread.start()
# Start the bot
client.run(DISCORD_TOKEN)
