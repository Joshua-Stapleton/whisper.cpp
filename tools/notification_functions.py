import subprocess
import smtplib
import aiosmtplib

REPLACEMENTS = {
    '\u2019': "'",  # Right single quotation mark
    '\u2018': "'",  # Left single quotation mark
    '\u201C': '"',  # Left double quotation mark
    '\u201D': '"',  # Right double quotation mark
    '\u2026': '...',  # Horizontal ellipsis
    '\xe4': 'a',  # Latin small letter a with diaeresis
    '\xc4': 'A',  # Latin capital letter A with diaeresis
    '\xf6': 'o',  # Latin small letter o with diaeresis
    '\xd6': 'O',  # Latin capital letter O with diaeresis
    '\xfc': 'u',  # Latin small letter u with diaeresis
    '\xdc': 'U',  # Latin capital letter U with diaeresis
    '\xdf': 'ss',  # Latin small letter sharp S, used in German
    '\u20AC': 'EUR',  # Euro sign
    '\u00A3': 'GBP',  # Pound sign
    '\u00A5': 'JPY',  # Yen sign
    '\u00A9': '(c)',  # Copyright sign
    '\u00AE': '(r)',  # Registered sign
    '\u2122': '(tm)',  # Trade mark sign
    '\u00B0': ' degrees ',  # Degree sign
}

def replace_disallowed_characters(message):
    for old, new in REPLACEMENTS.items():
        message = message.replace(old, new)
    return message


def send_email(sender, recipient, subject, message, password):
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.ehlo()
        server.starttls()
        server.login(sender, password)
        message = 'Subject: {}\n\n{}'.format(subject, message)
        server.sendmail(sender, recipient, replace_disallowed_characters(message))
        server.quit()
        print("Successfully sent email to " + recipient, ". Subject: " + subject)
    except Exception as e:
        print("Failed to send email: {}".format(e))


async def send_email_async(sender, recipient, subject, message, password):
    try:
        message = f'Subject: {subject}\n\n{message}'
        await aiosmtplib.send(
            message,
            sender=sender,
            recipients=[recipient],
            hostname="smtp.gmail.com",
            port=465, # Use port 465 for SMTPS
            username=sender,
            password=password,
            use_tls=True,
        )
        print("Successfully sent email to " + recipient, ". Subject: " + subject)
    except Exception as e:
        print(f"Failed to send email: {e}")
