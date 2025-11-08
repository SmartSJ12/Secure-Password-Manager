import sqlite3
import os
import sys
import smtplib
import random
import re
import string
from cryptography.fernet import Fernet
from difflib import SequenceMatcher


# ============================================
# PASSWORD INPUT WITH ASTERISKS
# ============================================
def input_password(prompt="Enter password: "):
    """Custom password input that shows '*' for each character typed."""
    # VS Code terminal often doesn't support real-time masking
    if os.getenv("TERM_PROGRAM") == "vscode":
        return input(prompt)

    password = ""
    print(prompt, end='', flush=True)
    # Windows
    if os.name == 'nt':
        import msvcrt
        while True:
            ch = msvcrt.getch()
            if ch in {b'\r', b'\n'}:
                print('')
                break
            elif ch == b'\x08':  # Backspace
                if len(password) > 0:
                    password = password[:-1]
                    sys.stdout.write('\b \b')
                    sys.stdout.flush()
            elif ch == b'\x03':  # Ctrl+C
                raise KeyboardInterrupt
            else:
                ch = ch.decode(errors="ignore")
                if ch.isprintable():
                    password += ch
                    sys.stdout.write('*')
                    sys.stdout.flush()
        # macOS / Linux
    else:
        import termios
        import tty
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            while True:
                ch = sys.stdin.read(1)
                if ch in ('\r', '\n'):
                    print('')
                    break
                elif ch == '\x7f':  # Backspace
                    if len(password) > 0:
                        password = password[:-1]
                        sys.stdout.write('\b \b')
                        sys.stdout.flush()
                elif ch == '\x03':  # Ctrl+C
                    raise KeyboardInterrupt
                else:
                    password += ch
                    sys.stdout.write('*')
                    sys.stdout.flush()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    return password

# ============================================
# ENCRYPTION SETUP
# ============================================
KEY_FILE = "key.key"

def generate_key():
    if not os.path.exists(KEY_FILE):
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as key_file:
            key_file.write(key)
        print("Encryption key generated and saved.\n")

def load_key():
    if not os.path.exists(KEY_FILE):
        generate_key()
    with open(KEY_FILE, "rb") as key_file:
        return key_file.read()

fernet = Fernet(load_key())

# ============================================
# TWO - FACTOR AUTHENTICATION
# ============================================
def send_email_otp(receiver_email):
    otp = random.randint(100000, 999999)
    message = f"Subject: Your OTP Code\n\nYour OTP is {otp}"
    
    # Login credentials
    sender = "jerripottulu.2025@vitstudent.ac.in"
    password = "zrdw pbum zzgr flcw"  # Use an App Password, not your main password
    
    # Send email
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, receiver_email, message)
    
    return otp
# ============================================
# CHECKING PASSWORD STRENGTH
# ============================================
def check_password_strength(password, username=""):
    """Check if a password is strong and return feedback."""
    strength_criteria = {
        "length": len(password) >= 8,
        "uppercase": re.search(r"[A-Z]", password),
        "lowercase": re.search(r"[a-z]", password),
        "digit": re.search(r"\d", password),
        "special": re.search(r"[!@#$%^&*(),.?\":{}|<>]", password)
    }

    feedback_parts = []

    # --- Similarity check with username ---
    if username:
        # Normalize both
        user_norm = re.sub(r'[^a-z]', '', username.lower())
        pass_norm = re.sub(r'[^a-z]', '', password.lower())

        # Skip similarity check if username has no letters
        if user_norm:
            # Direct substring check
            if user_norm in pass_norm or pass_norm in user_norm:
                feedback_parts.append("Password is too similar to username")
            else:
                # Fuzzy ratio check
                similarity_ratio = SequenceMatcher(None, user_norm, pass_norm).ratio()
                if similarity_ratio >= 0.6:  # 60% similarity threshold
                    feedback_parts.append("Password is too similar to username")

    # --- Standard strength checks ---
    if not strength_criteria["length"]:
        feedback_parts.append("at least 8 characters")
    if not strength_criteria["uppercase"]:
        feedback_parts.append("an uppercase letter")
    if not strength_criteria["lowercase"]:
        feedback_parts.append("a lowercase letter")
    if not strength_criteria["digit"]:
        feedback_parts.append("a number")
    if not strength_criteria["special"]:
        feedback_parts.append("a special character (!@#$%^& etc.)")

    # --- Final result ---
    if not feedback_parts:
        return True, "Strong password "
    else:
        return False, "Weak password  - Missing or issue: " + ", ".join(feedback_parts)

# ============================================
# GENERATE A STRONG PASSWORD
# ============================================
def generate_password(username=""):
    """Generate a strong password that meets all criteria and isn't too similar to the username."""
    special_chars = "!@#$%^&*()-_=+[]{};:,.<>?"
    all_chars = string.ascii_letters + string.digits + special_chars

    def too_similar(pwd, uname):
        uname_norm = re.sub(r'[^a-z]', '', uname.lower())
        pwd_norm = re.sub(r'[^a-z]', '', pwd.lower())
        if not uname_norm:
            return False
        if uname_norm in pwd_norm or pwd_norm in uname_norm:
            return True
        return SequenceMatcher(None, uname_norm, pwd_norm).ratio() >= 0.6

    max_attempts = 500
    for attempt in range(max_attempts):
        password_chars = [
            random.choice(string.ascii_lowercase),
            random.choice(string.ascii_uppercase),
            random.choice(string.digits),
            random.choice(special_chars)
        ]

        password_chars += random.choices(all_chars, k=random.randint(8, 12))
        random.shuffle(password_chars)
        password = "".join(password_chars)

        strong, _ = check_password_strength(password, username)

        if strong and not too_similar(password, username):
            return password

        if attempt > 200 and strong:
            return password

    return "".join(random.choices(all_chars, k=16))


# ============================================
# DATABASE SETUP
# ============================================
def init_db():
    conn = sqlite3.connect("password_manager.db")
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS credentials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            website TEXT NOT NULL,
            username TEXT NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS master (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            password TEXT NOT NULL
        )
    ''')

    cursor.execute("SELECT * FROM master WHERE id = 1")
    if not cursor.fetchone():
        default_master = "1"  # Default password for first run
        encrypted = fernet.encrypt(default_master.encode())
        cursor.execute("INSERT INTO master (id, password) VALUES (1, ?)", (encrypted,))
        print("Default master password created. (Use '1' to log in first time.)")

    conn.commit()
    conn.close()


# ============================================
# CRUD OPERATIONS
# ============================================
def add_credential():
    website = input("Enter website name: ")
    username = input("Enter username: ")
    password_confirmed = False

    while True:
        password = input_password("Enter password: ")
        is_strong, feedback = check_password_strength(password, username)
        print(feedback)

        if not is_strong:
            print("This password is weak.")

            while True:
                print("What would you like to do?")
                print("1. Use this weak password anyway.")
                print("2. Make or generate a stronger password.")
                choice = input("Enter your choice: ")

                if choice == "1":
                    # Ask to confirm the weak password
                    while True:
                        confirm_password = input_password("Confirm your password: ")
                        if confirm_password == password:
                            password_confirmed = True
                            break
                        else:
                            print("Passwords do NOT match. Try again.\n")
                    break

                elif choice == "2":
                    while True:
                        print("1. Strengthen it manually")
                        print("2. Generate a strong one automatically")
                        sub_choice = input("Enter your choice: ")

                        if sub_choice == "1":
                            break

                        elif sub_choice == "2":
                            while True:
                                print("Generating a strong password for you...")
                                generated_password = generate_password(username)
                                print(f"Your generated password is: {generated_password}\n")

                                print("1. Use this generated password")
                                print("2. Generate another")
                                print("3. Enter my own password instead")
                                sub_option = input("Enter your choice: ")

                                if sub_option == "1":
                                    password = generated_password
                                    password_confirmed = True
                                    break

                                elif sub_option == "2":
                                    continue  # regenerate

                                elif sub_option == "3":
                                    while True:
                                        password = input_password("Enter your own password: ")
                                        is_strong, feedback = check_password_strength(password, username)
                                        print(feedback)
                                        if not is_strong:
                                            print("That password is still weak. Please try again.\n")
                                            continue

                                        confirm_password = input_password("Confirm your password: ")
                                        if confirm_password != password:
                                            print("Passwords do NOT match. Try again.\n")
                                            continue
                                        password_confirmed = True
                                        break
                                    break
                                else:
                                    print("Invalid choice! Try again.\n")
                            break
                        else:
                            print("Invalid choice! Try again.\n")
                    break
                else:
                    print("Invalid choice! Try again.\n")
            if password_confirmed:
                break
        else:
            break

    if not password_confirmed:
        confirm_password = input_password("Confirm your password: ")
        if confirm_password != password:
            print("Passwords do NOT match. Operation failed.")
            return

    # Save to DB
    encrypted_password = fernet.encrypt(password.encode())
    conn = sqlite3.connect("password_manager.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO credentials (website, username, password) VALUES (?, ?, ?)",
        (website, username, encrypted_password)
    )
    conn.commit()
    conn.close()
    print("Credential added successfully!\n")


def view_credentials():
    conn = sqlite3.connect("password_manager.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM credentials")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("No credentials found.\n")
        return

    print("\nStored Credentials (Decrypted):")
    print("-" * 60)
    for row in rows:
        decrypted_password = fernet.decrypt(row[3]).decode()
        print(f"ID: {row[0]} | Website: {row[1]} | Username: {row[2]} | Password: {decrypted_password}")
    print("-" * 60 + "\n")

def update_credential():
    view_credentials()
    id_to_update = input("Enter the ID of the credential to update: ")

    # Validate ID input
    if not id_to_update.isdigit():
        print("Invalid ID format. Please enter a numeric ID.\n")
        return

    id_to_update = int(id_to_update)

    # Check if ID exists in DB
    conn = sqlite3.connect("password_manager.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM credentials WHERE id = ?", (id_to_update,))
    record = cursor.fetchone()

    if not record:
        print(f"No credential found with ID {id_to_update}.\n")
        conn.close()
        return

    print(f"\nEditing credential for Website: {record[1]} | Username: {record[2]}\n")

    website = input("Enter new website name (leave blank to keep current): ") or record[1]
    username = input("Enter new username (leave blank to keep current): ") or record[2]

    # Get password and check strength first
    while True:
        password = input_password("Enter new password: ")
        is_strong, feedback = check_password_strength(password, username)
        print(feedback)

        if not is_strong:
            confirm = input("Would you still like to use this weak password? (y/n): ").lower()
            if confirm != 'y':
                print("Please enter a different password.\n")
                continue
        break

    # Confirm password
    while True:
        confirm_password = input_password("Confirm your password: ")
        if confirm_password == password:
            break
        print("Passwords do NOT match. Try again.\n")

    # Save to DB
    encrypted_password = fernet.encrypt(password.encode())
    cursor.execute('''
        UPDATE credentials
        SET website = ?, username = ?, password = ?
        WHERE id = ?
    ''', (website, username, encrypted_password, id_to_update))
    conn.commit()
    conn.close()

    print("\nCredential updated successfully!\n")

def delete_credential():
    view_credentials()
    id_to_delete = input("Enter the ID of the credential to delete: ")

    # Validate ID input
    if not id_to_delete.isdigit():
        print("Invalid ID format. Please enter a numeric ID.\n")
        return

    id_to_delete = int(id_to_delete)

    conn = sqlite3.connect("password_manager.db")
    cursor = conn.cursor()

    # Check if ID exists
    cursor.execute("SELECT * FROM credentials WHERE id = ?", (id_to_delete,))
    record = cursor.fetchone()

    if not record:
        print(f"No credential found with ID {id_to_delete}.\n")
        conn.close()
        return

    # Confirm deletion
    print(f"\nAre you sure you want to delete this credential?")
    print(f"Website: {record[1]} | Username: {record[2]}")
    confirm = input("Type 'yes' to confirm deletion: ").strip().lower()

    if confirm == "yes":
        cursor.execute("DELETE FROM credentials WHERE id = ?", (id_to_delete,))
        conn.commit()
        print("Credential deleted successfully!\n")
    else:
        print("Deletion cancelled.\n")

    conn.close()

def get_master_password():
    """Fetch and decrypt the stored master password."""
    conn = sqlite3.connect("password_manager.db")
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM master WHERE id = 1")
    result = cursor.fetchone()
    conn.close()
    if result:
        return fernet.decrypt(result[0]).decode()
    return None


def set_master_password(new_password):
    """Encrypt and save the new master password."""
    encrypted = fernet.encrypt(new_password.encode())
    conn = sqlite3.connect("password_manager.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE master SET password = ? WHERE id = 1", (encrypted,))
    conn.commit()
    conn.close()

# ============================================
# MAIN MENU
# ============================================
def main():
    generate_key()
    init_db()
    master_password = get_master_password()
    number_of_tries = 0

    while True:
        if number_of_tries == 2:
            while True:
                print("It seems like you have forgotten your password, would you like to reset it?")
                print("1. Yes, I would like to reset my password.")
                print("2. No, I remember my password.")
                print("3. Exit")
                choice = input("Enter your choice: ")

                if choice == '1':
                    receiver = input("Enter your email: ")
                    otp_sent = send_email_otp(receiver)
                    try:
                        otp_entered = int(input("Enter the OTP sent to your email: "))
                    except ValueError:
                        print("Invalid input. OTP should be a number.")
                        continue

                    if otp_entered == otp_sent:
                        new_master = input_password("Enter your new master password: ")
                        confirm_master = input_password("Confirm your password: ")
                        if new_master == confirm_master:
                            set_master_password(new_master)
                            master_password = new_master
                            print("Password reset successful!")
                            number_of_tries = 0
                            break
                        else:
                            print("Passwords do NOT match. Operation Failed.")
                    else:
                        print("Invalid OTP.")
                elif choice == '2':
                    number_of_tries = 1
                    break
                elif choice == '3':
                    print("Exiting Secure Password Manager. Goodbye!")
                    sys.exit()
                else:
                    print("Invalid choice! Please try again.\n")

        print("========== Secure Password Manager ==========")
        entered_password = input_password("Enter Password: ")
        if entered_password == master_password:
            number_of_tries = 0
            while True:
                print("============================================")
                print("1. Add Credential")
                print("2. View Credentials")
                print("3. Update Credential")
                print("4. Delete Credential")
                print("5. Exit")
                choice = input("Enter your choice: ")

                if choice == '1':
                    add_credential()
                elif choice == '2':
                    view_credentials()
                elif choice == '3':
                    update_credential()
                elif choice == '4':
                    delete_credential()
                elif choice == '5':
                    print("Exiting Secure Password Manager. Goodbye!")
                    return
                else:
                    print("Invalid choice! Please try again.\n")
        else:
            number_of_tries += 1
            print("Incorrect Password.")

# ============================================
# RUN PROGRAM
# ============================================
if __name__ == "__main__":
    main()
