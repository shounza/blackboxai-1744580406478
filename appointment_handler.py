from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import (
    CommandHandler, 
    MessageHandler, 
    Filters, 
    ConversationHandler,
    CallbackContext,
    CallbackQueryHandler
)
import logging
from datetime import datetime
from utils import validate_date, validate_time, store_appointment, get_user_appointments, cancel_appointment

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
DATE, TIME, NOTES, CONFIRMATION = range(4)

# Callback data
CONFIRM = 'confirm'
CANCEL = 'cancel'

def start(update: Update, context: CallbackContext) -> int:
    """Start the conversation and ask for date."""
    user = update.message.from_user
    logger.info(f"User {user.first_name} started booking process")
    
    message = (
        f"👋 Hi {user.first_name}! Let's book your appointment.\n\n"
        "Please enter the date for your appointment in YYYY-MM-DD format.\n"
        "For example: 2024-02-01"
    )
    
    update.message.reply_text(message)
    return DATE

def date_handler(update: Update, context: CallbackContext) -> int:
    """Handle the date input and ask for time."""
    user = update.message.from_user
    date_string = update.message.text
    
    # Validate date
    is_valid, date_obj = validate_date(date_string)
    
    if not is_valid:
        message = (
            "❌ Invalid date format or past date.\n\n"
            "Please enter a future date in YYYY-MM-DD format.\n"
            "For example: 2024-02-01"
        )
        update.message.reply_text(message)
        return DATE
    
    # Store date in context
    context.user_data['appointment_date'] = date_obj
    
    message = (
        "📅 Date confirmed!\n\n"
        "Now, please enter the time for your appointment in HH:MM format (24-hour).\n"
        "Available hours are between 09:00 and 17:00\n"
        "For example: 14:30"
    )
    
    update.message.reply_text(message)
    return TIME

def time_handler(update: Update, context: CallbackContext) -> int:
    """Handle the time input and ask for notes."""
    user = update.message.from_user
    time_string = update.message.text
    
    # Validate time
    is_valid, time_obj = validate_time(time_string)
    
    if not is_valid:
        message = (
            "❌ Invalid time format or outside business hours.\n\n"
            "Please enter a time between 09:00 and 17:00 in HH:MM format.\n"
            "For example: 14:30"
        )
        update.message.reply_text(message)
        return TIME
    
    # Store time in context
    context.user_data['appointment_time'] = time_obj
    
    message = (
        "⏰ Time confirmed!\n\n"
        "Would you like to add any notes for your appointment?\n"
        "Type your notes or send /skip to continue without notes."
    )
    
    update.message.reply_text(message)
    return NOTES

def notes_handler(update: Update, context: CallbackContext) -> int:
    """Handle notes and show confirmation."""
    user = update.message.from_user
    notes = update.message.text
    
    if notes == '/skip':
        notes = ""
    
    # Store notes in context
    context.user_data['appointment_notes'] = notes
    
    return show_confirmation(update, context)

def show_confirmation(update: Update, context: CallbackContext) -> int:
    """Show appointment details and ask for confirmation."""
    date_obj = context.user_data['appointment_date']
    time_obj = context.user_data['appointment_time']
    notes = context.user_data.get('appointment_notes', '')
    
    message = (
        "*📋 Appointment Details*\n\n"
        f"📅 Date: {date_obj.strftime('%Y-%m-%d')}\n"
        f"⏰ Time: {time_obj.strftime('%H:%M')}\n"
    )
    
    if notes:
        message += f"📝 Notes: {notes}\n"
    
    message += "\nWould you like to confirm this appointment?"
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Confirm", callback_data=CONFIRM),
            InlineKeyboardButton("❌ Cancel", callback_data=CANCEL)
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        update.message.reply_text(message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    else:
        update.callback_query.message.reply_text(message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    
    return CONFIRMATION

def handle_confirmation(update: Update, context: CallbackContext) -> int:
    """Handle the confirmation button press."""
    query = update.callback_query
    query.answer()
    
    user = query.from_user
    choice = query.data
    
    if choice == CONFIRM:
        # Store appointment
        success, message = store_appointment(
            user_id=user.id,
            user_name=user.first_name,
            date=context.user_data['appointment_date'],
            time=context.user_data['appointment_time'],
            notes=context.user_data.get('appointment_notes', '')
        )
        
        if success:
            query.message.reply_text(
                "✅ Great! Your appointment has been confirmed!\n\n"
                f"See you on {context.user_data['appointment_date'].strftime('%Y-%m-%d')} "
                f"at {context.user_data['appointment_time'].strftime('%H:%M')}!\n\n"
                "You can book another appointment using /start"
            )
        else:
            query.message.reply_text(
                f"❌ {message}\n"
                "Please try booking again using /start"
            )
    else:
        query.message.reply_text(
            "❌ Appointment booking cancelled.\n"
            "You can start a new booking using /start"
        )
    
    # Clear user data
    context.user_data.clear()
    return ConversationHandler.END

def cancel(update: Update, context: CallbackContext) -> int:
    """Cancel the conversation."""
    user = update.message.from_user
    logger.info(f"User {user.first_name} canceled the conversation.")
    
    update.message.reply_text(
        "❌ Appointment booking cancelled.\n"
        "You can start a new booking using /start"
    )
    
    # Clear user data
    context.user_data.clear()
    return ConversationHandler.END

def view_appointments(update: Update, context: CallbackContext) -> None:
    """Show user's appointments."""
    user = update.message.from_user
    appointments = get_user_appointments(user.id)
    
    if not appointments:
        update.message.reply_text(
            "📅 You don't have any appointments scheduled.\n"
            "You can book an appointment using /start"
        )
        return
    
    message = "*📋 Your Appointments*\n\n"
    
    for apt in appointments:
        message += (
            f"🔹 *{apt['date']} at {apt['time']}*\n"
            f"   ID: `{apt['id']}`\n"
        )
        if apt['notes']:
            message += f"   Notes: {apt['notes']}\n"
        message += "\n"
    
    message += "To cancel an appointment, use:\n/cancel <appointment_id>"
    
    update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

def cancel_appointment_command(update: Update, context: CallbackContext) -> None:
    """Cancel a specific appointment."""
    if not context.args:
        update.message.reply_text(
            "❌ Please provide an appointment ID.\n"
            "Use /view to see your appointments and their IDs."
        )
        return
    
    appointment_id = context.args[0]
    user = update.message.from_user
    
    success, message = cancel_appointment(appointment_id, user.id)
    
    if success:
        update.message.reply_text(f"✅ {message}")
    else:
        update.message.reply_text(f"❌ {message}")

def get_appointment_handlers():
    """Return the conversation handler and other command handlers."""
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            DATE: [MessageHandler(Filters.text & ~Filters.command, date_handler)],
            TIME: [MessageHandler(Filters.text & ~Filters.command, time_handler)],
            NOTES: [
                MessageHandler(Filters.text & ~Filters.command, notes_handler),
                CommandHandler('skip', notes_handler)
            ],
            CONFIRMATION: [CallbackQueryHandler(handle_confirmation)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    return [
        conv_handler,
        CommandHandler('view', view_appointments),
        CommandHandler('cancel', cancel_appointment_command)
    ]
