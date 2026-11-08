import os
import random
import string
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
SUPPORT_HANDLE = "@Saintlockgg"

PAYMENTS = {
    "【entity-Chime¦canonical_name=Chime】": os.getenv("CHIME_TAG", "$saintlockbase"),
    "Cashapp": os.getenv("CASHAPP_TAG", "$saintlockecon"),
    "BTC": os.getenv("BTC_ADDRESS", "3QCnokVAVef596eFDitZyVHzcPcu6PggTF"),
    "SOL": os.getenv("SOL_ADDRESS", "2tk82QkRPHYTG1WmPyJQcEYmGNEazVKrUiiHPJ3jCtFH"),
    "ETH": os.getenv("ETH_ADDRESS", "0xb17D7Cdd7e1cbd379ad2dc3E8518A626Faea93FD"),
}

# 【entity-SQUARE¦canonical_name=Square】 - ONE LINK FOR ALL PRODUCTS
# Get it from 【entity-Square¦canonical_name=Square】 -> Online -> Payment Links -> Create link -> Let customers enter amount
SQUARE_CHECKOUT_LINK = os.getenv("SQUARE_CHECKOUT_LINK", "https://square.link/u/test")

# Products - change names/prices here
PRODUCTS = {
    "hoodie": {"name": "Carmine Hoodie", "price": 60, "desc": "Black / Red Hoodie"},
    "tee": {"name": "Saintlock Tee", "price": 35, "desc": "Black / Red Tee"},
    "food": {"name": "Saintlock Meal", "price": 25, "desc": "Food Item"},
    "econ": {"name": "Econ Item", "price": 40, "desc": "Econ Item"},
}

# In-memory DB
accounts = {}  # telegram_id -> {username, password, balance, cart:[], loyalty}
pending_topups = {}  # order_id -> {user_id, username, method, note}

ASK_USERNAME, ASK_PASSWORD = range(2)

def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔝 Top Up Balance", callback_data="topup_menu")],
        [InlineKeyboardButton("🛒 Shop CC", callback_data="shop_hoodie"),
         InlineKeyboardButton("🥊 Shop_Accounts", callback_data="shop_tee")],
        [InlineKeyboardButton("🥇 Shop_Enrolls", callback_data="shop_food"),
         InlineKeyboardButton("🗑️ Shop_BINs", callback_data="shop_econ")],
        [InlineKeyboardButton("🛒", callback_data="cart"),
         InlineKeyboardButton("💰", callback_data="balance"),
         InlineKeyboardButton("📞", callback_data="support")],
    ])

def welcome_text(user_id):
    acc = accounts.get(user_id)
    if not acc:
        return "Welcome to SAINTLOCK"
    return (
        f"⚫️🔴 Welcome to SAINTLOCK 🔴⚫️\n\n"
        f"👤 Username: {acc['username']}\n"
        f"⭐ Customer Loyalty: {acc['loyalty']}%\n"
        f"💰 Account Balance: ${acc['balance']:.2f}  |  🛒 Cart Items: {len(acc['cart'])}\n\n"
        f"Choose a category below:"
    )

# ---------- START / SIGNUP ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in accounts:
        await update.message.reply_text(
            "⚫️🔴 Welcome to SAINTLOCK 🔴⚫️\n\n"
            "You need an account to shop.\n"
            "Create a Username (at least 5 characters):"
        )
        return ASK_USERNAME
    await update.message.reply_text(welcome_text(user_id), reply_markup=main_keyboard())
    return ConversationHandler.END

async def ask_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.strip()
    if len(username) < 5:
        await update.message.reply_text("Username must be at least 5 characters. Try again:")
        return ASK_USERNAME
    if any(a['username'].lower() == username.lower() for a in accounts.values()):
        await update.message.reply_text("That username is taken. Pick another:")
        return ASK_USERNAME
    context.user_data['new_username'] = username
    await update.message.reply_text("Now create a Password:")
    return ASK_PASSWORD

async def ask_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    accounts[user_id] = {
        "username": context.user_data['new_username'],
        "password": update.message.text,
        "balance": 0.0,
        "cart": [],
        "loyalty": 0
    }
    await update.message.reply_text(welcome_text(user_id), reply_markup=main_keyboard())
    return ConversationHandler.END

# ---------- BUTTONS ----------

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    # HOME
    if data == "home":
        await query.edit_message_text(welcome_text(user_id), reply_markup=main_keyboard())
        return

    # CART / BALANCE / SUPPORT
    if data == "cart":
        acc = accounts.get(user_id, {"cart": []})
        items = "\n".join(acc['cart']) if acc['cart'] else "Empty"
        await query.edit_message_text(f"🛒 Your Cart:\n{items}", reply_markup=main_keyboard())
        return
    if data == "balance":
        acc = accounts.get(user_id, {"balance": 0})
        await query.edit_message_text(f"💰 Balance: ${acc['balance']:.2f}", reply_markup=main_keyboard())
        return
    if data == "support":
        await query.edit_message_text(f"📞 Support: Contact {SUPPORT_HANDLE}", reply_markup=main_keyboard())
        return

    # SHOP CATEGORIES
    if data.startswith("shop_"):
        key = data.replace("shop_", "")
        p = PRODUCTS[key]
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"🛒 Add to Cart - {p['name']}", callback_data=f"add_{key}")],
            [InlineKeyboardButton(f"💳 Checkout with Card - ${p['price']} (Square)", callback_data=f"checkout_{key}")],
            [InlineKeyboardButton("⬅️ Back", callback_data="home")]
        ])
        await query.edit_message_text(
            f"⚫️🔴 {p['name']} 🔴⚫️\n\n"
            f"{p['desc']}\n"
            f"Price: ${p['price']}\n\n"
            f"Checkout uses Square - your card goes to Square only, never to us.",
            reply_markup=kb
        )
        return

    if data.startswith("add_"):
        key = data.replace("add_", "")
        p = PRODUCTS[key]
        accounts[user_id]['cart'].append(p['name'])
        await query.edit_message_text(f"✅ Added {p['name']} to cart.\nCart Items: {len(accounts[user_id]['cart'])}", reply_markup=main_keyboard())
        return

    # SQUARE CHECKOUT - ONE LINK FOR ALL ITEMS
    if data.startswith("checkout_"):
        key = data.replace("checkout_", "")
        p = PRODUCTS[key]
        await query.edit_message_text(
            f"⚫️🔴 CHECKOUT - {p['name']} - ${p['price']} 🔴⚫️\n\n"
            f"Pay securely with Credit/Debit Card via 【entity-Square¦canonical_name=Square】:\n"
            f"👉 {SQUARE_CHECKOUT_LINK}\n\n"
            f"⚠️ When 【entity-Square¦canonical_name=Square】 asks for amount, type: ${p['price']}\n\n"
            f"Money goes straight to my Square account.\n"
            f"After you pay, send your Square receipt to {SUPPORT_HANDLE}",
            reply_markup=main_keyboard()
        )
        return

    # TOP UP MENU
    if data == "topup_menu":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("【entity-Chime¦canonical_name=Chime】", callback_data="topup_Chime"),
             InlineKeyboardButton("Cashapp", callback_data="topup_Cashapp")],
            [InlineKeyboardButton("BTC", callback_data="topup_BTC"),
             InlineKeyboardButton("SOL", callback_data="topup_SOL"),
             InlineKeyboardButton("ETH", callback_data="topup_ETH")],
            [InlineKeyboardButton("⬅️ Back", callback_data="home")]
        ])
        await query.edit_message_text(
            "⚫️🔴 TOP UP BALANCE 🔴⚫️\n\n"
            "⚠️ For Crypto: Screenshot your transaction BEFORE you send it. You will need the SS + Order # to complete Top Up.\n\nChoose a method:",
            reply_markup=kb
        )
        return

    if data.startswith("topup_"):
        method = data.replace("topup_", "")
        acc = accounts.get(user_id)
        username = acc['username'] if acc else query.from_user.username
        note = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        order_id = f"SL-{random.randint(100000, 999999)}"
        pending_topups[order_id] = {"user_id": user_id, "username": username, "method": method, "note": note}

        if method in ["【entity-Chime¦canonical_name=Chime】", "Cashapp"]:
            await query.edit_message_text(
                f"⚫️🔴 TOP UP - {method} 🔴⚫️\n\n"
                f"Send to: {PAYMENTS[method]}\n"
                f"📝 IMPORTANT NOTE - Put this in the payment note: {note}\n"
                f"Admin will use this note to find your payment.\n\n"
                f"After sending, wait for admin approval.",
                reply_markup=main_keyboard()
            )
            admin_text = f"🧾 NEW TOP UP REQUEST\n\nUser: {username} (ID: {user_id})\nMethod: {method}\nNote to look for: {note}\n\nCheck your {method} and Approve/Decline:"
        else:
            await query.edit_message_text(
                f"⚫️🔴 TOP UP - {method} 🔴⚫️\n\n"
                f"Send to: {PAYMENTS[method]}\n"
                f"🧾 Order #: {order_id}\n\n"
                f"⚠️ Screenshot your transaction NOW.\n"
                f"Please Contact support {SUPPORT_HANDLE} with your Order # and a SS of transaction to complete Top Up",
                reply_markup=main_keyboard()
            )
            admin_text = f"🧾 NEW TOP UP REQUEST\n\nUser: {username} (ID: {user_id})\nMethod: {method}\nOrder #: {order_id}\n\nAsk user for SS + Order # and Approve/Decline:"

        admin_kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Approve Top Up", callback_data=f"approve_{order_id}"),
            InlineKeyboardButton("❌ Decline Top Up", callback_data=f"decline_{order_id}")
        ]])
        await context.bot.send_message(chat_id=ADMIN_ID, text=admin_text, reply_markup=admin_kb)
        return

    if data.startswith("approve_"):
        order_id = data.replace("approve_", "")
        await query.edit_message_text(f"✅ Approved {order_id}. Use /addbalance {order_id} <amount> to add funds.")
        return

    if data.startswith("decline_"):
        order_id = data.replace("decline_", "")
        info = pending_topups.get(order_id)
        if info:
            await context.bot.send_message(chat_id=info['user_id'], text=f"❌ Your Top Up {order_id} was declined. Contact support {SUPPORT_HANDLE}")
        await query.edit_message_text(f"❌ Declined {order_id}")
        return

# ---------- ADMIN COMMANDS ----------

async def listaccounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not accounts:
        await update.message.reply_text("No accounts yet.")
        return
    text = "👥 All Accounts (usernames only):\n\n" + "\n".join([f"- {a['username']} | Loyalty: {a['loyalty']}% | Balance: ${a['balance']:.2f}" for a in accounts.values()])
    await update.message.reply_text(text)

async def botaccounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await listaccounts(update, context)

async def addbalance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        order_id = context.args[0]
        amount = float(context.args[1])
        info = pending_topups.get(order_id)
        if not info:
            await update.message.reply_text("Order not found.")
            return
        accounts[info['user_id']]['balance'] += amount
        accounts[info['user_id']]['loyalty'] = min(100, accounts[info['user_id']]['loyalty'] + 1)
        await context.bot.send_message(chat_id=info['user_id'], text=f"✅ Top Up Approved! ${amount} added. New Balance: ${accounts[info['user_id']]['balance']:.2f}")
        await update.message.reply_text(f"Added ${amount} to {info['username']}")
    except:
        await update.message.reply_text("Use: /addbalance <OrderID> <amount>  Example: /addbalance SL-123456 50")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={ASK_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_username)],
                ASK_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_password)]},
        fallbacks=[]
    )
    app.add_handler(conv)
    app.add_handler(CommandHandler("listaccounts", listaccounts))
    app.add_handler(CommandHandler("Botaccounts", botaccounts))
    app.add_handler(CommandHandler("addbalance", addbalance))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
