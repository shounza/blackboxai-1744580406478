import os
import logging
from telegram.ext import Updater, CommandHandler
from youtube_handler import get_youtube_handlers

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def error_handler(update, context):
    """Log Errors caused by Updates."""
    logger.error(f'Update "{update}" caused error "{context.error}"')
    
    # Send message to user only if update and effective_message exist
    if update and hasattr(update, 'effective_message') and update.effective_message:
        update.effective_message.reply_text(
            "❌ Sorry, an error occurred. Please try again or contact support."
        )

def help_command(update, context):
    """Send a message when the command /help is issued."""
    help_text = (
        "🤖 *YouTube Music Downloader Bot*\n\n"
        "Available commands:\n\n"
        "🎵 */download* - Download music from YouTube\n"
        "❓ */help* - Show this help message\n\n"
        "To download music:\n"
        "1. Use /download command\n"
        "2. Send a valid YouTube URL\n"
        "3. Wait for the bot to process and send your music\n\n"
        "Note: Maximum file size limit is 50MB"
    )
    
    update.message.reply_text(help_text, parse_mode='Markdown')

def main():
    """Start the bot."""
    # Create the Updater and pass it your bot's token
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    if not TOKEN:
        logger.error("No token provided! Set TELEGRAM_BOT_TOKEN environment variable.")
        return

    try:
        logger.info("Starting bot initialization...")
        
        # Set higher logging level for httpx to avoid excessive logs
        logging.getLogger("httpx").setLevel(logging.WARNING)
        
        # Initialize the updater
        logger.info("Initializing updater with token...")
        updater = Updater(TOKEN, use_context=True)
        
        # Get the dispatcher
        logger.info("Setting up dispatcher...")
        dp = updater.dispatcher
        
        # Register handlers
        logger.info("Registering command handlers...")
        dp.add_handler(CommandHandler("help", help_command))
        
        logger.info("Registering YouTube handlers...")
        for handler in get_youtube_handlers():
            dp.add_handler(handler)
        
        logger.info("Registering error handler...")
        dp.add_error_handler(error_handler)
        
        # Start the Bot
        logger.info("Starting polling...")
        updater.start_polling(drop_pending_updates=True)
        logger.info("Bot started successfully!")
        
        # Run the bot until you press Ctrl-C
        updater.idle()
        
    except Exception as e:
        logger.error(f"Error starting bot: {str(e)}")
        raise  # Re-raise the exception to see the full traceback

if __name__ == '__main__':
    main()
