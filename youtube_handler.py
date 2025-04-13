import os
import yt_dlp
from telegram.ext import CommandHandler, MessageHandler, Filters, ConversationHandler
from telegram import ParseMode

# States for conversation
WAITING_FOR_LINK = 1

def start_download(update, context):
    """Start the download process by asking for a YouTube link"""
    update.message.reply_text(
        "🎵 Please send me a YouTube link to download the music.\n"
        "Make sure it's a valid YouTube URL."
    )
    return WAITING_FOR_LINK

def download_music(update, context):
    """Handle the YouTube link and download the music"""
    youtube_url = update.message.text
    chat_id = update.effective_chat.id
    
    # Send processing message
    processing_message = update.message.reply_text(
        "⏳ Processing your request... Please wait."
    )
    
    try:
        # Configure yt-dlp options
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': f'downloads/{chat_id}_%(title)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'extract_audio': True,
            'audio_format': 'mp3',
            'audio_quality': '192K',
            'no_check_certificate': True,
            'prefer_insecure': True,
            'geo_bypass': True,
            'nocheckcertificate': True,
            'ignoreerrors': True,
            'no_playlist': True,
            'extractor_retries': 'auto',
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web'],
                    'player_skip': ['configs', 'webpage']
                }
            }
        }
        
        # Create downloads directory if it doesn't exist
        os.makedirs('downloads', exist_ok=True)
        
        # Download the audio
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                # First try to extract info without downloading
                info = ydl.extract_info(youtube_url, download=False)
                title = info['title']
                
                # Update processing message with title
                processing_message.edit_text(
                    f"📥 Downloading: {title}\nPlease wait..."
                )
                
                # Now proceed with download
                info = ydl.extract_info(youtube_url, download=True)
                duration = info['duration']
                
                # Get the path of the downloaded file
                download_path = f"downloads/{chat_id}_{title}.mp3"
                
                # Check if file size is within Telegram's limit (50MB)
                file_size = os.path.getsize(download_path)
                if file_size > 50 * 1024 * 1024:  # 50MB in bytes
                    os.remove(download_path)
                    processing_message.edit_text(
                        "❌ Sorry, the audio file is too large (>50MB). "
                        "Please try a shorter video."
                    )
                    return ConversationHandler.END
                
                # Send the audio file
                with open(download_path, 'rb') as audio_file:
                    context.bot.send_audio(
                        chat_id=chat_id,
                        audio=audio_file,
                        title=title,
                        duration=duration,
                        caption=f"🎵 *{title}*",
                        parse_mode=ParseMode.MARKDOWN
                    )
                
                # Clean up
                os.remove(download_path)
                processing_message.delete()
                
            except yt_dlp.utils.DownloadError as de:
                error_message = str(de).lower()
                if "sign in" in error_message or "confirm your age" in error_message:
                    processing_message.edit_text(
                        "❌ Sorry, this video is age-restricted and cannot be downloaded."
                    )
                elif "private video" in error_message:
                    processing_message.edit_text(
                        "❌ Sorry, this video is private and cannot be accessed."
                    )
                elif "copyright" in error_message:
                    processing_message.edit_text(
                        "❌ Sorry, this video is not available due to copyright restrictions."
                    )
                else:
                    processing_message.edit_text(
                        "❌ Sorry, there was an error downloading this video. "
                        "Please try another URL."
                    )
                return ConversationHandler.END
                
    except Exception as e:
        processing_message.edit_text(
            "❌ An error occurred while processing your request.\n"
            "Please make sure you've sent a valid YouTube URL."
        )
    
    return ConversationHandler.END

def cancel(update, context):
    """Cancel the conversation."""
    update.message.reply_text(
        "❌ Download cancelled. Send /download to start a new download."
    )
    return ConversationHandler.END

def get_youtube_handlers():
    """Return the handlers for YouTube download functionality"""
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('download', start_download)],
        states={
            WAITING_FOR_LINK: [
                MessageHandler(
                    Filters.text & ~Filters.command,
                    download_music
                )
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    return [conv_handler]
