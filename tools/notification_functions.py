import smtplib
import aiosmtplib
import re

REPLACEMENTS = {
    '\u2019': "'",  # Right single quotation mark
    '\u2018': "'",  # Left single quotation mark
    '\u201C': '"',  # Left double quotation mark
    '\u201D': '"',  # Right double quotation mark
    '\u2026': '...',  # Horizontal ellipsis
    '\u2013': '-',
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
    '\xb0': ' degrees ',  # Degree sign in hexadecimal
    '\u00A2': ' cents ',  # Cent sign
    '\u2030': ' permille ',  # Per mille sign
    '\u2044': ' slash ',  # Fraction slash
}

def replace_disallowed_characters(message):
    for old, new in REPLACEMENTS.items():
        message = message.replace(old, new)
    return message


def remove_duplicates_and_brackets_from_string(message):
    lines = message.split('\n')
        
    lines_dict = {}
    for line in lines:
        lines_dict[line] = lines_dict.get(line, 0) + 1

    result = ""
    for line, count in lines_dict.items():
        if count <= 3 and not re.match(r'\s*\[.*\]\s*|\s*\(.*\)\s*', line):
            result += line + '\n'
            
    return result.strip()


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


async def send_email_async(sender, recipient, subject, message, password): # When GPT-4 generates emails, it sometimes also generates headers. The email function detects headers.
    try:
        # ensure there is no 'Subject' in the message body
        message = message.replace('Subject:', '')
        
        # ensure there is no 'Subject' in the subject
        subject = subject.replace('Subject:', '').strip()
        
        # only include the filename not the extensions
        subject = subject.split('.')[0]
        message = f'Subject: {subject}\n\n{message}'

        await aiosmtplib.send(
            remove_duplicates_and_brackets_from_string(replace_disallowed_characters(message)),
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
