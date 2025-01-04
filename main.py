import os
import json
import csv
import queue
import threading
import re
from datetime import datetime
import time
import random
import email
import imaplib
from typing import Optional
from dataclasses import dataclass
from faker import Faker
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium import webdriver
from colorama import init, Fore, Style

init()  # Initialize colorama


class Colors:
    SUCCESS = Fore.GREEN
    ERROR = Fore.RED
    INFO = Fore.WHITE
    ATTEMPT = Fore.YELLOW
    START = Fore.CYAN
    RESET = Style.RESET_ALL


@dataclass
class SignupJob:
    email: str
    status: str = "pending"
    code: Optional[str] = None
    timestamp: Optional[str] = None
    attempts: int = 0  # Track number of verification attempts


# Shared queues
signup_queue = queue.Queue()  # For new signup jobs
verification_queue = queue.Queue()  # For emails waiting for verification codes
completed_queue = queue.Queue()  # For completed signups


def get_verification_code(email_address, password, test_email, worker_id):
    """Get verification code from email - single attempt"""
    try:
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(email_address, password)
        mail.select("inbox")

        search_criteria = f'(FROM "no-reply@abs.xyz" SUBJECT "Waitlist Verification Code" TO "{test_email}")'
        _, messages = mail.search(None, search_criteria)

        message_numbers = messages[0].split()
        if message_numbers:
            latest_email_id = message_numbers[-1]
            _, msg = mail.fetch(latest_email_id, "(RFC822)")
            email_body = msg[0][1]
            email_message = email.message_from_bytes(email_body)

            for part in email_message.walk():
                if part.get_content_type() == "text/html":
                    body = part.get_payload(decode=True).decode()
                    match = re.search(r'<p style="font-size:24px;.*?">(\w+)</p>', body)
                    if match:
                        code = match.group(1)
                        print(
                            f"{Colors.SUCCESS}Worker {worker_id} | Found code: {code} for {test_email}{Colors.RESET}"
                        )
                        return code
        return None

    except Exception as e:
        print(
            f"{Colors.ERROR}Worker {worker_id} | Verification attempt failed: {str(e)}{Colors.RESET}"
        )
        return None
    finally:
        try:
            mail.logout()
        except:
            pass


def save_to_csv(email: str, code: str, timestamp: str, status: str = "verified"):
    """Save signup information to CSV file"""
    with open("signup_log.csv", "a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([email, code, timestamp, status])


def verification_worker(gmail_address: str, gmail_password: str, worker_id: int):
    """Worker that checks for verification codes"""
    while True:
        try:
            job = verification_queue.get(timeout=1)

            if job.status == "pending":
                code = get_verification_code(
                    gmail_address, gmail_password, job.email, worker_id
                )

                if code:
                    job.code = code
                    job.status = "verified"
                    job.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    completed_queue.put(job)
                else:
                    job.attempts += 1
                    print(
                        f"{Colors.ATTEMPT}Worker {worker_id} | Attempt {job.attempts}/10 | No code found for {job.email}{Colors.RESET}"
                    )

                    if job.attempts >= 10:
                        print(
                            f"{Colors.ERROR}Worker {worker_id} | Max attempts reached for {job.email}{Colors.RESET}"
                        )
                        job.status = "failed"
                        completed_queue.put(job)
                    else:
                        time.sleep(2)
                        verification_queue.put(job)

            verification_queue.task_done()

        except queue.Empty:
            time.sleep(1)
        except Exception as e:
            print(
                f"{Colors.ERROR}Verification worker {worker_id} error: {str(e)}{Colors.RESET}"
            )


def signup_worker(worker_id: int, total_signups: int):
    """Worker that handles the signup process"""
    signup_count = 0
    while True:
        try:
            job = signup_queue.get(timeout=1)
            if job.status == "pending":
                signup_count += 1
                print(
                    f"{Colors.START}Thread {worker_id} | Signup {signup_count}/{total_signups} | Starting signup...{Colors.RESET}"
                )
                success = perform_signup(
                    job.email, worker_id, signup_count, total_signups
                )
                if success:
                    verification_queue.put(job)
            signup_queue.task_done()
        except queue.Empty:
            time.sleep(1)
        except Exception as e:
            print(
                f"{Colors.ERROR}Thread {worker_id} signup error: {str(e)}{Colors.RESET}"
            )


def perform_signup(
    test_email: str, worker_id: int, signup_count: int, total_signups: int
) -> bool:
    """Perform the actual signup process"""
    driver = None
    try:
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-extensions")  # Added for speed
        chrome_options.add_argument("--disable-logging")  # Added for speed
        chrome_options.add_argument("--disable-dev-shm-usage")  # Added for stability
        chrome_options.add_argument("--no-first-run")  # Added for speed
        chrome_options.add_argument("--disable-infobars")  # Added for speed

        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(20)  # Added timeout
        wait = WebDriverWait(driver, 8)  # Reduced wait time

        print(
            f"{Colors.START}Thread {worker_id} | Signup {signup_count}/{total_signups} | Starting for {test_email}{Colors.RESET}"
        )

        driver.get("https://abs.xyz")
        join_waitlist_button = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[.//text()='Join Waitlist']")
            )
        )
        join_waitlist_button.click()

        email_input = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "input[placeholder='Email']")
            )
        )
        email_input.send_keys(test_email)

        confirm_button = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
        )
        confirm_button.click()

        return True

    except Exception as e:
        print(
            f"{Colors.ERROR}Thread {worker_id} | Signup {signup_count}/{total_signups} | Error: {str(e)}{Colors.RESET}"
        )
        return False
    finally:
        if driver:
            driver.quit()


def completion_worker():
    """Worker that handles completed signups"""
    while True:
        try:
            job = completed_queue.get(timeout=1)
            if job.status == "verified":
                save_to_csv(job.email, job.code, job.timestamp)
            elif job.status == "failed":
                save_to_csv(
                    job.email,
                    "FAILED",
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "failed",
                )
            completed_queue.task_done()
        except queue.Empty:
            time.sleep(1)
        except Exception as e:
            print(f"{Colors.ERROR}Completion worker error: {str(e)}{Colors.RESET}")


with open("config.json", "r") as f:
    config = json.load(f)

gmail_address = config["imap_username"]
gmail_password = config["imap_password"]
email_suffix = config["email_suffix"]
imap_server = config["imap_server"]

def generate_email():
    """Generate a random email address"""
    fake = Faker()
    username = "".join(fake.user_name() + (str(random.randint(0, 9999))))

    return f"{username}@{email_suffix}"


def main():
    """Main function"""
    num_signup_threads = int(input("Enter number of signup threads: "))
    num_signups_per_thread = int(input("Enter number of signups per thread: "))

    # Start verification workers
    for i in range(5):
        t = threading.Thread(
            target=verification_worker, args=(gmail_address, gmail_password, i + 1)
        )
        t.daemon = True
        t.start()

    # Start signup workers
    for i in range(num_signup_threads):
        t = threading.Thread(target=signup_worker, args=(i + 1, num_signups_per_thread))
        t.daemon = True
        t.start()

    # Start completion worker
    t = threading.Thread(target=completion_worker)
    t.daemon = True
    t.start()

    if not os.path.exists("signup_log.csv"):
        with open("signup_log.csv", "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["email", "code", "timestamp", "status"])

    total_signups = num_signup_threads * num_signups_per_thread
    print(
        f"\n{Colors.INFO}Starting {total_signups} total signups with {num_signup_threads} threads{Colors.RESET}"
    )
    print(
        f"{Colors.INFO}Each thread will process {num_signups_per_thread} signups\n{Colors.RESET}"
    )

    for _ in range(total_signups):
        email = generate_email()
        signup_queue.put(SignupJob(email=email))

    try:
        signup_queue.join()
        verification_queue.join()
        completed_queue.join()
        print(f"\n{Colors.SUCCESS}All tasks completed successfully!{Colors.RESET}")
    except KeyboardInterrupt:
        print(f"\n{Colors.ERROR}Gracefully shutting down...{Colors.RESET}")


if __name__ == "__main__":
    main()
