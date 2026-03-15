import re
import time
import tkinter as tk
from tkinter import messagebox, filedialog
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from threading import Thread
import datetime

collected_emails = set()  # Use a set to avoid duplicates

def login(driver, email, password):
    driver.get("https://www.linkedin.com/login")
    time.sleep(2)
    driver.find_element(By.ID, "username").send_keys(email)
    driver.find_element(By.ID, "password").send_keys(password + Keys.RETURN)
    time.sleep(5)

def load_post(driver, post_url):
    driver.get(post_url)
    time.sleep(5)  # Wait before scrolling begins

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

    # Initial scrape before any clicks
    new_emails = extract_emails(driver)
    if new_emails:
        append_to_txt(new_emails, "collected_emails.txt")

    while True:
        try:
            driver.execute_script("window.scrollBy(0, 600);")
            time.sleep(1.5)

            more_buttons = driver.find_elements(By.XPATH, "//button[contains(., 'more comments')]" )
            clicked = False
            for btn in more_buttons:
                if btn.is_displayed():
                    try:
                        driver.execute_script("arguments[0].click();", btn)
                        print("Clicked 'Load more comments'")
                        last_click_time = time.time()
                        time.sleep(2)
                        # Scrape and save after each click
                        new_emails = extract_emails(driver)
                        if new_emails:
                            append_to_txt(new_emails, "collected_emails.txt")
                        clicked = True
                    except Exception as click_err:
                        print("Click error:", click_err)

            if not clicked:
                print("No visible 'Load more comments' buttons right now.")
        except Exception as net_err:
            print("Network issue occurred:", net_err)
            print("Waiting 60 seconds for network restoration...")
            time.sleep(60)

        if time.time() - last_click_time > 150:
            print("No new comments loaded for over 2.5 minutes. Stopping scroll.")
            break

def extract_emails(driver):
    global collected_emails
    comments = driver.find_elements(By.CLASS_NAME, "comments-comment-item__main-content")
    new_emails = set()
    for comment in comments:
        text = comment.text
        found_emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
        for email in found_emails:
            if email not in collected_emails:
                new_emails.add(email)
    if new_emails:
        collected_emails.update(new_emails)
        for email in new_emails:
            print("Extracted Email:", email)
    return new_emails

def save_to_txt(data, filepath):
    with open(filepath, mode='w', encoding='utf-8') as f:
        for email in data:
            f.write(email + "\n")

def append_to_txt(data, filepath):
    # Appends emails to file, one per line
    with open(filepath, mode='a', encoding='utf-8') as f:
        for email in data:
            f.write(email + "\n")

def start_extraction(email, password, post_url):
    global collected_emails
    collected_emails.clear()
    driver = None

    try:
        service = Service(ChromeDriverManager().install())
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--remote-debugging-port=9222')
        chrome_options.add_argument('--disable-gpu')
        driver = webdriver.Chrome(service=service, options=chrome_options)

        login(driver, email, password)
        load_post(driver, post_url)

        if collected_emails:
            messagebox.showinfo("Done", f"{len(collected_emails)} emails saved to collected_emails.txt")
        else:
            messagebox.showinfo("No Emails", "No emails found in the comments.")

    except Exception as e:
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        fallback = f"emails_error_backup_{timestamp}.txt"
        save_to_txt(collected_emails, fallback)
        messagebox.showerror("Error", f"{str(e)}\nProgress saved to {fallback}")
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

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