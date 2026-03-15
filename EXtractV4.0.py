import re
import time
import csv
import tkinter as tk
from tkinter import messagebox
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from threading import Thread
import datetime

collected_data = []  # Stores (first_name, email)
TEMP_DATA = []       # Temp data for incremental saving
LAST_SAVE_TIME = time.time()
COUNT_THRESHOLD = 10
TIME_INTERVAL = 300  # 5 minutes

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

            extract_emails(driver)

            if not clicked:
                print("No visible 'Load more comments' buttons right now.")
        except Exception as net_err:
            print("Network issue occurred:", net_err)
            print("Waiting 60 seconds for network restoration...")
            time.sleep(60)

        if time.time() - last_click_time > 150:
            print("No new comments loaded for over 2.5 minutes. Initiating countdown...")
            save_data(TEMP_DATA)
            TEMP_DATA.clear()
            countdown_start = time.time()
            while time.time() - countdown_start < 90:
                extract_emails(driver)
                time.sleep(10)
            break

def extract_emails(driver):
    global TEMP_DATA, LAST_SAVE_TIME

    comments = driver.find_elements(By.CLASS_NAME, "comments-comment-item__main-content")

    for comment in comments:
        text = comment.text
        print("FULL COMMENT HTML:\n", comment.get_attribute("outerHTML"))  # For debugging

        found_emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
        first_name = "Unknown"

        try:
            # Move up to full comment container
            parent = comment.find_element(By.XPATH, "./ancestor::div[contains(@class, 'comments-comment-item')]")
            # Extract full name from aria-label (most reliable)
            name_element = parent.find_element(By.XPATH, ".//a[@aria-label]")
            full_name = name_element.get_attribute("aria-label").strip()
            if full_name:
                first_name = full_name.split()[0]
        except Exception as e:
            print("Name extraction failed:", e)
            first_name = "Unknown"

        for email in found_emails:
            if email not in [entry[1] for entry in collected_data]:
                TEMP_DATA.append((first_name, email))
                collected_data.append((first_name, email))
                print(f"Extracted: {first_name} <{email}>")

    if len(TEMP_DATA) >= COUNT_THRESHOLD or time.time() - LAST_SAVE_TIME >= TIME_INTERVAL:
        save_data(TEMP_DATA)
        TEMP_DATA.clear()
        LAST_SAVE_TIME = time.time()

def save_data(data):
    if data:
        with open("collected_emails.csv", mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            for name, email in data:
                writer.writerow([name, email])
        print(f"Saved {len(data)} entries to collected_emails.csv")

def start_extraction(email, password, post_url):
    global collected_data, TEMP_DATA
    collected_data.clear()
    TEMP_DATA.clear()

    try:
        service = Service('./chromedriver.exe')
        driver = webdriver.Chrome(service=service)

        login(driver, email, password)
        load_post(driver, post_url)
        extract_emails(driver)
        driver.quit()

        if TEMP_DATA:
            save_data(TEMP_DATA)
            TEMP_DATA.clear()

        if collected_data:
            messagebox.showinfo("Done", f"{len(collected_data)} unique entries saved to collected_emails.csv")
        else:
            messagebox.showinfo("No Emails", "No emails found in the comments.")

    except Exception as e:
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        fallback = f"emails_error_backup_{timestamp}.csv"
        save_data(TEMP_DATA)
        TEMP_DATA.clear()
        messagebox.showerror("Error", f"{str(e)}\nProgress saved to {fallback}")

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
