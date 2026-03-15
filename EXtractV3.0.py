import re
import time
import tkinter as tk
from tkinter import messagebox, filedialog
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from threading import Thread
import datetime
import os
import signal

collected_emails = []  # Stores all emails
BATCH_COUNT = 0
BATCH_SIZE = 500
CURRENT_BATCH = []
STOP_REQUESTED = False
OUTPUT_FILE = os.path.join(os.getcwd(), "collected_emails.txt")

# Ensure the file exists before starting
with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
    pass

def signal_handler(sig, frame):
    global STOP_REQUESTED
    print("\n⚠️ CTRL+E pressed. Saving progress and exiting...")
    STOP_REQUESTED = True
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)  # CTRL+C fallback

def login(driver, email, password):
    driver.get("https://www.linkedin.com/login")
    time.sleep(2)
    driver.find_element(By.ID, "username").send_keys(email)
    driver.find_element(By.ID, "password").send_keys(password + Keys.RETURN)
    time.sleep(5)

def load_post(driver, post_url):
    driver.get(post_url)
    time.sleep(5)

    try:
        filter_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Most relevant')]"))
        )
        filter_button.click()
        time.sleep(1)

        most_recent = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//span[text()='Most recent']/ancestor::div[@role='button']"))
        )
        driver.execute_script("arguments[0].click();", most_recent)
        time.sleep(3)
    except Exception as e:
        print("Could not switch to 'Most recent':", e)

    start_time = time.time()
    last_click_time = time.time()

    while True:
        if STOP_REQUESTED:
            break

        try:
            driver.execute_script("window.scrollBy(0, 600);")
            time.sleep(1.5)

            more_buttons = driver.find_elements(By.XPATH, "//button[contains(., 'more comments')]")
            clicked = False
            for btn in more_buttons:
                if btn.is_displayed():
                    try:
                        driver.execute_script("arguments[0].click();", btn)
                        print("Clicked 'Load more comments'")
                        clicked = True
                        last_click_time = time.time()
                        time.sleep(2)
                    except Exception as click_err:
                        print("Click error:", click_err)

            if not clicked:
                print("No visible 'Load more comments' buttons right now.")
        except Exception as net_err:
            print("Network issue occurred:", net_err)
            print("Waiting 60 seconds for network restoration...")
            time.sleep(60)

        extract_emails(driver)

        if time.time() - last_click_time > 150:
            print("No new comments loaded for over 2.5 minutes. Stopping scroll.")
            break

def extract_emails(driver):
    global collected_emails, CURRENT_BATCH
    comments = driver.find_elements(By.CLASS_NAME, "comments-comment-item__main-content")

    for comment in comments:
        text = comment.text
        found_emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}', text)
        for email in found_emails:
            if email not in collected_emails:
                collected_emails.append(email)
                CURRENT_BATCH.append(email)

        if len(CURRENT_BATCH) >= BATCH_SIZE:
            save_emails(CURRENT_BATCH)
            CURRENT_BATCH = []

def save_emails(emails):
    global BATCH_COUNT
    if emails:
        with open(OUTPUT_FILE, mode='a', encoding='utf-8') as f:
            for email in emails:
                f.write(email + "\n")
            f.flush()
            os.fsync(f.fileno())  # Flush to disk immediately
        BATCH_COUNT += 1
        print(f"✅ Saved {len(emails)} emails to {OUTPUT_FILE} (Batch {BATCH_COUNT})")
        print(f"📝 File now contains: {len(collected_emails)} total emails.")

def start_extraction(email, password, post_url):
    global collected_emails, CURRENT_BATCH
    collected_emails.clear()
    CURRENT_BATCH.clear()
    try:
        service = Service('./chromedriver.exe')
        driver = webdriver.Chrome(service=service)

        login(driver, email, password)
        load_post(driver, post_url)

        if CURRENT_BATCH:
            save_emails(CURRENT_BATCH)

        driver.quit()
        messagebox.showinfo("Done", f"✅ Total emails saved: {len(collected_emails)}\nSaved to: {OUTPUT_FILE}")
    except Exception as e:
        if CURRENT_BATCH:
            save_emails(CURRENT_BATCH)
        messagebox.showerror("Error", f"❌ {str(e)}\nProgress saved to {OUTPUT_FILE}")

def run_gui():
    def on_submit():
        email = email_entry.get()
        password = password_entry.get()
        url = url_entry.get()
        if not (email and password and url):
            messagebox.showwarning("Missing Info", "Please fill in all fields.")
            return
        Thread(target=start_extraction, args=(email, password, url)).start()

    app = tk.Tk()
    app.title("LinkedIn Email Extractor")
    app.geometry("400x250")

    tk.Label(app, text="LinkedIn Email").pack(pady=5)
    email_entry = tk.Entry(app, width=40)
    email_entry.pack()

    tk.Label(app, text="Password").pack(pady=5)
    password_entry = tk.Entry(app, show="*", width=40)
    password_entry.pack()

    tk.Label(app, text="LinkedIn Post URL").pack(pady=5)
    url_entry = tk.Entry(app, width=40)
    url_entry.pack()

    tk.Button(app, text="Extract Emails", command=on_submit, bg="#4CAF50", fg="white").pack(pady=20)

    app.mainloop()

if __name__ == "__main__":
    run_gui()
